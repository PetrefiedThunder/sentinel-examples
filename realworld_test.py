"""
Real-world scenario tests for Sentinel SDK 0.1.7.

Each test runs the actual SDK against the production API at api.pauseapi.app,
auto-approving (or auto-rejecting) via direct REST calls so we can exercise
the full client-server-decision round trip without manual intervention.

Run:
    SENTINEL_API_KEY=sk_live_… python realworld_test.py
"""
import asyncio
import os
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from sentinel import (
    ApprovalRejected,
    ApprovalTimeout,
    SentinelAPIError,
    SentinelClient,
    configure,
    oversight,
)

API = "https://api.pauseapi.app"
KEY = os.environ["SENTINEL_API_KEY"]
configure(api_key=KEY, api_url=API)

HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
http = httpx.Client(base_url=API, headers=HEADERS, timeout=30)


# ──────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────
def auto_decide(decision: str, delay: float = 1.0):
    """Find the latest pending approval and decide it after `delay` seconds."""
    def runner():
        time.sleep(delay)
        # find most recent pending action for this tenant
        for _ in range(20):
            r = http.get("/v1/approvals", params={"limit": 5})
            r.raise_for_status()
            data = r.json()
            pending = [a for a in data if a.get("decision") == "pending"]
            if pending:
                action_id = pending[0]["action_id"]
                http.post(
                    f"/v1/approvals/{action_id}/decision",
                    json={"decision": decision, "decided_by": "realworld-test"},
                ).raise_for_status()
                return action_id
            time.sleep(0.5)
        raise RuntimeError("no pending approval found")
    t = threading.Thread(target=runner, daemon=True)
    t.start()
    return t


def auto_decide_specific(action_id: str, decision: str, delay: float = 1.0):
    def runner():
        time.sleep(delay)
        http.post(
            f"/v1/approvals/{action_id}/decision",
            json={"decision": decision, "decided_by": "realworld-test"},
        ).raise_for_status()
    t = threading.Thread(target=runner, daemon=True)
    t.start()
    return t


def section(name: str):
    print(f"\n{'='*70}\n{name}\n{'='*70}")


PASS, FAIL = "✅", "❌"


# ══════════════════════════════════════════════════════════════════
# SCENARIO 1 — Happy path latency
# ══════════════════════════════════════════════════════════════════
section("1. Happy path — end-to-end latency (5 sequential approvals)")

@oversight(risk_level="medium", timeout_seconds=30)
def transfer(amount: int):
    return {"ok": amount}

latencies = []
for i in range(5):
    auto_decide("approved", delay=0.3)
    t0 = time.time()
    transfer(amount=i)
    latencies.append(time.time() - t0)

print(f"  per-call latencies (s): {[f'{x:.2f}' for x in latencies]}")
print(f"  p50={statistics.median(latencies):.2f}s  p95={max(latencies):.2f}s")
print(f"  {PASS} all 5 completed")


# ══════════════════════════════════════════════════════════════════
# SCENARIO 2 — Rejection raises ApprovalRejected
# ══════════════════════════════════════════════════════════════════
section("2. Rejection — must raise ApprovalRejected")

@oversight(risk_level="high", timeout_seconds=30)
def risky(x):
    return f"executed: {x}"

auto_decide("rejected", delay=0.5)
try:
    risky("should_not_run")
    print(f"  {FAIL} no exception raised — function executed despite rejection")
except ApprovalRejected as e:
    print(f"  {PASS} ApprovalRejected raised: {e!r}")
except Exception as e:
    print(f"  {FAIL} wrong exception: {type(e).__name__}: {e}")


# ══════════════════════════════════════════════════════════════════
# SCENARIO 3 — Async function support
# ══════════════════════════════════════════════════════════════════
section("3. Async function — decorator must handle `async def`")

@oversight(risk_level="medium", timeout_seconds=30)
async def async_send(to: str):
    await asyncio.sleep(0.01)
    return {"sent_to": to}

auto_decide("approved", delay=0.5)
result = asyncio.run(async_send(to="alice@acme.com"))
print(f"  result: {result}")
print(f"  {PASS} async path works" if result == {"sent_to": "alice@acme.com"} else f"  {FAIL}")


# ══════════════════════════════════════════════════════════════════
# SCENARIO 4 — Class method decoration
# ══════════════════════════════════════════════════════════════════
section("4. Class method — decorator must work as @method")

class PaymentsService:
    def __init__(self, account_id):
        self.account_id = account_id

    @oversight(risk_level="critical", timeout_seconds=30)
    def refund(self, charge_id):
        return {"account": self.account_id, "refunded": charge_id}

svc = PaymentsService(account_id="acct_xyz")
auto_decide("approved", delay=0.5)
out = svc.refund(charge_id="ch_abc123")
print(f"  result: {out}")
expected = {"account": "acct_xyz", "refunded": "ch_abc123"}
print(f"  {PASS} method binding preserved" if out == expected else f"  {FAIL}")


# ══════════════════════════════════════════════════════════════════
# SCENARIO 5 — Concurrent approvals (5 in flight at once)
# ══════════════════════════════════════════════════════════════════
section("5. Concurrency — 5 parallel @oversight calls")

