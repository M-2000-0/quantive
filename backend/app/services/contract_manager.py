"""Contract management for pilot/deal agreements."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pay_for_performance import SuccessFeeCalculator

try:
    from app.database import AsyncSessionLocal
except ImportError:  # app.database is sync-only; async session factory not configured yet
    AsyncSessionLocal = None

try:
    from app.models import Contract, Org, User
except ImportError:  # Contract/Org models not defined yet (WIP)
    Contract = None
    Org = None
    User = None


class ContractManager:
    """Manage contract lifecycle, terms, and fee invoicing for pilots/deals."""
    
    # Contract types
    CONTRACT_TYPE_PILOT = "pilot"
    CONTRACT_TYPE_ENTERPRISE = "enterprise"
    CONTRACT_TYPE_REVENUE_SHARE = "revenue_share"
    CONTRACT_TYPE_SUCCESS_FEE = "success_fee"
    
    # Contract statuses
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"
    STATUS_PENDING = "pending"
    
    # Duration defaults
    DEFAULT_PILOT_DURATION_MONTHS = 6
    MIN_PILOT_DURATION_MONTHS = 3
    MAX_PILOT_DURATION_MONTHS = 12
    
    @staticmethod
    async def create_pilot_contract(
        org_id: str,
        portfolio_size_usd: Decimal,
        duration_months: Optional[int] = None,
        fee_percentage: Decimal = Decimal("10"),
        min_savings_threshold: Decimal = Decimal("2"),
        max_fee_cap_percentage: Decimal = Decimal("0.5"),
        contract_type: str = CONTRACT_TYPE_PILOT,
        created_by: str = "system",
    ) -> Contract:
        """
        Create a new pilot contract with specified terms.
        
        Returns the created Contract object.
        """
        
        duration = duration_months or ContractManager.DEFAULT_PILOT_DURATION_MONTHS
        
        # Validate duration
        if duration < ContractManager.MIN_PILOT_DURATION_MONTHS:
            duration = ContractManager.MIN_PILOT_DURATION_MONTHS
        if duration > ContractManager.MAX_PILOT_DURATION_MONTHS:
            duration = ContractManager.MAX_PILOT_DURATION_MONTHS
        
        from app.models import Contract as ContractModel
        
        contract = ContractModel(
            org_id=org_id,
            contract_type=contract_type,
            status=ContractManager.STATUS_ACTIVE,
            title=f"Quantive Debt Optimization Pilot - {org_id}",
            description=f"6-month pilot optimization of ${portfolio_size_usd} sovereign debt portfolio with success-fee pricing",
            portfolio_notional=portfolio_size_usd,
            duration_months=duration,
            started_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=duration * 30),
            fee_percentage=fee_percentage,
            min_savings_threshold=min_savings_threshold,
            max_fee_cap_percentage=max_fee_cap_percentage,
            created_by=created_by,
            updated_at=datetime.now(timezone.utc),
        )
        
        # Save to database
        async def _save():
            async with AsyncSessionLocal() as db:
                db.add(contract)
                await db.flush()  # Get ID without full commit
                await db.refresh(contract)
                # Don't commit here - let the caller manage transaction
                return contract
        
        return await _save()
    
    @staticmethod
    async def calculate_and_invoice_fee(
        contract_id: str,
        optimization_job_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Calculate success fee for a completed optimization and generate invoice.
        
        Process:
        1. Retrieve contract and optimization job
        2. Get baseline cost (from contract terms or job metadata)
        3. Get optimized cost from job results
        4. Calculate success fee
        5. Generate invoice record
        6. Return calculation + invoice
        """
        
        if db is None:
            async with AsyncSessionLocal() as session:
                return await ContractManager.calculate_and_invoice_fee(
                    contract_id=contract_id,
                    optimization_job_id=optimization_job_id,
                    db=session,
                )
        
        # 1. Retrieve contract
        from app.models import Contract as ContractModel
        contract_result = await db.get(ContractModel, contract_id)
        if not contract_result:
            raise ValueError(f"Contract {contract_id} not found")
        
        if contract_result.status != ContractManager.STATUS_ACTIVE:
            raise ValueError(f"Contract {contract_id} is not active (status: {contract_result.status})")
        
        # 2. Retrieve optimization job
        from app.models import OptimizationJob as JobModel
        job_result = await db.get(JobModel, optimization_job_id)
        if not job_result:
            raise ValueError(f"Optimization job {optimization_job_id} not found")
        
        if job_result.org_id != contract_result.org_id:
            raise ValueError("Optimization job org_id doesn't match contract org_id")
        
        # 3. Determine baseline cost
        # Priority: contract.terms > job.baseline_cost_override > default baseline calculation
        baseline_cost = (
            Decimal(str(job_result.baseline_cost)) 
            if job_result.baseline_cost 
            else Decimal(str(contract_result.portfolio_notional or "0")) * Decimal("0.065")  # 6.5% default
        )
        
        # 4. Get optimized cost from job results
        optimized_cost = Decimal(str(job_result.financing_cost)) if job_result.financing_cost else Decimal("0")
        
        if optimized_cost == 0:
            # Try to get from job metrics
            if job_result.metrics:
                optimized_cost = Decimal(str(job_result.metrics.get("financing_cost", "0")))
        
        # 5. Calculate success fee
        fee_result = SuccessFeeCalculator.calculate_fee(
            baseline_cost=baseline_cost,
            optimized_cost=optimized_cost,
            fee_percentage=contract_result.fee_percentage,
            min_savings_threshold=contract_result.min_savings_threshold,
            max_fee_cap_percentage=contract_result.max_fee_cap_percentage,
            portfolio_notional=contract_result.portfolio_notional,
        )
        
        # 6. Generate invoice
        invoice = {
            "invoice_id": f"INV-{contract_result.id}-{optimization_job_id}-{datetime.utcnow().strftime('%Y%m%d')}",
            "contract_id": contract_id,
            "optimization_job_id": optimization_job_id,
            "baseline_cost": str(baseline_cost),
            "optimized_cost": str(optimized_cost),
            "savings_usd": str(fee_result["savings"]),
            "savings_percentage": str(fee_result["savings_percentage"]),
            "success_fee_usd": str(fee_result["fee"]),
            "fee_percentage": str(contract_result.fee_percentage),
            "eligible": fee_result["eligible"],
            "reason": fee_result["reason"],
            "issue_date": datetime.utcnow().isoformat(),
            "due_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "payment_status": "unpaid",
            "terms": {
                "fee_structure": f"{contract_result.fee_percentage}% of savings",
                "minimum_savings": f"{contract_result.min_savings_threshold}% threshold",
                "cap": f"{contract_result.max_fee_cap_percentage}% of portfolio notional",
            },
        }
        
        # 7. Update contract status if optimization completed
        if job_result.status == "completed":
            contract_result.status = ContractManager.STATUS_COMPLETED
            contract_result.completed_at = datetime.utcnow()
            # Don't commit here - caller manages transaction
        
        return {
            "contract": contract_result,
            "optimization_job": job_result,
            "fee_calculation": fee_result,
            "invoice": invoice,
        }
    
    @staticmethod
    async def check_contract_renewal(
        contract_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if contract is eligible for renewal or extension.
        
        Returns renewal info including:
        - days_until_expiry
        - eligible_for_renewal
        - suggested_terms
        - discount_for_early_renewal
        """
        
        async with AsyncSessionLocal() as db:
            from app.models import Contract as ContractModel
            contract_result = await db.get(ContractModel, contract_id)
            
            if not contract_result:
                return None
            
            now = datetime.now(timezone.utc)
            days_until_expiry = (contract_result.expires_at - now).days
            
            # Eligible for renewal if within 30 days of expiry
            eligible_for_renewal = days_until_expiry <= 30 and contract_result.status == ContractManager.STATUS_ACTIVE
            
            # Calculate renewal discount (20% if renewed before expiry, 10% after)
            if eligible_for_renewal and days_until_expiry <= 7:
                renewal_discount = Decimal("0.20")  # 20% discount
            elif eligible_for_renewal:
                renewal_discount = Decimal("0.10")  # 10% discount
            else:
                renewal_discount = Decimal("0")
            
            # Suggest new terms
            suggested_duration = max(
                ContractManager.MIN_PILOT_DURATION_MONTHS,
                min(ContractManager.MAX_PILOT_DURATION_MONTHS, contract_result.duration_months)
            )
            
            # Calculate new expiry
            new_expires_at = now + timedelta(days=suggested_duration * 30)
            
            return {
                "contract_id": contract_id,
                "org_id": str(contract_result.org_id),
                "current_terms": {
                    "contract_type": contract_result.contract_type,
                    "duration_months": contract_result.duration_months,
                    "fee_percentage": str(contract_result.fee_percentage),
                    "min_savings_threshold": str(contract_result.min_savings_threshold),
                    "max_fee_cap_percentage": str(contract_result.max_fee_cap_percentage),
                },
                "days_until_expiry": days_until_expiry,
                "eligible_for_renewal": eligible_for_renewal,
                "renewal_discount_percentage": renewal_discount * 100,
                "suggested_new_duration_months": suggested_duration,
                "new_expiry_date": new_expires_at.isoformat(),
                "current_expiry_date": contract_result.expires_at.isoformat(),
                "status": contract_result.status,
                "recommended_action": (
                    "renew_before_expiry" if eligible_for_renewal and days_until_expiry <= 7 
                    else "renew Soon" if eligible_for_renewal 
                    else "expire_and_negotiate"
                ),
            }
    
    @staticmethod
    async def get_contract_summary(
        contract_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a summarized view of contract status and metrics."""
        
        async with AsyncSessionLocal() as db:
            
            contract_result = await db.get(Contract, contract_id)
            if not contract_result:
                return None
            
            # Get related optimization jobs summary
            from app.models import OptimizationJob
            savings_expr = func.case(
                (
                    and_(
                        OptimizationJob.status == "completed",
                        OptimizationJob.baseline_cost.isnot(None),
                        OptimizationJob.financing_cost.isnot(None),
                    ),
                    OptimizationJob.baseline_cost - OptimizationJob.financing_cost,
                ),
                else_=0,
            )
            job_summary_result = await db.execute(
                select(
                    func.count(OptimizationJob.id).label("total_jobs"),
                    func.sum(
                        func.case(
                            (OptimizationJob.status == "completed", 1),
                            else_=0,
                        )
                    ).label("completed_jobs"),
                    func.sum(savings_expr).label("total_savings_usd"),
                )
                .where(OptimizationJob.contract_id == contract_id)
            )
            
            job_summary = job_summary_result.first()
            
            # Get renewal info
            renewal_info = await ContractManager.check_contract_renewal(contract_id)
            
            return {
                "contract_id": contract_id,
                "org_id": str(contract_result.org_id),
                "contract_type": contract_result.contract_type,
                "status": contract_result.status,
                "created_at": contract_result.created_at.isoformat(),
                "expires_at": contract_result.expires_at.isoformat(),
                "duration_months": contract_result.duration_months,
                "portfolio_notional_usd": str(contract_result.portfolio_notional),
                "fee_structure": {
                    "fee_percentage": str(contract_result.fee_percentage),
                    "min_savings_threshold": str(contract_result.min_savings_threshold),
                    "max_fee_cap_percentage": str(contract_result.max_fee_cap_percentage),
                },
                "metrics": {
                    "total_optimization_jobs": job_summary.total_jobs or 0,
                    "completed_jobs": job_summary.completed_jobs or 0,
                    "total_savings_usd": float(job_summary.total_savings_usd or 0),
                    "average_savings_per_job": float(
                        (job_summary.total_savings_usd or 0) / 
                        (job_summary.completed_jobs or 1)
                    ),
                },
                "renewal_info": renewal_info,
            }
    
    @staticmethod
    async def list_org_contracts(
        org_id: str,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List all contracts for an organization with filtering."""
        
        async with AsyncSessionLocal() as db:
            from app.models import Contract as ContractModel
            
            # Build query
            query = select(ContractModel).where(ContractModel.org_id == org_id)
            
            # Apply status filter
            if status_filter:
                query = query.where(ContractModel.status == status_filter)
            
            # Apply pagination
            query = query.offset(offset).limit(limit).order_by(desc(ContractModel.created_at))
            
            # Execute
            result = await db.execute(query)
            contracts = result.scalars().all()
            
            # Get total count for pagination
            count_query = select(func.count()).select_from(ContractModel).where(ContractModel.org_id == org_id)
            if status_filter:
                count_query = count_query.where(ContractModel.status == status_filter)
            total_count_result = await db.execute(count_query)
            total_count = total_count_result.scalar()
            
            return {
                "contracts": contracts,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count,
            }