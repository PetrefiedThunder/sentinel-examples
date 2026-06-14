"""
Sentinel 60-second demo.

Run:   python demo.py

What happens:
  1. AI agent decides to wire $50,000.
  2. Sentinel pauses execution.
  3. You get an email at you@example.com.
  4. Click Approve in the email.
  5. The function unblocks and "runs".

The wire isn't real — but the gate is.
"""
import os
import time

from sentinel import configure, oversight


# ── Configure the SDK ───────────────────────────────────────────────
configure(
    api_key=os.environ["SENTINEL_API_KEY"],
    api_url="https://api.pauseapi.app",
)


# ── The risky function the agent wants to call ──────────────────────
@oversight(risk_level="high", timeout_seconds=300)
def wire_transfer(amount_cents: int, recipient: str, memo: str) -> dict:
    """
    Pretend this is `stripe.transfers.create(...)`.
    Without the @oversight decorator, the agent would run this autonomously.
    """
    print(f"  → executing wire: ${amount_cents/100:,.2f} → {recipient}")
    return {
        "id": f"tr_{int(time.time())}",
        "amount": amount_cents,
        "destination": recipient,
        "memo": memo,
        "status": "succeeded",
    }


# ── The "agent" deciding to act ─────────────────────────────────────
if __name__ == "__main__":
    print("\n🤖 Agent: I need to send a payment to a vendor.")
    print("   Calling wire_transfer($50,000, acct_acme_corp, 'Q2 invoice')…\n")
    print("⏸  Sentinel paused execution. Email sent to approver.")
    print("   Open your inbox → click Approve.\n")

    started = time.time()
    receipt = wire_transfer(
        amount_cents=50_000_00,
        recipient="acct_acme_corp",
        memo="Q2 invoice",
    )

    elapsed = time.time() - started
    print(f"\n✅ Human approved in {elapsed:.1f}s.")
    print(f"   Receipt: {receipt}\n")
