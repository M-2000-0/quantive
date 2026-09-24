# Quantive Launch Readiness Test Plan

**Scope:** Quantive web platform — React SPA, FastAPI backend, local LLM/RAG pipeline (pre-production).
**Start:** Thursday 25 September 2026 (working days only). **Owner:** QA, with dev support for environment prerequisites.
**Baseline evidence:** Full-stack verification completed 24 September 2026. Four launch-blocking defects were found and fixed (commit `81bbb1c`): a login redirect loop, missing CSRF tokens on five POST flows, a runtime crash on the Personal dashboard, and US tax rules shown to non-US users. Backend test suite: 363 passing. Frontend suite: 126 of 133 passing (7 stale failures). This plan converts those findings into permanent regression checks.

---

## Phase 1 — Account Creation (Days 1–2: Sep 25, Sep 28)

| ID | Test case | Pass criteria | Fail criteria |
|---|---|---|---|
| AC-01 | Register with valid data | Account created; session cookies set; redirect to dashboard within 5 s | Any error shown, or redirect back to /login |
| AC-02 | Register with duplicate email | Specific inline "account exists" message; no second account created | Generic error, or HTTP 500 surfaced to user |
| AC-03 | Password rules | Short/weak passwords rejected with a field-level message | "pass" is accepted |
| AC-04 | Session persistence | Refresh /dashboard after sign-in; user stays signed in | Redirect to /login (regression check for the fixed login loop) |
| AC-05 | Logout | Cookies cleared; browser Back cannot reopen /dashboard | Authenticated content visible after logout |
| AC-06 | Forgot / reset password | Reset email within 2 min; link works once, then expires | No email after 5 min — log as environment blocker |

**Severity:** AC-01/04/05 failures = Critical (launch blocker). AC-02/03 = High. AC-06 = High if email service is unconfigured, otherwise Medium.

## Phase 2 — System Navigation (Days 2–3: Sep 28–29)

Scripted walkthrough of every sidebar route (25 primary routes plus the Personal section).

- **NAV-01** Protected routes redirect logged-out visitors to /login; no data leaks.
- **NAV-02** Every nav route renders content within 3 s — no blank screens, no console errors. Record route name + console output for any failure.
- **NAV-03** Personal dashboard renders score and open-task list. Fail criterion: the error boundary "Something went wrong" (regression check for the rebuilt dashboard).
- **NAV-04** Back/forward across five routes keeps correct state; no duplicate form submissions.
- **NAV-05** Marketing pages (/landing, /pricing, /terms) load without a session.

**Pass:** 100% of routes render; zero console errors on the ten highest-traffic routes. **Fail:** any blank screen (Critical); any console error (High).

## Phase 3 — Feature Verification (Days 3–6: Sep 29 – Oct 1)

Priority follows the revenue path — P0: onboarding, portfolio, optimization, AI advisor, billing. P1: banking, Qubo tax scan, notifications, imports/exports.

- **FEAT-01 (P0)** Portfolio lifecycle: create → add instrument → run optimization → results with risk scores. Pass: completes end-to-end; figures match the backend response. Fail: missing results or mismatched totals (Critical).
- **FEAT-02 (P0)** Sovereign AI advisor: ask three reference questions; each answers within 15 s and shows cited sources. *Area for further investigation:* the fine-tuned model alone often produces incoherent text; the RAG fallback currently carries answer quality. Decision required — see Recommendations.
- **FEAT-03 (P1)** Qubo tax scan on seeded transactions: a user with country "BD" receives BD rule references and never US-only rules (regression check for the jurisdiction fix).
- **FEAT-04 (P1)** PFM import: 1 MB and 9.5 MB files parse to a summary. Fail: a >10 MB file is accepted (must be rejected), or a malformed file crashes the page.
- **FEAT-05 (P0)** Billing: currently **blocked by missing Stripe keys** — an environment prerequisite, not a code defect. Re-test once keys are set: checkout session, webhook updates the subscription, quota enforcement works.
- **FEAT-06 (P1)** Notifications: trigger an alert → unread badge increments; mark-as-read survives a refresh.

**Pass:** every P0 flow passes on two consecutive runs. Any P0 failure = launch blocker; P1 failures = fix before launch or document accepted risk with stakeholder sign-off.

## Phase 4 — Cross-Platform Testing (Days 6–7: Oct 2, Oct 5)

Matrix: Chrome, Firefox, Safari, Edge (latest) on Windows/macOS; Safari on iOS and Chrome on Android (latest two OS versions); Electron desktop build (Windows).

- **XC-01** Re-run AC-01, NAV-03, FEAT-01, FEAT-02 in every matrix cell.
- **XC-02** Layouts at 375 px, 768 px, 1440 px: no horizontal scrolling, no truncated controls.
- **XC-03** Sign-in works on every tested browser; flag any browser that drops session cookies.
- **XC-04** Performance: 95th-percentile API response under 2 s; first visible content under 3 s on a throttled 4G connection.

**Pass:** identical functional behavior everywhere; cosmetic differences logged as Low.

## Timeline & Exit Criteria

| Working days | Dates | Phase | Gate to proceed |
|---|---|---|---|
| 1–2 | Sep 25, 28 | Account creation | AC-01/04/05 green twice |
| 2–3 | Sep 28–29 | Navigation | 100% route render |
| 3–6 | Sep 29 – Oct 1 | Features | All P0 green twice |
| 6–7 | Oct 2, 5 | Cross-platform | Matrix complete |

**Go/no-go (Oct 5):** zero open Critical or High defects; all P0 flows passed twice consecutively; environment prerequisites closed (Stripe keys + webhook, PostgreSQL for staging/production, custom domain with CORS allowlist — documented in DEPLOY.md, roughly one day combined).

## Summary of Findings & Recommendations

**Confirmed and fixed (24 Sep) — now permanent regression tests:** login loop → AC-04; five CSRF-missing POST endpoints → add a suite-wide check that every POST carries the CSRF header; Personal dashboard crash → NAV-03; cross-jurisdiction rule leakage → FEAT-03.

**Open items requiring decisions before launch:**
1. **Fix the 7 stale frontend tests (1–2 h).** They fail against code that demonstrably works in the live browser, so CI cannot currently be trusted as a launch gate.
2. **Resolve AI answer presentation.** Recommendation: make RAG-grounded answers primary (they cite sources and answer coherently today) and keep the fine-tuned model behind a feature flag until output quality improves.
3. **Close environment prerequisites:** Stripe, PostgreSQL, domain/CORS — ~1 day of configuration, owner: dev ops.
4. **Automate the P0 set.** Playwright is already installed; add a smoke suite covering register → dashboard → AI question → logout, run on every deploy. This turns the plan's critical path into a repeatable, automated gate rather than a one-off manual effort.
