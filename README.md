# Sentinel demo — 60-second recording

## What you'll record

A 60-second screen recording showing a Python agent that "wants" to wire $50,000, getting paused by Sentinel, an approval email, and the function unblocking when you tap Approve.

## Before you hit record

- Quit Slack / iMessage / anything that pings.
- Mac: `Cmd+Shift+5` → "Record Selected Portion" → drag a rectangle over the half of the screen with your terminal.
- Have your phone (or Mail.app on the laptop) visible.
- Open `1@christophersellers.com` mailbox and have it on screen too.

## Recording flow (60 seconds, no editing)

1. `./run.sh` ← shows pip install + script start
2. Terminal prints: "🤖 Agent: I need to send a payment…"
3. Terminal prints: "⏸ Sentinel paused execution. Email sent."
4. **Cut to your phone / Mail app** — approval email lands within ~2s
5. Tap the green **Approve** button
6. **Cut back to terminal** — "✅ Human approved in 7.4s. Receipt: tr_…"
7. Stop recording.

## After

Drop the file in iMovie. Add a `pauseapi.app` end-card. Done.

## Reset between takes

The demo runs cleanly N times in a row — each call creates a fresh approval. No state to reset.

If you want to fail-test (rejected/timeout), just don't click Approve and the script raises `ApprovalTimeout` after 5 min.
