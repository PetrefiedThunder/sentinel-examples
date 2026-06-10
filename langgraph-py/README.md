# LangGraph (Python) + Sentinel — gated agent

A real LangGraph agent that calls two tools:

- `check_balance` — read-only, runs freely
- `wire_transfer` — gated through Sentinel; pauses for human approval before executing

The point: **you allowlist which tools require approval**, the rest run normally. Your agent stays fast, the dangerous things stay paused.

## Run

```bash
export SENTINEL_API_KEY=sk_live_...   # from https://app.pauseapi.app/signup
export OPENAI_API_KEY=sk-...
export APPROVER_EMAIL=you@yourdomain.com

pip install -r requirements.txt
python agent.py
```

## What you'll see

```
🤖 Agent receiving:
   "Send Alice $50,000 from acct_acme to acct_alice_consulting. ..."

⏸  When the agent calls wire_transfer, Sentinel pauses and emails
   you@yourdomain.com — go approve it.

(agent calls check_balance — runs immediately, balance returned)
(agent calls wire_transfer — Sentinel pauses, emails APPROVER_EMAIL)
```

Open the email. Tap **Approve**. Back in the terminal:

```
  → executing wire: $50,000 from acct_acme → acct_alice_consulting

✅ Agent finished. Final message:
   The wire transfer of $50,000 from acct_acme to acct_alice_consulting
   has been successfully processed. Transfer ID: tr_1779781234.
```

## The one line that makes this work

```python
from sentinel.adapters.langgraph import SentinelToolGate

gate = SentinelToolGate(
    risk_level="high",
    approvers=["alice@acme.com"],
    tool_allowlist=["wire_transfer"],   # only this one
)

gated_fn = gate.wrap(wire_transfer_fn, function_name="wire_transfer")
```

`gate.wrap()` works on plain Python callables — sync or async — so it plugs into any LangGraph style: `create_react_agent` tools, `StateGraph` nodes, or custom `ToolNode` functions. The adapter never imports langgraph, so it works with any LangGraph version.

## Customizing the gate

| Option | Behavior |
|---|---|
| `tool_allowlist=["X", "Y"]` | Only X and Y require approval. Everything else runs free. |
| `tool_denylist=["cheap_lookup"]` | Everything is gated EXCEPT cheap_lookup. |
| neither set | Every tool call requires approval (paranoid mode). |

## What gets sent to the approver

The approval email shows:
- Function name (`wire_transfer`)
- Risk level (`high`)
- All arguments JSON: `{"amount_usd": 50000, "from_account": "acct_acme", ...}`
- Approve / Reject buttons with signed magic links

So the approver sees exactly what's about to run before they click.

## On rejection or timeout

The wrapper raises `sentinel.exceptions.ApprovalRejected` inside the tool call, which surfaces through LangGraph's tool execution. Your agent's final message will reflect "the action was rejected" rather than completing the transfer.

## Using LangChain.js instead?

See the [`langchain-js`](../langchain-js) example — same scenario, gated via `SentinelCallbackHandler`.

See the [Sentinel docs](https://pauseapi.app/docs#langchain).
