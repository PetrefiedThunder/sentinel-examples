# Sentinel — runnable examples

Live examples for [Sentinel](https://pauseapi.app), human-in-the-loop approval for AI agents.

Pick an example and follow its README — each one is self-contained.

| Example | Stack | What it shows |
|---|---|---|
| **[`python-demo`](#python-demo-the-60-second-recording)** | Python | Wire-transfer function gated by `@oversight`. The 60-sec demo video script. |
| **[`langchain-js`](./langchain-js)** | TypeScript / Node + LangChain.js | Real agent calling two tools — `check_balance` (free) and `wire_transfer` (gated). Allowlist approval. |
| **[`langgraph-py`](./langgraph-py)** | Python + LangGraph | Same two-tool agent in Python — `wire_transfer` gated via `SentinelToolGate.wrap()`. Allowlist approval. |
| **[`webhooks-receiver`](./webhooks-receiver)** | Node (zero deps) | Receive Sentinel approval webhooks and verify the HMAC signature. Production checklist + Express + FastAPI equivalents. |

Need an API key first? https://app.pauseapi.app/signup — free tier, no card.

---

## python-demo (the 60-second recording)

Files at the repo root (`demo.py`, `run.sh`, `realworld_test.py`) are the Python demo + the 10-scenario real-world test suite.

### Run

```bash
SENTINEL_API_KEY=sk_live_... ./run.sh
```

Terminal pauses → email lands → tap Approve → terminal unblocks with a fake transfer receipt. ~5 seconds end-to-end with a near-instant approver.

### Real-world test suite

```bash
SENTINEL_API_KEY=sk_live_... python realworld_test.py
```

Exercises 10 scenarios against the live API: latency, async, class methods, concurrency, rejection, timeout, network failure, JSON-serializability check. Used as the canonical "is the SDK production-grade" proof.

---

## langchain-js

See [`langchain-js/README.md`](./langchain-js) for full instructions. Quick version:

```bash
cd langchain-js
export SENTINEL_API_KEY=sk_live_...
export OPENAI_API_KEY=sk-...
export APPROVER_EMAIL=you@yourdomain.com
npm install
npm start
```

A LangChain.js agent receives "send Alice $50,000". It calls `check_balance` (runs immediately, read-only) then tries `wire_transfer` (pauses for your approval). Approve in the email → agent finishes the wire.

The Sentinel piece is one line:

```js
new SentinelCallbackHandler({
  riskLevel: 'high',
  approvers: ['alice@acme.com'],
  toolAllowlist: ['wire_transfer'],   // only this tool is gated
});
```

---

## Recording the demo video (for the launch)

Pre-recording checklist:
- Quit Slack / iMessage / anything that pings
- Mac: `Cmd+Shift+5` → "Record Selected Portion" → rectangle over your terminal
- Have your phone (or Mail.app) visible
- Open the approver inbox

60-sec take:
1. `./run.sh` (or `cd langchain-js && npm start`) — shows install + script start
2. Terminal prints "🤖 Agent: I need to send a payment…"
3. Terminal prints "⏸ Sentinel paused…"
4. **Cut to phone** — approval email arrives in ~2s
5. Tap the green **Approve** button
6. **Cut back to terminal** — "✅ Human approved in 3.3s. Receipt: tr_…"
7. Stop.

Drop into iMovie. Add a `pauseapi.app` end-card. Ship.
