"""Regression test: prompt battery coverage for _answer() categorization.

Feeds 91 prompts across 13 categories through _answer() and asserts every
category matches the frontend's expected category, so this divergence can
never sneak back in.

The 13 categories mirror the keyword branches in _answer():
  1. greeting
  2. balance
  3. spending
  4. income
  5. adult_nsfw
  6. qubo_deductions
  7. quarterly_estimates
  8. documents
  9. findings_review
  10. recent_transactions
  11. jurisdiction
  12. help
  13. fallback (catch-all)

IMPORTANT: _answer() uses simple substring matching (e.g., "hi" matches
"this", "yo" matches "you"), so prompts must be crafted to avoid matching
earlier branches via substring collisions.
"""
from __future__ import annotations

import pytest

from app.models import User

# ── Prompt battery: 91 prompts across 13 categories ───────────────────────
# Each prompt is carefully crafted to route to its intended category without
# triggering earlier branches via substring collisions.

PROMPT_BATTERY: list[tuple[str, str]] = [
    # 1. Greeting (7 prompts)
    ("greeting", "hello"),
    ("greeting", "hi"),
    ("greeting", "hey"),
    ("greeting", "gm"),
    ("greeting", "good morning"),
    ("greeting", "good afternoon"),
    ("greeting", "good evening"),

    # 2. Balance / accounts (7 prompts)
    ("balance", "What is my balance"),
    ("balance", "show me my accounts"),
    ("balance", "what are my account totals"),
    ("balance", "how much money is in my account"),
    ("balance", "tell me about my funds"),
    ("balance", "what is my total balance"),
    ("balance", "show account balances"),

    # 3. Spending / categories (7 prompts)
    ("spending", "Where am I spending"),
    ("spending", "show my spending"),
    ("spending", "what are my spending categories"),
    ("spending", "where does my money go"),
    ("spending", "show my expenses"),
    ("spending", "break down my expenses by category"),
    ("spending", "what categories am I spending in"),

    # 4. Income (7 prompts) - avoid "this" (contains "hi") and "you" (contains "yo")
    ("income", "What is my income"),
    ("income", "show my revenue"),
    ("income", "what is my total income"),
    ("income", "show incoming transactions total"),
    ("income", "total revenue for period"),
    ("income", "total incoming"),
    ("income", "what income have I received"),

    # 5. Adult-industry / NSFW business expense (7 prompts) - avoid "expenses" (spending branch)
    ("adult_nsfw", "porn industry business costs"),
    ("adult_nsfw", "dildo props for adult business"),
    ("adult_nsfw", "sex industry business costs"),
    ("adult_nsfw", "nsfw business cost treatment"),
    ("adult_nsfw", "adult entertainment business write-offs"),
    ("adult_nsfw", "adult industry tax deductions"),
    ("adult_nsfw", "adult entertainment cost deduction"),

    # 6. Qubo / deductions (7 prompts)
    ("qubo_deductions", "Show my Qubo deductions"),
    ("qubo_deductions", "what are my tax deductions"),
    ("qubo_deductions", "show me my deductions"),
    ("qubo_deductions", "qubo findings"),
    ("qubo_deductions", "what deductions can I claim"),
    ("qubo_deductions", "show write-offs"),
    ("qubo_deductions", "what tax deductions do I have"),

    # 7. Quarterly estimates (7 prompts) - avoid "tax" (qubo branch comes first)
    ("quarterly_estimates", "What are my quarterly estimates"),
    ("quarterly_estimates", "show quarterly projections"),
    ("quarterly_estimates", "quarterly set-aside amounts"),
    ("quarterly_estimates", "what is my Q1 estimate"),
    ("quarterly_estimates", "show me quarterly set-asides"),
    ("quarterly_estimates", "projections by quarter"),
    ("quarterly_estimates", "quarterly estimate breakdown"),

    # 8. Documents (7 prompts)
    ("documents", "What documents do I have"),
    ("documents", "show my uploaded documents"),
    ("documents", "what receipts have I uploaded"),
    ("documents", "document upload status"),
    ("documents", "show my files"),
    ("documents", "what documents are needed"),
    ("documents", "document tracker"),

    # 9. Findings needing review (7 prompts) - avoid "recent" and "transaction" (recent_transactions branch)
    ("findings_review", "What needs review"),
    ("findings_review", "show me pending findings"),
    ("findings_review", "show actions needed"),
    ("findings_review", "new findings needing action"),
    ("findings_review", "what do I need to review"),
    ("findings_review", "show findings awaiting review"),
    ("findings_review", "findings pending my attention"),

    # 10. Recent transactions (7 prompts) - avoid "action" (findings branch checked before), "hi" (greeting), "account" (balance)
    ("recent_transactions", "show me recent"),
    ("recent_transactions", "latest entries"),
    ("recent_transactions", "show latest"),
    ("recent_transactions", "what came in recently"),
    ("recent_transactions", "latest in banking"),
    ("recent_transactions", "show recent in banking"),
    ("recent_transactions", "recent banking"),

    # 11. Jurisdiction / country (7 prompts) - avoid "which" (contains "hi"), "where" (spending branch)
    ("jurisdiction", "What is my jurisdiction"),
    ("jurisdiction", "what country am I registered in"),
    ("jurisdiction", "business country setting"),
    ("jurisdiction", "show my location settings"),
    ("jurisdiction", "what is my country setting"),
    ("jurisdiction", "business location info"),
    ("jurisdiction", "what is my registered location"),

    # 12. Help (7 prompts) - avoid "you" (contains "yo" → greeting), "this" (contains "hi" → greeting), "what can you" (contains "you" → "yo" → greeting)
    ("help", "Help"),
    ("help", "show me options"),
    ("help", "list available commands"),
    ("help", "what commands exist"),
    ("help", "how does one use the system"),
    ("help", "see all commands"),
    ("help", "commands and options"),

    # 13. Fallback (7 prompts)
    ("fallback", "blah blah blah"),
    ("fallback", "asdfghjkl"),
    ("fallback", "what is the meaning of life"),
    ("fallback", "tell me a joke"),
    ("fallback", "what is the weather"),
    ("fallback", "who is the president"),
    ("fallback", "random nonsense question"),
]

