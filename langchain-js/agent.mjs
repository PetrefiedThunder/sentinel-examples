/**
 * LangChain.js + Sentinel — a real agent with gated tools.
 *
 * Two tools:
 *   - check_balance(account)     ← read-only, NOT gated
 *   - wire_transfer(amount, to)  ← gated through Sentinel, requires human approval
 *
 * Run:
 *   export OPENAI_API_KEY=sk-...
 *   export SENTINEL_API_KEY=sk_live_...
 *   npm install
 *   npm start
 *
 * What happens:
 *   1. Agent receives: "send Alice $50,000 from account A"
 *   2. Agent calls check_balance — runs immediately (read-only, not gated)
 *   3. Agent calls wire_transfer — Sentinel pauses, emails your approver,
 *      waits up to 5 min
 *   4. You click Approve in the email
 *   5. wire_transfer actually runs, agent reports success
 */

import { ChatOpenAI } from '@langchain/openai';
import { tool } from '@langchain/core/tools';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { configure } from 'sentinel-oversight';
import { SentinelCallbackHandler } from 'sentinel-oversight/langchain';
import { z } from 'zod';

const SENTINEL_API_KEY = process.env.SENTINEL_API_KEY;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const APPROVER_EMAIL =
  process.env.APPROVER_EMAIL || 'you@yourdomain.com';

if (!SENTINEL_API_KEY) {
  console.error('SENTINEL_API_KEY env var required.');
  console.error('Get one from https://app.pauseapi.app/signup');
  process.exit(1);
}
if (!OPENAI_API_KEY) {
  console.error('OPENAI_API_KEY env var required.');
  process.exit(1);
}

// 1. Configure Sentinel once at startup
configure({ apiKey: SENTINEL_API_KEY });

// 2. Define tools — both look like normal LangChain tools.
// Sentinel only sees them when the SentinelCallbackHandler fires.

const checkBalance = tool(
  async ({ account }) => {
    // Pretend this hits your accounting system
    return JSON.stringify({ account, balance_usd: 73_400.55 });
  },
  {
    name: 'check_balance',
    description:
      'Get the current USD balance for an account. Read-only, safe to call.',
    schema: z.object({
      account: z.string().describe('Account identifier, e.g. "acct_acme"'),
    }),
  }
);

const wireTransfer = tool(
  async ({ amount_usd, from_account, to_account, memo }) => {
    // Real implementation would call stripe.transfers.create / Plaid / etc.
    // Here we just log and return a fake receipt — Sentinel already gated
    // this call BEFORE we got here.
    console.log(
      `  → executing wire: $${amount_usd.toLocaleString()} from ${from_account} → ${to_account}`
    );
    return JSON.stringify({
      transfer_id: `tr_${Math.floor(Date.now() / 1000)}`,
      amount_usd,
      from_account,
      to_account,
      memo,
      status: 'succeeded',
    });
  },
  {
    name: 'wire_transfer',
    description:
      'Move money between accounts. Requires human approval before executing.',
    schema: z.object({
      amount_usd: z.number().positive(),
      from_account: z.string(),
      to_account: z.string(),
      memo: z.string().optional(),
    }),
  }
);

// 3. Build the agent
const llm = new ChatOpenAI({
  apiKey: OPENAI_API_KEY,
  model: 'gpt-4o-mini',
  temperature: 0,
});

const agent = createReactAgent({
  llm,
  tools: [checkBalance, wireTransfer],
});

// 4. Run with the Sentinel callback — only `wire_transfer` is gated.
console.log('\n🤖 Agent receiving:');
const userPrompt =
  'Send Alice $50,000 from acct_acme to acct_alice_consulting. ' +
  'Memo: "Q2 consulting invoice". Check our balance first.';
console.log(`   "${userPrompt}"\n`);

const result = await agent.invoke(
  { messages: [{ role: 'user', content: userPrompt }] },
  {
    callbacks: [
      new SentinelCallbackHandler({
        riskLevel: 'high',
        approvers: [APPROVER_EMAIL],
        timeoutSeconds: 300,
        // Only gate the dangerous tool — let read-only tools run free.
        toolAllowlist: ['wire_transfer'],
      }),
    ],
  }
);

console.log('\n✅ Agent finished. Final message:\n');
const last = result.messages.at(-1);
console.log(`   ${last?.content ?? '(no content)'}\n`);
