# STARTUPS / QUANTIVE — AGENT TODO

**Models**: MiMo V2.5 (git/CI) · DeepSeek V4 Flash (migrations/tests) · Big Pickle (stripe) · Hy3 (GDPR)
**Updated**: 2026-08-16 · **Source**: PENDING.md audit

## INSTRUCTIONS — READ FIRST

You are the lead engineer on Quantive — a blockchain compliance/risk startup. It is NOT a git repo: zero commits, one unbacked folder.

Complete **ALL items below** in order of priority (Q-01 first — the entire startup is unbacked). For every item:

1. Read the relevant code/config first — do not guess.
2. Implement the fix or build the feature yourself.
3. Verify: run the project's typecheck/build/tests (if none exist, add the minimal check — e.g. a transpile check or smoke test).
4. Update this file: mark each item `[x]` and note what you did.
5. If an item is a DECISION (merge/archive/positioning), write your recommendation with reasons in the build log instead of shipping code blindly.

Constraints:
- Match the project's existing conventions; do not touch other projects' code.
- Do not delete user data. Archiving > deleting when unsure.
- Never commit secrets, keys, or .env files to git.
- Run the verification steps before finishing; report exact pass/fail counts.

When you finish, produce a complete build log in the EXACT style of `zambrano os/14ag.md` (Title · Date · Status · What was built · KEY ARCHITECTURAL DECISIONS table · ROADMAP STATUS checkboxes · FILE INVENTORY · WHAT'S NEXT) and save it as `QUANTIVE-BUILDLOG.md` inside this folder.

## PENDING ITEMS

⚠️ **Q-01 first — a drive failure kills the whole startup today.**

- [ ] [MiMo V2.5] Q-01 — git init + commit + push to GitHub (the entire startup is unbacked — this is first).
- [ ] [DeepSeek V4 Flash] Q-02 — prisma migrate dev + commit the migrations (prisma/migrations/ is EMPTY; the 14-model schema can't be applied anywhere).
- [ ] [MiMo V2.5] Q-03 — Let .github/workflows/ci.yml run and fix failures.
- [ ] [MiMo V2.5] Q-04 — npm install + run the 3 test files (database, crypto, helpers) and fix.
- [ ] [Big Pickle] Q-05 — Decide src/services/demo.ts: demo mode vs real seed.
- [ ] [Big Pickle] Q-06 — Verify Stripe checkout end-to-end (src/services/subscription.ts).
- [ ] [Hy3] Q-07 — Add data retention policy + deletion flow (GDPR/DSAR for wallet/transaction/risk data).
