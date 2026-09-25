# Quantive Launch Demo Script

**Audience:** investors, sovereign-debt stakeholders, procurement/technical evaluators
**Duration:** 12–15 min (core) / 18 min (with Banking + Qubo add-on)
**Environment:** local demo, `demo_stress@test.com` / `DemoPass123!`
**Golden rule:** every number you say should be on screen. All data below is real, live from the demo workspace — market figures (BTC, AAPL, Treasury yields) are fetched live at demo time, so expect small drift. Portfolio/banking numbers are stable unless the seed is reset.

---

## 0 · Pre-flight checklist

**T-24h (once):**

- [ ] Backend up: `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- [ ] Frontend up: `cd frontend && npm run dev` → http://localhost:5173
- [ ] Seed idempotent (safe to re-run): `cd backend && python scripts/seed_demo_account.py`
  - Adds whatever is missing; `--reset-banking` rebuilds banking if demo data got dirty
- [ ] Full walkthrough rehearsal: login → dashboard → optimization → 4 AI questions → banking → Qubo

**T-15 min (every time):**

- [ ] `curl http://127.0.0.1:8000/api/health` → `200`
- [ ] **Warm the AI** (first call loads the embedding model, ~10–15s; later calls ~1–2s):
  open the demo, send one throwaway chat message (e.g. "hello"), wait for the reply
- [ ] Fresh browser profile or incognito (clean localStorage), viewport ~1440×900
- [ ] Backup screenshots (or a screen recording) of dashboard, optimization result, and 2 AI answers — see Fallbacks

---

## Scene 1 — Login (1 min)

**Do:** http://localhost:5173/login → sign in with the demo credentials.

**Talking points:**

- "Everything you'll see is the user's actual workspace — this login grants org-scoped access to one sovereign debt office's data. Every API call is authenticated, CSRF-protected, and RBAC-checked; banking data never leaks across organizations."
- "No cloud dependency in the AI path — inference and retrieval run locally."

**Fallback:** if login loops or 401s, hard-refresh once (stale session cookie). If still failing, restart backend and retry once; then use the backup recording.

---

## Scene 2 — Dashboard (3 min)

**Do:** land on **Overview**. Point at each widget in order.

**On screen (seeded values):**

- **$1.6B TOTAL DEBT · 4.4% WEIGHTED COUPON · 10 INSTRUMENTS · 26/100 RISK SCORE**
- Maturity distribution ladder (2026 → 2056)
- Priority task: **"T-Bill Rolling Program matures — USD 60,000,000 · 67 days"**
- Risk breakdown: Refinancing 17, Currency 40, Interest-rate 24 (all "Low" bands)
- Market Pulse card with live sentiment

**Talking points:**

- "A debt office's whole position in one glance: $1.59B outstanding across 10 instruments in 3 currencies. The weighted coupon of 4.4% implies roughly $70M of annual interest cost — that's the number we optimize."
- "The platform doesn't wait for you to notice risk — that T-Bill maturing in 67 days is already a task with a link to the portfolio. Refinancing risk 17/100 comes from the share of the book maturing inside 2 years."
- "Everything is computed live from the database, not hardcoded: add an instrument and every number, the ladder and the risk scores move."

**Fallback:** if the wizard modal appears ("Portfolio Ready!"), click **Skip for now** and continue — don't run the optimization from here if you want the narrated version in Scene 3. If Market Pulse shows stale data, it's a cached provider snapshot; say "market data refreshes on our data pipeline schedule" and move on.

---

## Scene 3 — Live optimization (4 min)

**Do:** click **New report** (top right) → lands on `/optimizations/new`. Keep the form defaults (portfolio preselected, minimize-cost objective), optionally bump scenarios to 1,000, then submit. The job starts live.

**While it runs (polls every ~2s):** narrate what's happening:

**Talking points:**

- "We're generating 1,000 Monte Carlo rate and FX scenarios, then three solver backends — greedy, mean-variance, and scenario-based — compete on the same objectives: 40% financing cost, 25% refinancing risk, 20% rate risk, 15% currency risk, under constraints like max 8% financing cost and max 40% floating."
- "This is the core IP: not a black box — every strategy comes with an explanation of which constraint bound and which objective drove it."
- "A 30–60 second turnaround on a $1.6B book is what makes this usable in an actual debt office meeting."