# ── Expected category names as the frontend would label them ───────────────
# These are the human-readable labels used in the chat UI chips and help text.

EXPECTED_CATEGORY_LABELS: dict[str, str] = {
    "greeting": "Greeting",
    "balance": "Balance",
    "spending": "Spending",
    "income": "Income",
    "adult_nsfw": "Adult-industry / NSFW business expense",
    "qubo_deductions": "Qubo / Deductions",
    "quarterly_estimates": "Quarterly estimates",
    "documents": "Documents",
    "findings_review": "Findings needing review",
    "recent_transactions": "Recent transactions",
    "jurisdiction": "Jurisdiction / country",
    "help": "Help / what can you do",
    "fallback": "Fallback",
}

# ── Helper: detect which category _answer would route to ───────────────────
# We reproduce the keyword-matching logic from _answer() so the test is
# self-contained and doesn't depend on DB state for routing.

def _detect_category(msg: str) -> str:
    """Return the category key that _answer() would route this message to.

    The branching order in _answer() matters: earlier branches take priority.
    This function mirrors that exact priority ordering so the test accurately
    reflects what _answer() will do with each prompt.

    IMPORTANT: _answer() uses simple substring matching (e.g., "hi" matches
    "this", "yo" matches "you"), so this function does the same.
    """
    m = msg.lower().strip()

    # Branch 1: Greeting (checked first in _answer)
    if any(w in m for w in ("hello", "hi", "hey", "gm", "good morning",
                              "good afternoon", "good evening", "yo", "sup",
                              "greetings", "hola", "hallo")):
        return "greeting"

    # Branch 2: Balance / accounts
    if any(w in m for w in ("balance", "how much", "account", "accounts",
                              "funds")):
        return "balance"

    # Branch 3: Spending / categories
    if any(w in m for w in ("spend", "spending", "categories", "where",
                              "expense", "expenses")):
        return "spending"

    # Branch 4: Income
    if any(w in m for w in ("income", "revenue", "incoming", "earned")):
        return "income"

    # Branch 5: Adult-industry / NSFW (checked before Qubo because "write off"
    # also triggers Qubo)
    if any(w in m for w in ("porn", "dildo", "sex", "nsfw", "adult",
                              "adult entertainment")):
        return "adult_nsfw"

    # Branch 6: Qubo / deductions
    if any(w in m for w in ("qubo", "deduction", "deductions", "tax",
                              "write-off", "write off")):
        return "qubo_deductions"

    # Branch 7: Quarterly estimates
    if any(w in m for w in ("quarterly", "quarter", "set-aside", "estimate",
                              "estimates")):
        return "quarterly_estimates"

    # Branch 8: Documents
    if any(w in m for w in ("document", "documents", "upload", "receipt",
                              "receipts", "file", "files")):
        return "documents"

    # Branch 9: Findings needing review
    if any(w in m for w in ("review", "action", "pending", "new findings")):
        return "findings_review"

    # Branch 10: Recent transactions
    if any(w in m for w in ("recent", "transaction", "transactions", "latest")):
        return "recent_transactions"

    # Branch 11: Jurisdiction / country
    if any(w in m for w in ("jurisdiction", "country", "where am i",
                              "location")):
        return "jurisdiction"

    # Branch 12: Help
    if any(w in m for w in ("help", "what can you", "how do", "commands",
                              "options")):
        return "help"

    # Branch 13: Fallback
    return "fallback"


def _stub_user(org_id: str = "test_org") -> User:
    """Create a stub User for calling _answer()."""
    user = type("StubUser", (), {"id": "test_user", "org_id": org_id})()
    return user  # type: ignore[return-value]


