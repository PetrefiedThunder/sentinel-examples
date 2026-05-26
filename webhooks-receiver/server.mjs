/**
 * Tiny zero-dep HTTP server that receives + verifies Sentinel webhook deliveries.
 *
 * Run:
 *   export SENTINEL_WEBHOOK_SECRET=whsec_...
 *   node server.mjs
 *   # → Listening on http://localhost:8080
 *
 * Then expose it with ngrok / cloudflared (or just deploy this to any host),
 * and register the URL with Sentinel:
 *
 *   curl -X POST https://api.pauseapi.app/v1/webhooks \
 *     -H "Authorization: Bearer $SENTINEL_API_KEY" \
 *     -H "Content-Type: application/json" \
 *     -d '{"url":"https://<your-url>/sentinel"}'
 *
 * Now every approval decision lands here, signature-verified.
 */
import { createServer } from 'node:http';
import { createHmac, timingSafeEqual } from 'node:crypto';

const PORT = Number(process.env.PORT) || 8080;
const SECRET = process.env.SENTINEL_WEBHOOK_SECRET;

if (!SECRET) {
  console.error('SENTINEL_WEBHOOK_SECRET env var required.');
  console.error('Get one from the response of POST /v1/webhooks.');
  process.exit(1);
}

function verifySignature(rawBody, sentSig) {
  if (!sentSig || typeof sentSig !== 'string') return false;
  const expected = createHmac('sha256', SECRET).update(rawBody).digest('hex');
  if (sentSig.length !== expected.length) return false;
  return timingSafeEqual(Buffer.from(sentSig), Buffer.from(expected));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

const server = createServer(async (req, res) => {
  if (req.method !== 'POST' || req.url !== '/sentinel') {
    res.statusCode = 404;
    res.end('Not found. POST /sentinel');
    return;
  }

  const rawBody = await readBody(req);
  const sentSig = req.headers['x-sentinel-signature'];
  const eventType = req.headers['x-sentinel-event'];
  const deliveryId = req.headers['x-sentinel-delivery'];

  if (!verifySignature(rawBody, sentSig)) {
    console.error(
      `[${new Date().toISOString()}] ✗ SIGNATURE INVALID — rejecting ${deliveryId}`
    );
    res.statusCode = 401;
    res.end('Invalid signature');
    return;
  }

  let event;
  try {
    event = JSON.parse(rawBody.toString('utf8'));
  } catch {
    res.statusCode = 400;
    res.end('Malformed JSON');
    return;
  }

  console.log(`[${new Date().toISOString()}] ✓ ${eventType} (${deliveryId})`);
  console.log(`  action=${event.action_id}  decision=${event.decision}`);
  console.log(`  function=${event.function_name}  risk=${event.risk_level}`);
  console.log(`  decided_by=${event.decided_by}`);
  console.log(`  args=${JSON.stringify(event.arguments)}`);
  console.log();

  // ── This is where you'd do whatever your business logic needs ──
  // e.g. fan out to Slack, append to your audit DB, kick off a downstream
  // workflow, etc. Respond 2xx FAST — Sentinel retries 5xx with backoff.
  // ───────────────────────────────────────────────────────────────

  res.statusCode = 200;
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify({ ok: true }));
});

server.listen(PORT, () => {
  console.log(`Listening on http://localhost:${PORT}/sentinel`);
  console.log('Waiting for Sentinel webhook deliveries…');
});
