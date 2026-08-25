from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

try:
    from app.database import AsyncSession, get_db
except ImportError:  # app.database is sync-only; async session not configured yet (WIP)
    from app.database import get_db  # noqa: F401
    AsyncSession = None

from app.security.oauth2 import get_current_user
from app.services.contract_manager import ContractManager
from app.services.pay_for_performance import SuccessFeeCalculator, calculate_fee  # noqa: F401

try:
    from app.models import Contract  # noqa: F401
except ImportError:  # Contract model not defined yet (WIP)
    Contract = None

router = APIRouter(prefix="/pay-for-performance", tags=["pay-for-performance"])

@router.post("/calculate-fee", response_model=Dict[str, Any])
async def calculate_fee_endpoint(
    baseline_cost: Decimal,
    optimized_cost: Decimal,
    portfolio_notional: Optional[Decimal] = Query(
        default=None, 
        description="Portfolio notional for cap calculation",
        ge=0
    ),
    fee_percentage: Decimal = Query(
        default=Decimal("10"), 
        ge=0, le=100, 
        description="Success fee percentage of savings"
    ),
    min_savings_threshold: Decimal = Query(
        default=Decimal("2"), 
        ge=0, le=100, 
        description="Minimum savings % threshold"
    ),
    max_fee_cap_percentage: Decimal = Query(
        default=Decimal("0.5"), 
        ge=0, le=100, 
        description="Maximum fee as % of portfolio notional"
    ),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Calculate success fee for optimization results.
    
    **Pay-for-Performance Model:**
    - Fee = fee_percentage × (baseline_cost - optimized_cost)
    - Only charged if savings >= min_savings_threshold%
    - Fee capped at max_fee_cap_percentage × portfolio_notional
    """
    
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with an organization",
        )
    
    # Calculate fee
    fee_result = SuccessFeeCalculator.calculate_fee(
        baseline_cost=baseline_cost,
        optimized_cost=optimized_cost,
        fee_percentage=fee_percentage,
        min_savings_threshold=min_savings_threshold,
        max_fee_cap_percentage=max_fee_cap_percentage,
        portfolio_notional=portfolio_notional,
    )
    
    # Check eligibility and return response
    if not fee_result["eligible"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Savings threshold not met",
                "reason": fee_result["reason"],
                "savings_percentage": float(fee_result["savings_percentage"]),
                "required_threshold": float(min_savings_threshold),
                "fee": "0",
            }
        )
    
    return {
        "status": "success",
        "org_id": org_id,
        "calculation": fee_result,
        "timestamp": datetime.utcnow().isoformat(),
        "calculation_id": f"fee_{datetime.utcnow().timestamp()}",
    }

@router.post("/contract/create-pilot", response_model=Dict[str, Any])
async def create_pilot_contract_endpoint(
    portfolio_size_usd: Decimal = Query(
        ge=1000000,  # Minimum $1M portfolio
        description="Portfolio size in USD",
    ),
    duration_months: int = Query(
        default=6, 
        ge=3, le=12, 
        description="Pilot duration in months",
    ),
    fee_percentage: Decimal = Query(
        default=Decimal("10"), 
        ge=1, le=20, 
        description="Fee percentage of savings",
    ),
    min_savings_threshold: Decimal = Query(
        default=Decimal("2"), 
        ge=0.5, le=20, 
        description="Minimum savings threshold %",
    ),
    max_fee_cap_percentage: Decimal = Query(
        default=Decimal("0.5"), 
        ge=0.1, le=5, 
        description="Maximum fee as % of portfolio notional",
    ),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a new pilot contract with pay-for-performance terms."""
    
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with an organization",
        )
    
    # Create the contract
    contract = await ContractManager.create_pilot_contract(
        org_id=org_id,
        portfolio_size_usd=portfolio_size_usd,
        duration_months=duration_months,
        fee_percentage=fee_percentage,
        min_savings_threshold=min_savings_threshold,
        max_fee_cap_percentage=max_fee_cap_percentage,
        contract_type="pilot",
        created_by=current_user.get("username", "unknown"),
    )
    
    return {
        "status": "contract_created",
        "contract_id": str(contract.id),
        "contract": {
            "portfolio_size_usd": str(contract.portfolio_notional),
            "duration_months": contract.duration_months,
            "fee_percentage": str(contract.fee_percentage),
            "min_savings_threshold": str(contract.min_savings_threshold),
            "max_fee_cap_percentage": str(contract.max_fee_cap_percentage),
            "status": contract.status,
            "expires_at": contract.expires_at.isoformat() if contract.expires_at else None,
            "created_at": contract.created_at.isoformat(),
        },
        "terms_summary": {
            "model": "pay_for_performance",
            "fee_structure": f"{fee_percentage}% of savings above {min_savings_threshold}% threshold",
            "cap": f"{max_fee_cap_percentage}% of ${portfolio_size_usd:,.0f} notional = ${portfolio_size_usd * max_fee_cap_percentage / 100:,.2f} maximum fee",
            "no_upfront_fee": True,
            "payment_triggers": "upon optimization job completion with measurable savings",
        },
    }