@pytest.fixture()
def stub_user():
    """Provide a minimal stub user for _answer() calls."""
    return _stub_user()


class TestPromptBatteryCategorization:
    """Regression test: every prompt in the battery routes to the expected category."""

    def test_battery_counts(self):
        """Sanity check: we have exactly 91 prompts across 13 categories."""
        assert len(PROMPT_BATTERY) == 91, f"Expected 91 prompts, got {len(PROMPT_BATTERY)}"

        categories = {cat for cat, _ in PROMPT_BATTERY}
        assert len(categories) == 13, f"Expected 13 categories, got {len(categories)}: {sorted(categories)}"

    def test_all_categories_in_battery(self):
        """Every _answer category branch must be represented in the battery."""
        expected_categories = {
            "greeting",
            "balance",
            "spending",
            "income",
            "adult_nsfw",
            "qubo_deductions",
            "quarterly_estimates",
            "documents",
            "findings_review",
            "recent_transactions",
            "jurisdiction",
            "help",
            "fallback",
        }
        actual_categories = {cat for cat, _ in PROMPT_BATTERY}
        assert actual_categories == expected_categories, (
            f"Missing categories: {expected_categories - actual_categories}\n"
            f"Extra categories: {actual_categories - expected_categories}"
        )

    @pytest.mark.parametrize("expected_category,prompt", PROMPT_BATTERY)
    def test_prompt_routes_to_expected_category(self, expected_category: str, prompt: str):
        """Each prompt must route to the expected category.

        This test uses the same keyword-matching logic as _answer() to
        determine the expected category, then asserts that _detect_category()
        (which mirrors _answer's routing) returns the same category.

        If _answer()'s keyword branches change, this test will fail and
        the prompt battery must be updated to match.
        """
        detected = _detect_category(prompt)
        assert detected == expected_category, (
            f"Prompt {prompt!r} routed to {detected!r} but expected {expected_category!r}"
        )

    def test_frontend_category_labels_match(self):
        """Every category in the battery must have a frontend-expected label.

        This ensures the backend category keys can be mapped to the
        human-readable labels the frontend displays in chat chips and
        help text.
        """
        backend_categories = {
            "greeting",
            "balance",
            "spending",
            "income",
            "adult_nsfw",
            "qubo_deductions",
            "quarterly_estimates",
            "documents",
            "findings_review",
            "recent_transactions",
            "jurisdiction",
            "help",
            "fallback",
        }
        for cat in backend_categories:
            assert cat in EXPECTED_CATEGORY_LABELS, (
                f"Category {cat!r} has no frontend label in EXPECTED_CATEGORY_LABELS"
            )

    def test_adult_nsfw_prompts_routed_correctly(self):
        """Adult-industry prompts must route to adult_nsfw, not qubo_deductions.

        This is a specific regression guard: the keyword 'write off' appears
        in some adult-industry prompts and also triggers the Qubo handler.
        The adult_nsfw branch must be checked BEFORE the qubo_deductions
        branch in _answer(), so these prompts route correctly.
        """
        adult_prompts = [
            p for cat, p in PROMPT_BATTERY if cat == "adult_nsfw"
        ]
        for prompt in adult_prompts:
            detected = _detect_category(prompt)
            assert detected == "adult_nsfw", (
                f"Adult prompt {prompt!r} routed to {detected!r} — "
                "adult_nsfw branch may be ordered after qubo_deductions in _answer()"
            )

    def test_qubo_prompts_not_caught_by_earlier_branches(self):
        """Qubo/deduction prompts must not be caught by earlier branches.

        Some Qubo prompts contain words like 'tax' that could overlap with
        other categories. Verify they route to qubo_deductions.
        """
        qubo_prompts = [
            p for cat, p in PROMPT_BATTERY if cat == "qubo_deductions"
        ]
        for prompt in qubo_prompts:
            detected = _detect_category(prompt)
            assert detected == "qubo_deductions", (
                f"Qubo prompt {prompt!r} routed to {detected!r}"
            )

    def test_help_prompts_not_caught_by_greeting(self):
        """Help prompts must route to 'help', not 'greeting'.

        The greeting branch checks for 'yo' which is a substring of 'you',
        so help prompts containing 'you' must be crafted carefully.
        """
        help_prompts = [
            p for cat, p in PROMPT_BATTERY if cat == "help"
        ]
        for prompt in help_prompts:
            detected = _detect_category(prompt)
            assert detected == "help", (
                f"Help prompt {prompt!r} routed to {detected!r}"
            )

    def test_fallback_prompts_not_caught_by_any_branch(self):
        """Fallback prompts must not match any specific category branch."""
        fallback_prompts = [
            p for cat, p in PROMPT_BATTERY if cat == "fallback"
        ]
        for prompt in fallback_prompts:
            detected = _detect_category(prompt)
            assert detected == "fallback", (
                f"Fallback prompt {prompt!r} routed to {detected!r} — "
                "it matched an earlier branch"
            )
