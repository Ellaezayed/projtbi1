import asyncio
import json
import os
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch

import pandas as pd

import main
from metrics import Snapshot
from security import AnalyticsRateLimit, approved_origins


async def request(app, path, headers=(), method="GET", peer="192.0.2.1"):
    events = []

    async def send(event):
        events.append(event)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    await app({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path, "root_path": "",
        "query_string": b"", "headers": list(headers), "client": (peer, 12345),
        "server": ("localhost", 8000),
    }, receive, send)
    return events[0]["status"], dict(events[0]["headers"]), b"".join(
        event.get("body", b"") for event in events[1:]
    )


class ApiSecurityTests(IsolatedAsyncioTestCase):
    async def test_reviews_fail_closed_and_require_the_right_scope(self):
        raw = "r" * 40
        limited = "l" * 40
        snapshot = Snapshot(pd.DataFrame(), pd.DataFrame([{"review_text": "Synthetic review", "author_id": "private-id"}]),
                            {}, [], {"observed_review_count": 1})
        with patch.object(main, "current_snapshot", return_value=snapshot) as load:
            with patch.dict(os.environ, {"RAW_REVIEW_API_TOKEN": "", "LIMITED_API_TOKEN": ""}):
                self.assertEqual((await request(main.app, "/api/reviews"))[0], 503)
            with patch.dict(os.environ, {"RAW_REVIEW_API_TOKEN": raw, "LIMITED_API_TOKEN": limited}):
                for token, expected in ((None, 401), ("invalid", 401), (limited, 403)):
                    auth = [] if token is None else [(b"authorization", f"Bearer {token}".encode())]
                    status, headers, body = await request(main.app, "/api/reviews", auth)
                    self.assertEqual(status, expected)
                    self.assertEqual(headers[b"cache-control"], b"no-store")
                    self.assertNotIn(b"Synthetic review", body)
                    if expected == 401:
                        self.assertEqual(headers[b"www-authenticate"], b"Bearer")
                load.assert_not_called()
                status, headers, body = await request(
                    main.app, "/api/reviews", [(b"authorization", f"Bearer {raw}".encode())]
                )
                self.assertEqual(status, 200)
                self.assertEqual(headers[b"cache-control"], b"no-store")
                self.assertIn(b"Synthetic review", body)
                self.assertNotIn(b"private-id", body)
                self.assertNotIn(raw.encode(), body)
                load.assert_called_once()

    async def test_public_dashboard_route_and_cors(self):
        snapshot = Snapshot(pd.DataFrame({"product_id": [], "product_name": []}),
                            pd.DataFrame(), {"product_count": 0}, [],
                            {"observed_review_count": 0})
        main.app.dependency_overrides[main.current_snapshot] = lambda: snapshot
        self.addCleanup(main.app.dependency_overrides.clear)
        for path in ("/api/overview", "/api/categories", "/api/products", "/api/reviews/summary"):
            status, _, _ = await request(main.app, path)
            self.assertEqual(status, 200, path)
        for origin, expected in ((b"http://localhost:3000", 200), (b"https://example.invalid", 400)):
            status, headers, _ = await request(main.app, "/api/reviews", [
                (b"origin", origin), (b"access-control-request-method", b"GET"),
                (b"access-control-request-headers", b"authorization"),
            ], method="OPTIONS")
            self.assertEqual(status, expected)
            self.assertEqual(headers.get(b"access-control-allow-origin"),
                             origin if expected == 200 else None)
            self.assertNotIn(b"access-control-allow-credentials", headers)

    async def test_rate_limits_and_window_reset(self):
        now = [0]
        limiter = AnalyticsRateLimit(main.app, peer_limit=2, global_limit=3, raw_limit=1,
                                     raw_global_limit=2, clock=lambda: now[0])
        self.assertNotEqual((await request(limiter, "/api/reviews"))[0], 429)
        status, headers, body = await request(limiter, "/api/reviews",
                                             [(b"x-forwarded-for", b"192.0.2.99")])
        self.assertEqual(status, 429)
        self.assertEqual(headers[b"retry-after"], b"60")
        self.assertEqual(json.loads(body), {"detail": "Too many requests."})
        self.assertNotEqual((await request(limiter, "/api/unknown"))[0], 429)
        self.assertEqual((await request(limiter, "/api/unknown"))[0], 429)
        self.assertNotEqual((await request(limiter, "/api/unknown", peer="192.0.2.2"))[0], 429)
        self.assertEqual((await request(limiter, "/api/unknown", peer="192.0.2.3"))[0], 429)
        now[0] = 60
        self.assertNotEqual((await request(limiter, "/api/unknown", peer="192.0.2.3"))[0], 429)

    async def test_concurrency_limit_releases_slot(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def slow_app(scope, receive, send):
            entered.set()
            await release.wait()
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        limiter = AnalyticsRateLimit(slow_app, concurrency=1)
        first = asyncio.create_task(request(limiter, "/api/products"))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            status, headers, _ = await request(limiter, "/api/overview")
            self.assertEqual(status, 503)
            self.assertEqual(headers[b"retry-after"], b"1")
        finally:
            release.set()
            await first
        self.assertEqual((await request(limiter, "/api/overview"))[0], 204)


class OriginConfigurationTests(TestCase):
    def test_only_explicit_origins(self):
        self.assertEqual(approved_origins("http://localhost:3000, https://dashboard.example"),
                         ["http://localhost:3000", "https://dashboard.example"])
        for value in ("*", "https://*.example", "https://user@example", "https://example/path",
                      "null", "https://example:invalid"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                approved_origins(value)
