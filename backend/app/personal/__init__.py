"""Quantive Personal — premium personal tax-intelligence product.

Isolation rules (enterprise-shared, product-separated):
- SHARED: auth (app.security), billing tables/engine (app.billing + app.models.billing),
  main FastAPI app, middleware, audit infra patterns.
- SEPARATE: all Personal data lives in its own database file
  (see app.personal.database / PERSONAL_DATABASE_URL) with its own Base.
  Never import Quantive (sovereign-debt) portfolio/optimization models here,
  and never query Personal tables from sovereign code paths.

Product principles enforced here:
- Never fabricate deductions, savings, rules, eligibility, or documents.
- Uncertain treatment is labeled Potentially relevant / Needs information, etc.
- Tax rules are versioned by (jurisdiction, tax_year) in TaxRule.
- Facts are structured records with source/confidence/date, user-editable.
"""

from app.personal.database import PersonalBase  # noqa: F401  (ensures Base import path)
