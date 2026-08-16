# Quantive — Data Retention & GDPR Policy

**Status:** v1.0 · **Applies to:** Quantive SaaS (blockchain compliance / transaction risk monitoring)

## 1. Data we process

| Category | Examples | Legal basis |
|----------|----------|-------------|
| Account data | email, name, password hash, role, refresh token | Contract (Art. 6(1)(b)) |
| Monitoring data | wallet addresses, transactions, risk scores | Contract + legitimate interest (Art. 6(1)(f)) |
| Alert/case data | alerts, cases, comments, reports | Legitimate interest (AML/CFT obligations) |
| Integrations | API keys/config, webhook endpoints | Contract |
| Audit logs | actions, IP, trace IDs | Legal obligation (Art. 6(1)(c)) |
| Billing | subscription plan, Stripe session/sub IDs | Contract |

## 2. Retention schedule

| Data | Retention | Notes |
|------|-----------|-------|
| Transactions / risk data | **5 years** | AML/CFT record-keeping obligations |
| Wallets | Life of account | Needed for ongoing monitoring |
| Alerts / cases / reports | **5 years** | Regulatory record-keeping |
| Audit logs | **12 months** | Security operations |
| Webhook deliveries | **90 days** | Operational debugging |
| Session/refresh tokens | Until rotated/expired | Security |
| Billing records | **6 years** | Tax/accounting (kept after erasure per Art. 17(3)(e)) |
| Erasure receipts | **6 years** | Proof of DSAR fulfilment |

## 3. Rights of the data subject

| Right | Implementation |
|-------|----------------|
| Access (Art. 15) | `GET /api/v1/account/export` — full org-scoped JSON export, credentials stripped |
| Erasure (Art. 17) | `POST /api/v1/account/erasure` — hard-deletes all org data in dependency order; returns a receipt with counts |
| Rectification (Art. 16) | User profile management endpoints |
| Portability (Art. 20) | Export endpoint returns machine-readable JSON |

## 4. Erasure scope

`POST /api/v1/account/erasure` deletes: comments → cases → alerts → reports →
transactions → wallets → webhook deliveries → webhook endpoints → integrations →
audit logs → users → roles → subscriptions → organization.

**Excluded from automatic erasure:** billing records required by tax law
(Art. 17(3)(e)) — Stripe retains subscription history on the payment processor;
export the Stripe ledger before erasing if you need a local copy.

## 5. Security & access

- Erasure and export endpoints are authenticated + organization-scoped
  (`authenticate` + `requireOrganization` middleware) — a user can only act on
  their own org's data.
- Passwords and refresh tokens are never included in exports.
- All destructive operations are idempotent: deleting an already-deleted org
  returns counts of zero.

## 6. Contact / DPO

DPO contact and privacy notice URL to be configured in the product settings.
