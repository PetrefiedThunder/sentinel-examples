# Security Policy

## Reporting a vulnerability

**Do not file a public GitHub issue for security vulnerabilities.**

Email **security@regengine.co** with:

- A description of the issue
- Steps to reproduce
- Your assessment of the impact (data exposure, account takeover, etc.)
- An optional PGP key for our reply

We acknowledge within 48 hours and aim to ship a fix or mitigation within:

| Severity | Response | Fix target |
|---|---|---|
| Critical (full account takeover, payment fraud, secret leak) | 24h | 72h |
| High (privilege escalation, PII leak) | 48h | 7 days |
| Medium (CSRF, info disclosure) | 5 days | 30 days |
| Low (best-practice issues) | 14 days | next release |

## Disclosure

After a fix is shipped, we'll credit you in the release notes unless you ask to remain anonymous. We support coordinated disclosure — give us a reasonable window before public posting.

## Scope

In scope:
- `*.pauseapi.app` (API, dashboard, marketing)
- All published packages (`sentinel-oversight` on PyPI, `sentinel-oversight` on npm)
- Webhook signing, magic-link tokens, audit-log integrity

Out of scope:
- Findings requiring physical access or social engineering of staff
- Denial-of-service via brute traffic (we have rate limits — pls don't try)
- Vulnerabilities in 3rd-party dependencies already disclosed upstream (file with that project; we'll patch on their release)

## Bounty

No formal bounty program yet. We'll send a thank-you note and a Sentinel Pro credit. As we grow, this graduates to a real bounty.

## Public PGP key

Available on request via security@regengine.co.
