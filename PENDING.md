# QUANTIVE — Pending Work

Measured state (2026-08-08): Code ~75% · Deploy ~40% · Monetize ~65% · Tests: 3 files, not runnable (no node_modules). On standby by choice.

## Critical

1. **NOT a git repo.** Zero commits, no remote. The entire startup lives in one unbacked folder. `git init` + commit + push to GitHub first.
2. **Zero committed migrations.** `prisma/migrations/` is EMPTY. The schema (14 models) can't be applied to any real database. Run `prisma migrate dev` and commit the result — deployment is impossible without it.
3. **CI exists but never runs** (no repo). Once on GitHub, `.github/workflows/ci.yml` will test backend + frontend. Let it run and fix failures.
4. **Tests unrun** — node_modules absent; 3 test files (database, crypto, helpers). `npm install`, run `npm test`, fix.
5. **Seed data** — `src/services/demo.ts` hardcodes wallets/mixers. Decide if it's a demo mode or real seed.

## Monetization

- Stripe wired: `src/services/subscription.ts` (17 hits), Subscription model with stripeCustomerId/stripeSubscriptionId. Verify checkout end-to-end.
- The founding-pilot offer (One pager.txt) is written — good. The missing piece is a deployed URL to send prospects to.

## Deployment

- Dockerfile, docker-compose.yml, nginx conf, built `dist/` (241 files) all exist. Needs: git, migrations, a host, real .env.

## Blind spots (things even senior devs miss)

- **Compliance data = regulated data**: you store wallet addresses, transactions, and risk scores of individuals. GDPR/DSAR obligations, data retention limits, and breach liability apply. No retention policy or deletion flow exists — regulators will ask.
- **False-negative risk is the product risk, not false-positives**: your pitch mocks 90%+ false-positive screening tools. But in compliance, a false NEGATIVE (missing a sanctioned wallet) is catastrophic for the client. Your scoring dimensions must be auditable per-decision (the human-readable reason codes help — make them the headline, not the accuracy claim).
- **Blockchain data source cost is a hidden line item**: running chain nodes or paid APIs (Alchemy/QuickNode) for 6 chains at real volume is a monthly cost most pitches omit. Model it into pricing before launch.
- **Standby is fine, but unbacked is not**: even parked, put it in git. One drive failure and Quantive is gone.
