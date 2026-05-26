# Sentinel — webhook receiver example

Zero-dependency Node server that receives Sentinel webhook deliveries and verifies the HMAC-SHA256 signature.

## Why this matters

When Sentinel POSTs your URL on `approval.approved` / `approval.rejected`, the payload could in theory come from anyone who guessed your URL. **Always verify the `X-Sentinel-Signature` header before trusting the body.** This example shows the exact pattern.

## Run

```bash
# 1. Get a webhook secret by creating an endpoint
export SENTINEL_API_KEY=sk_live_...

curl -X POST https://api.pauseapi.app/v1/webhooks \
  -H "Authorization: Bearer $SENTINEL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-public-url/sentinel"}'

# → response contains:
#   "secret": "whsec_KpTnJSpy..."   ← store this; we won't show it again

# 2. Run the receiver locally
export SENTINEL_WEBHOOK_SECRET=whsec_KpTnJSpy...
node server.mjs

# 3. Expose it with ngrok (or deploy anywhere)
ngrok http 8080
# → forwards to https://abc123.ngrok-free.app/sentinel
#   (replace the URL in your /v1/webhooks call with this)
```

## What it does

- Listens on `POST /sentinel`
- Reads the raw body **before** parsing JSON (signature is over raw bytes)
- Computes `HMAC-SHA256(secret, rawBody)` and `timingSafeEqual` against `X-Sentinel-Signature`
- Rejects with `401` if invalid
- Logs the event and returns `200 {ok:true}` if valid

## Production checklist

- [ ] Verify signature on **every** delivery
- [ ] Read the raw body before parsing JSON (signature is over raw bytes)
- [ ] Use `timingSafeEqual` (not `===`) to avoid timing attacks
- [ ] Respond with 2xx fast — Sentinel retries 5xx + network errors 3 times with exponential backoff (1s, 4s, 16s)
- [ ] Idempotency: the same `X-Sentinel-Delivery` id may arrive twice during retries. Dedupe by storing it.
- [ ] Don't trust the body until verification passes — drop unsigned requests at the edge

## Express equivalent

If you're already using Express, drop this in:

```js
import express from 'express';
import { createHmac, timingSafeEqual } from 'node:crypto';

const app = express();

// Must use express.raw to keep the body as a Buffer for signature verification
app.post(
  '/sentinel',
  express.raw({ type: 'application/json' }),
  (req, res) => {
    const sentSig = req.headers['x-sentinel-signature'];
    const expected = createHmac('sha256', process.env.SENTINEL_WEBHOOK_SECRET)
      .update(req.body)
      .digest('hex');
    if (
      typeof sentSig !== 'string' ||
      sentSig.length !== expected.length ||
      !timingSafeEqual(Buffer.from(sentSig), Buffer.from(expected))
    ) {
      return res.status(401).end('Invalid signature');
    }
    const event = JSON.parse(req.body.toString('utf8'));
    // do something with the event
    res.json({ ok: true });
  }
);
```

## Python (FastAPI) equivalent

```python
import hashlib, hmac, os
from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI()
SECRET = os.environ["SENTINEL_WEBHOOK_SECRET"]

@app.post("/sentinel")
async def receive(request: Request, x_sentinel_signature: str = Header()):
    raw = await request.body()
    expected = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_sentinel_signature):
        raise HTTPException(401, "Invalid signature")
    event = await request.json()
    # do something with the event
    return {"ok": True}
```