@router.post("/contract/{contract_id}/generate-invoice", response_model=Dict[str, Any])
async def generate_invoice_endpoint(
    contract_id: str,
    optimization_job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Generate invoice for success fee on completed optimization."""
    
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with an organization",
        )
    
    # Calculate and invoice fee
    result = await ContractManager.calculate_and_invoice_fee(
        contract_id=contract_id,
        optimization_job_id=optimization_job_id,
        db=db,
    )
    
    invoice = result["invoice"]
    fee_calculation = result["fee_calculation"]
    
    # Check if fee is eligible
    if not fee_calculation["eligible"]:
        return {
            "status": "fee_not_eligible",
            "invoice": invoice,
            "reason": fee_calculation["reason"],
            "calculation": fee_calculation,
        }
    
    return {
        "status": "invoice_generated",
        "invoice": invoice,
        "fee_calculation": fee_calculation,
        "next_steps": [
            "Submit invoice to finance for processing",
            "Payment due within 30 days of issue date",
            "Fee payable only if savings verified in audit report",
            "Retain optimization report for audit trail",
        ],
    }

@router.get("/contract/{contract_id}/summary", response_model=Dict[str, Any])
async def contract_summary_endpoint(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get contract summary with metrics."""
    
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with an organization",
        )
    
    summary = await ContractManager.get_contract_summary(contract_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )
    
    # Verify ownership
    if summary["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contract does not belong to your organization",
        )
    
    return {
        "status": "summary_loaded",
        "contract_summary": summary,
    }

@router.get("/contracts/org", response_model=Dict[str, Any])
async def list_org_contracts_endpoint(
    status_filter: Optional[str] = Query(
        default=None, 
        description="Filter by status: active, completed, expired, cancelled",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List all contracts for organization."""
    
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with an organization",
        )
    
    contracts = await ContractManager.list_org_contracts(
        org_id=org_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    
    return {
        "status": "contracts_listed",
        "contracts": contracts["contracts"],
        "total_count": contracts["total_count"],
        "limit": contracts["limit"],
        "offset": contracts["offset"],
        "has_more": contracts["has_more"],
    }

@router.post("/contract/{contract_id}/check-renewal", response_model=Dict[str, Any])
async def check_contract_renewal_endpoint(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Check if contract is eligible for renewal."""
    
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not associated with an organization",
        )
    
    renewal_info = await ContractManager.check_contract_renewal(contract_id=contract_id)
    
    if not renewal_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )
    
    # Verify ownership
    if renewal_info["org_id"] != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contract does not belong to your organization",
        )
    
    return {
        "status": "renewal_check_complete",
        "renewal_info": renewal_info,
    }