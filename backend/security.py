"""Scoped service credentials and per-process request limits."""
import hmac
import os
from threading import BoundedSemaphore, Lock
from time import monotonic
from urllib.parse import urlsplit

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request
from starlette.responses import JSONResponse

bearer = HTTPBearer(auto_error=False)


def approved_origins(value: str) -> list[str]:
    origins = []
    for origin in filter(None, (item.strip() for item in value.split(","))):
        url = urlsplit(origin)
        if (url.scheme not in {"http", "https"} or not url.hostname
                or url.username is not None or url.password is not None
                or any(char.isspace() or char in "*?#\\" for char in origin)
                or origin != f"{url.scheme}://{url.netloc}"):
            raise ValueError("FRONTEND_ORIGIN must list explicit HTTP(S) origins.")
        _ = url.port  # Reject malformed ports at startup.
        origins.append(origin)
    return origins


def require_review_access(auth: HTTPAuthorizationCredentials | None = Security(bearer)) -> None:
    review_token = os.getenv("RAW_REVIEW_API_TOKEN", "")
    limited_token = os.getenv("LIMITED_API_TOKEN", "")
    if (len(review_token) < 32 or not review_token.isascii()
            or any(char.isspace() for char in review_token)
            or (limited_token and hmac.compare_digest(review_token.encode(), limited_token.encode()))):
        raise HTTPException(503, "Raw review access is disabled.")
    presented = auth.credentials.encode() if auth else b""
    if hmac.compare_digest(presented, review_token.encode()):
        return
    if len(limited_token) >= 32 and hmac.compare_digest(presented, limited_token.encode()):
        raise HTTPException(403, "Raw review permission required.")
    raise HTTPException(401, "Valid bearer credentials required.",
                        headers={"WWW-Authenticate": "Bearer"})


class AnalyticsRateLimit:
    """Fixed 60-second windows. Global quotas bound the number of peer entries."""

    def __init__(self, app, peer_limit=120, global_limit=600, raw_limit=30,
                 raw_global_limit=120, concurrency=16, clock=monotonic):
        self.app = app
        self.peer_limit = peer_limit
        self.global_limit = global_limit
        self.raw_limit = raw_limit
        self.raw_global_limit = raw_global_limit
        self.clock = clock
        self.lock = Lock()
        self.slots = BoundedSemaphore(concurrency)
        self.window = None
        self.total = 0
        self.raw_total = 0
        self.peers = {}
        self.raw_peers = {}

    def allow(self, peer, raw):
        with self.lock:
            now = int(self.clock())
            window, elapsed = divmod(now, 60)
            if window != self.window:
                self.window = window
                self.total = self.raw_total = 0
                self.peers.clear()
                self.raw_peers.clear()
            count = self.peers.get(peer, 0)
            raw_count = self.raw_peers.get(peer, 0)
            if (self.total >= self.global_limit or count >= self.peer_limit
                    or (raw and (raw_count >= self.raw_limit or self.raw_total >= self.raw_global_limit))):
                return False, 60 - elapsed
            self.total += 1
            self.peers[peer] = count + 1
            if raw:
                self.raw_total += 1
                self.raw_peers[peer] = raw_count + 1
            return True, 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        raw = scope["path"].rstrip("/") == "/api/reviews"
        allowed, retry_after = self.allow(request.client.host if request.client else "unknown", raw)
        if not allowed:
            response = JSONResponse({"detail": "Too many requests."}, status_code=429,
                                    headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"})
            await response(scope, receive, send)
            return
        if not self.slots.acquire(blocking=False):
            response = JSONResponse({"detail": "Analytics service is busy."}, status_code=503,
                                    headers={"Retry-After": "1", "Cache-Control": "no-store"})
            await response(scope, receive, send)
            return

        async def no_store(message):
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []), (b"cache-control", b"no-store")]
            await send(message)

        try:
            await self.app(scope, receive, no_store if raw else send)
        finally:
            self.slots.release()