**On completion:** open the result — strategies ranked with metrics, allocation table, benchmark comparison.

- "The ranked strategies show the trade-off frontier — cost today vs refinancing exposure in 2027–2031 where our ladder bunches up."

**Fallbacks:**

- Job stuck/failed: check `backend/backend_verify.log`; re-run from **New report** once. If the queue is wedged, pivot: "let me show you a completed run" → open any COMPLETED job from `/optimizations` (run one before the demo to guarantee one exists).
- Nothing completes at all: use the backup screenshots, and demo the **quick optimizer API** instead: `POST /api/optimize-debt/quick` returns a diversified 5Y/10Y/30Y allocation using the live Treasury curve in ~3s ("this is our fast path; the full engine adds scenario generation").

---

## Scene 4 — AI advisor Q&A (4 min) ⭐ centerpiece

**Do:** click the gold **Quantive AI** button (bottom right). Ask these **in this order**, typing them live:

**Q1 — "What is the price of Bitcoin?"** *(live market data)*
**Expected:** `Live market data (fetched just now): • BTC-USD: $84,4xx (▲/▼ x.xx%)` + knowledge-base note + "5 sources" chip.
**Say:** "Live quotes are wired straight into the assistant — same for stocks: ask for AAPL and you get the real price."
**Fallback:** if quotes fail (provider rate limit), the answer degrades to knowledge-base text — say "the quote provider is rate-limited right now; in production this is our market-data pipeline" and move to Q2, which doesn't depend on third parties.

**Q2 — "What happens to my debt if rates rise 50bps?"** *(portfolio-aware + live yields)* ⭐
**Expected (seeded book):**
```
Scenario: rates rise 50bps (parallel shift) — your book:
• Repricing share: ~17% of the book (floating-rate + maturities within 2y) resets within the year
• Annual interest cost: $69.6M → $70.9M (+$1.3M/yr)
• Mark-to-market on the locked book: -$98.3M (≈ −D×Δy×P, D≈12.4y — first-order estimate)
• Most of your book is fixed-rate, so a hike mostly hits you through refinancing at maturity…
```
plus the live snapshot ($1.59B / 10 instruments / USD 60% GBP 31% EUR 9%) and today's Treasury yields.
**Say:** "It knows the user's actual positions — the 17% repricing share is the floating and short-dated slice of *this* book, and the minus-$98M is a first-order duration impact."
**Then — memory moment:** type just **"what about 100bps?"** — no restating the question. The assistant remembers the exchange and returns the 100bps scenario (+$2.6M/yr). "Follow-ups work — the conversation carries context; I never had to repeat myself."
**Then — chain a second shock:** type **"and if the euro depreciates 10% on top of that?"** — the assistant composes the FX move onto the *same 100bps scenario*: EUR exposure ($140M, ~9% of book) restates to $126M, and a **combined first-order MTM (rates + FX)** line appears. "Rate and currency shocks compose — exactly how a treasury desk stress-tests."
**Then — persistence moment:** reload the page, reopen the assistant — the full thread is still there (history button top-left of the panel lists and switches earlier conversations). "Conversations survive reloads and are stored per user — nothing to re-ask, nothing lost."
**Fallback:** if the scenario block is missing (only textbook text), the portfolio snapshot didn't load — refresh the page once (session cookie) and retry; if still generic, the org's portfolio lookup failed, re-run the seeder and re-login.

**Q3 — "Summarize my portfolio"** *(position awareness)*
**Expected:** total, weighted coupon → ~$69.6M annual interest, weighted maturity 12.4y, currency mix, nearest maturity T-Bill 2026-12-01, longest 2056 gilt.
**Say:** "The same assistant is the analyst's shortcut — no navigation needed, the numbers come from the workspace, not from a slide deck."

**Q4 — "Explain debt sustainability analysis"** *(grounded RAG with citations)*
**Expected:** clean cited prose from the knowledge base, "📚 sources" expandable with IMF/DSF sources.
**Say:** "When it's not about my data, it answers from our sovereign-finance knowledge base with citations — grounded retrieval, not hallucination. Everything ships on-prem: no data leaves the deployment."

