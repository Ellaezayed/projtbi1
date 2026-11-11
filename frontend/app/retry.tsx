"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

export function Retry() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  return (
    <button className="retry" disabled={pending} onClick={() => startTransition(() => router.refresh())}>
      {pending ? "Connecting…" : "Try again"}
    </button>
  );
}
