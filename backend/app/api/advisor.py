"""AI Debt Advisor API endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/advisor", tags=["advisor"])


class AdvisorQuestion(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    country_code: str = Field(default="US", max_length=2)


@router.post("/ask")
def ask_advisor(
    data: AdvisorQuestion,
    user: User = Depends(get_current_user),
):
    """Ask the AI Debt Advisor a question."""
    from app.ai_advisor import DebtAdvisorAI
    advisor = DebtAdvisorAI()
    return advisor.answer(data.question, country_code=data.country_code.upper())


@router.get("/capabilities")
def get_capabilities():
    """Get the advisor's capabilities."""
    return {
        "capabilities": [
            {"category": "Market Timing", "examples": ["Should we issue now?", "Is the curve favorable?"]},
            {"category": "Risk Analysis", "examples": ["What are our risks?", "Rate hike exposure?"]},
            {"category": "Peer Comparison", "examples": ["Compare to G7", "How vs Brazil?"]},
            {"category": "Strategy", "examples": ["Optimal tenor?", "USD vs EUR?"]},
            {"category": "Credit Rating", "examples": ["What affects our rating?", "Upgrade path?"]},
            {"category": "Fiscal Analysis", "examples": ["Fiscal position?", "Sustainability outlook?"]},
            {"category": "Inflation", "examples": ["Inflation impact?", "ILB issuance?"]},
        ],
        "supported_countries": ["US", "UK", "JP", "DE", "FR", "IT", "CA", "CN", "IN", "BR", "RU", "AU", "KR", "MX", "ZA", "SA", "CH", "SE", "NO", "SG", "ID", "TR", "AR", "PL", "NL", "ES"],
    }