**Q5 (bonus) — "What are my balances?"** *(bridges to Banking)*
**Expected:** Operating $23.8M / Reserve $4.1M / Yield $1.5M — **Total: $29,436,554**.
**Say:** "And it reads the banking ledger too — which is where we're going next."

**Fallbacks:** any 403/CSRF glitch — the widget auto-retries; if a message errors, refresh and resend. If answers feel slow (>10s), the embedding model went cold — send one throwaway message before the audience returns.

---

## Scene 5 — Banking + Qubo (optional, 3 min)

**Do:** sidebar **Banking** → `/banking/app`.

**On screen:** $29.4M available · $0 fees on $888K moved · 90-day forecast +$2.0M · three accounts · live transaction feed (payroll, AWS, utilities, travel, a pending invoice).

- **Say:** "Zero transaction fees by design — the ledger is double-entry, idempotent, and org-scoped. The AI CFO cards are rule-based estimates from real flows: runway, payroll coverage, tax set-aside."

**Do:** sidebar **Qubo Tax** → `/qubo/workspace`.

**On screen:** **31 open findings · $302,560 potentially deductible** · findings with rule IDs (QBIZ-2026-travel, -utilities…), requirements, and Accept/Dismiss.

- **Say:** "Qubo scanned 40 posted outflows against versioned jurisdiction rules — note the honesty contract: 'potentially deductible', never promised savings. Each finding links its rule, requirements and documents. Quarterly estimates and a CPA export are one click."

**Fallback:** if findings look stale, hit **Scan ledger for deductions →** live (it's fast and idempotent — demo-worthy in itself).

---

## Closing (30 sec)

- "One platform: the debt book, the cash, the tax angle — with an AI advisor that has all three in context."
- **CTA:** pilot program — we onboard one portfolio with your real curve and constraints in under a week.

---

## Appendix A — Recovery playbook

| Symptom | Fix |
|---|---|
| Backend down / `health:000` | restart backend (see README command), wait ~25s, re-check health |
| Frontend down | `cd frontend && npm run dev` (port 5173) |
| Empty $0 dashboard | `cd backend && python scripts/seed_demo_account.py` (idempotent; add `--reset-banking` to rebuild banking) |
| AI first reply very slow | normal on cold start (~15s); always warm up pre-demo |
| AI answers without portfolio block | refresh page (session), re-ask; else re-run seeder + re-login |
| Live quotes failing | provider rate limit — degrade gracefully, pivot to Q2 (portfolio math is local) |
| Optimization job stuck | check `backend/backend_verify.log`; retry once; else show a pre-run COMPLETED job |
| Login loop | hard refresh; if persistent, clear site data and log in again |

## Appendix B — Verified Q&A reference (values at time of writing)

| Question | Source | Expected numbers |
|---|---|---|
| "rates rise 50bps?" | live positions | +$1.3M/yr interest, −$98.3M MTM, 17% repricing share |
| "rates rise 100bps?" | live positions | +$2.6M/yr interest, −$196.7M MTM |
| follow-up: "what about 100bps?" | conversation memory | resolves to the 100bps scenario, +$2.6M/yr |
| "and if the euro depreciates 10% on top of that?" | chained FX what-if | same 100bps scenario + EUR −10% → $140M→$126M, combined MTM line (rates + FX) |
| page reload + reopen assistant | conversation persistence | last thread restored from DB, full history + sources |
| "Summarize my portfolio" | live positions | $1.59B · 4.38% coupon · 12.4y · USD 60/GBP 31/EUR 9 |
| "price of Bitcoin/AAPL" | live quotes | real-time price ± day change |
| "my balances" | banking ledger | $29.44M total across 3 accounts |
| "Qubo deductions" | findings table | 31 new findings, $302,560 open |
| "debt sustainability" | knowledge base | cited IMF/DSF prose |

## Appendix C — One-breath elevator version

"Quantive gives a debt management office its whole position — $1.6B across 10 instruments here — with live risk scoring, a 30-second optimization engine over a thousand Monte Carlo scenarios, and an AI advisor that answers questions like 'what happens to my debt if rates rise 50bps' from your actual book, your live market data, and a cited sovereign-finance knowledge base. Banking and tax sit on the same ledger. All of it runs on-prem."
