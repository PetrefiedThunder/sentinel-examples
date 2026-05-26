# LangChain.js + Sentinel — gated agent

A real LangChain.js agent that calls two tools:

- `check_balance` — read-only, runs freely
- `wire_transfer` — gated through Sentinel; pauses for human approval before executing

The point: **you allowlist which tools require approval**, the rest run normally. Your agent stays fast, the dangerous things stay paused.

## Run

```bash
export SENTINEL_API_KEY=sk_live_...   # from https://app.pauseapi.app/signup
export OPENAI_API_KEY=sk-...
export APPROVER_EMAIL=you@yourdomain.com

npm install
npm start
```

## What you'll see

```
🤖 Agent receiving:
   "Send Alice $50,000 from acct_acme to acct_alice_consulting. ..."

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

```js
import { SentinelCallbackHandler } from 'sentinel-oversight/langchain';

await agent.invoke(input, {
  callbacks: [
    new SentinelCallbackHandler({
      riskLevel: 'high',
      approvers: ['alice@acme.com'],
      toolAllowlist: ['wire_transfer'],   // only this one
    }),
  ],
});
```

## Customizing the gate

| Option | Behavior |
|---|---|
| `toolAllowlist: ['X', 'Y']` | Only X and Y require approval. Everything else runs free. |
| `toolDenylist: ['cheap_lookup']` | Everything is gated EXCEPT cheap_lookup. |
| neither set | Every tool call requires approval (paranoid mode). |

## What gets sent to the approver

The approval email shows:
- Function name (`wire_transfer`)
- Risk level (`high`)
- All arguments JSON: `{"amount_usd": 50000, "from_account": "acct_acme", ...}`
- Approve / Reject buttons with signed magic links

So the approver sees exactly what's about to run before they click.

## On rejection or timeout

The callback throws inside LangChain's tool-execution loop, which aborts the chain. Your agent's final message will reflect "the action was rejected" rather than completing the transfer.

## Doesn't work with Python LangChain?

Yes it does — use the Python adapter instead:

```python
from sentinel.adapters.langchain import SentinelCallbackHandler

agent.run("...", callbacks=[SentinelCallbackHandler(risk_level="high")])
```

See the [Sentinel docs](https://pauseapi.app/docs#langchain).