@oversight(risk_level="medium", timeout_seconds=30)
def concurrent_task(idx):
    return f"task-{idx}-done"

# fire-and-forget approver: keep approving everything pending for 8 s
stop_flag = threading.Event()
def auto_approve_all():
    while not stop_flag.is_set():
        try:
            r = http.get("/v1/approvals", params={"limit": 20})
            for a in r.json():
                if a.get("decision") == "pending":
                    http.post(
                        f"/v1/approvals/{a['action_id']}/decision",
                        json={"decision": "approved", "decided_by": "auto"},
                    )
        except Exception:
            pass
        time.sleep(0.3)

approver_thread = threading.Thread(target=auto_approve_all, daemon=True)
approver_thread.start()

t0 = time.time()
with ThreadPoolExecutor(max_workers=5) as ex:
    futs = [ex.submit(concurrent_task, i) for i in range(5)]
    results = [f.result(timeout=30) for f in futs]
elapsed = time.time() - t0
stop_flag.set()

print(f"  results: {results}")
print(f"  total wall-clock: {elapsed:.2f}s for 5 concurrent calls")
ok = len(results) == 5 and all(f"task-{i}-done" in results for i in range(5))
print(f"  {PASS} all 5 ran in parallel" if ok else f"  {FAIL}")


# ══════════════════════════════════════════════════════════════════
# SCENARIO 6 — Non-JSON-serializable arguments
# ══════════════════════════════════════════════════════════════════
section("6. Non-serializable args — must fail gracefully")

@oversight(risk_level="low", timeout_seconds=30)
def takes_set(s):
    return list(s)

try:
    takes_set({1, 2, 3})
    print(f"  {FAIL} should have errored on un-serializable set()")
except (TypeError, SentinelAPIError) as e:
    print(f"  {PASS} caught as expected: {type(e).__name__}: {str(e)[:120]}")
except Exception as e:
    print(f"  ⚠️  unexpected exception type: {type(e).__name__}: {e}")


# ══════════════════════════════════════════════════════════════════
# SCENARIO 7 — Wrapped function raises after approval
# ══════════════════════════════════════════════════════════════════
section("7. Function exception — should propagate after approval")

@oversight(risk_level="medium", timeout_seconds=30)
def buggy():
    raise ValueError("internal bug")

auto_decide("approved", delay=0.5)
try:
    buggy()
    print(f"  {FAIL} no exception raised")
except ValueError as e:
    print(f"  {PASS} ValueError propagated: {e}")
except Exception as e:
    print(f"  {FAIL} wrong exception: {type(e).__name__}: {e}")


# ══════════════════════════════════════════════════════════════════
# SCENARIO 8 — Network failure (bad URL) graceful error
# ══════════════════════════════════════════════════════════════════
section("8. Bad API URL — graceful SentinelAPIError or connection error")

bad_client = SentinelClient.__new__(SentinelClient)
from sentinel.config import SentinelConfig
bad_client.config = SentinelConfig(api_key=KEY, api_url="https://does-not-exist-xyz.example.com")
bad_client._client = None
bad_client._aclient = None

try:
    bad_client.create_approval("test", {}, "low", ["a@b.com"], 10)
    print(f"  {FAIL} should have failed")
except (SentinelAPIError, httpx.ConnectError, httpx.HTTPError) as e:
    print(f"  {PASS} caught: {type(e).__name__}: {str(e)[:120]}")
except Exception as e:
    print(f"  ⚠️  unexpected: {type(e).__name__}: {e}")


# ══════════════════════════════════════════════════════════════════
# SCENARIO 9 — Timeout
# ══════════════════════════════════════════════════════════════════
section("9. Timeout — 6 s wait with no decision must raise ApprovalTimeout")

@oversight(risk_level="low", timeout_seconds=6)
def slow_decision():
    return "ran"

t0 = time.time()
try:
    slow_decision()
    print(f"  {FAIL} no timeout raised")
except ApprovalTimeout as e:
    elapsed = time.time() - t0
    print(f"  {PASS} ApprovalTimeout after {elapsed:.1f}s (configured 6s)")
except Exception as e:
    print(f"  {FAIL} wrong exception: {type(e).__name__}: {e}")


# ══════════════════════════════════════════════════════════════════
# SCENARIO 10 — Direct POST latency benchmark
# ══════════════════════════════════════════════════════════════════
section("10. Raw POST /v1/approvals latency (50 sequential)")

ts = []
for _ in range(50):
    t0 = time.time()
    r = http.post(
        "/v1/approvals",
        json={
            "function_name": "ping",
            "arguments": {"n": 1},
            "risk_level": "low",
            "approvers": ["a@b.com"],
            "timeout_seconds": 10,
        },
    )
    r.raise_for_status()
    ts.append(time.time() - t0)

print(f"  p50={statistics.median(ts)*1000:.0f}ms  p95={sorted(ts)[47]*1000:.0f}ms  p99={max(ts)*1000:.0f}ms")
print(f"  mean={statistics.mean(ts)*1000:.0f}ms  stdev={statistics.stdev(ts)*1000:.0f}ms")


print(f"\n{'='*70}\nDONE\n{'='*70}\n")
