"""LangGraph (Python) + Sentinel — a real agent with gated tools.

Two tools:
  - check_balance(account)                ← read-only, NOT gated
  - wire_transfer(amount, from, to, memo) ← gated through Sentinel,
                                            requires human approval

Run:
  export SENTINEL_API_KEY=sk_live_...
  export OPENAI_API_KEY=sk-...
  export APPROVER_EMAIL=you@yourdomain.com
  pip install -r requirements.txt
  python agent.py

What happens:
  1. Agent receives: "send Alice $50,000 from account A"
  2. Agent calls check_balance — runs immediately (read-only, not gated)
  3. Agent calls wire_transfer — Sentinel pauses, emails your approver,
     waits up to 5 min
  4. You click Approve in the email
  5. wire_transfer actually runs, agent reports success
"""

import json
import os
import sys
import time

# --- Env checks first, with friendly exits ---------------------------------

SENTINEL_API_KEY = os.environ.get("SENTINEL_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
APPROVER_EMAIL = os.environ.get("APPROVER_EMAIL")

if not SENTINEL_API_KEY:
    print("SENTINEL_API_KEY env var required.", file=sys.stderr)
    print("Get one from https://app.pauseapi.app/signup", file=sys.stderr)
    sys.exit(1)
if not OPENAI_API_KEY:
    print("OPENAI_API_KEY env var required.", file=sys.stderr)
    sys.exit(1)
if not APPROVER_EMAIL:
    print("APPROVER_EMAIL env var required (where approval emails go).", file=sys.stderr)
    sys.exit(1)

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

import sentinel
from sentinel.adapters.langgraph import SentinelToolGate

# --- 1. Configure Sentinel once at startup ----------------------------------

sentinel.configure(api_key=SENTINEL_API_KEY)

# --- 2. Build the gate -------------------------------------------------------
# The gate wraps plain Python callables. With tool_allowlist set, ONLY
# wire_transfer pauses for approval — check_balance is returned unwrapped
# and runs free.

gate = SentinelToolGate(
    risk_level="high",
    approvers=[APPROVER_EMAIL],
    timeout_seconds=300,  # wait up to 5 min for the human
    tool_allowlist=["wire_transfer"],  # only this tool is gated
)

# --- 3. Define the underlying functions ------------------------------------


def check_balance_fn(account: str) -> str:
    # Pretend this hits your accounting system
    return json.dumps({"account": account, "balance_usd": 73_400.55})


def wire_transfer_fn(
    amount_usd: float, from_account: str, to_account: str, memo: str = ""
) -> str:
    # Real implementation would call stripe.transfers.create / Plaid / etc.
    # Here we just log and return a fake receipt — Sentinel already gated
    # this call BEFORE we got here.
    print(f"  → executing wire: ${amount_usd:,.0f} from {from_account} → {to_account}")
    return json.dumps(
        {
            "transfer_id": f"tr_{int(time.time())}",
            "amount_usd": amount_usd,
            "from_account": from_account,
            "to_account": to_account,
            "memo": memo,
            "status": "succeeded",
        }
    )


# --- 4. Wrap with the gate, THEN register as LangGraph tools ----------------
# gate.wrap() pauses the call for human approval. We pass function_name
# explicitly so it matches the allowlist. check_balance is not on the
# allowlist, so we never wrap it — it runs free. (Wrapping it anyway would
# also be fine: wrap() returns the function unchanged for ungated names.)


@tool
def check_balance(account: str) -> str:
    """Get the current USD balance for an account. Read-only, safe to call."""
    return check_balance_fn(account)


gated_wire_transfer = gate.wrap(wire_transfer_fn, function_name="wire_transfer")


@tool
def wire_transfer(
    amount_usd: float, from_account: str, to_account: str, memo: str = ""
) -> str:
    """Move money between accounts. Requires human approval before executing."""
    # This pauses for Sentinel approval before wire_transfer_fn runs.
    return gated_wire_transfer(
        amount_usd=amount_usd,
        from_account=from_account,
        to_account=to_account,
        memo=memo,
    )


# --- 5. Build the agent -----------------------------------------------------

llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini", temperature=0)

agent = create_react_agent(llm, [check_balance, wire_transfer])

# --- 6. Run -----------------------------------------------------------------

user_prompt = (
    "Send Alice $50,000 from acct_acme to acct_alice_consulting. "
    'Memo: "Q2 consulting invoice". Check our balance first.'
)

print("\n🤖 Agent receiving:")
print(f'   "{user_prompt}"\n')
print("⏸  When the agent calls wire_transfer, Sentinel pauses and emails")
print(f"   {APPROVER_EMAIL} — go approve it.\n")

result = agent.invoke({"messages": [{"role": "user", "content": user_prompt}]})

print("\n✅ Agent finished. Final message:\n")
last = result["messages"][-1]
print(f"   {getattr(last, 'content', '(no content)')}\n")
