"""Track revenue share across organization and time periods."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import NULLIF, and_, desc, func, select, text

from app.database import AsyncSessionLocal
from app.models import Contract, OptimizationJob


class RevenueShareTracker:
    """Track and report revenue share statistics and analytics."""
    
    @staticmethod
    async def get_org_revenue_summary(
        org_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: str = "all",  # "all", "monthly", "quarterly", "yearly"
    ) -> Dict[str, Any]:
        """
        Get revenue summary for an organization over a time period.
        
        Returns total savings, fees earned, optimization stats, etc.
        """
        
        async def _summary():
            async with AsyncSessionLocal() as db:
                # Build date filters
                date_filter = ""
                if start_date and end_date:
                    date_filter = (
                        f"AND optimization_jobs.created_at >= '{start_date.isoformat()}' "
                        f"AND optimization_jobs.created_at <= '{end_date.isoformat()}'"
                    )
                
                # Base query components
                base_select = """
                    COUNT(DISTINCT optimization_jobs.id) as total_optimizations,
                    COALESCE(SUM((optimization_jobs.baseline_cost - optimization_jobs.financing_cost)::numeric), 0) as total_raw_savings,
                    COALESCE(SUM(
                        (CASE WHEN 
                            (optimization_jobs.baseline_cost - optimization_jobs.financing_cost) / 
                            NULLIF(optimization_jobs.baseline_cost, 0) >= {threshold}::numeric/100 
                        THEN (optimization_jobs.baseline_cost - optimization_jobs.financing_cost) * {fee_pct}::numeric/100 
                        ELSE 0 END)
                    ), 0) as total_fees_earned,
                    COALESCE(COUNT(DISTINCT contracts.org_id), 0) as orgs_served,
                """
                
                threshold = str(Decimal("2"))  # 2% default
                fee_pct = str(Decimal("10"))    # 10% default
                
                full_select = base_select.format(
                    threshold=threshold,
                    fee_pct=fee_pct,
                )
                
                # Full query with date filter
                query_text = f"""
                    SELECT {full_select}
                    FROM optimization_jobs
                    LEFT JOIN contracts ON optimization_jobs.contract_id = contracts.id
                    WHERE contracts.org_id = '{org_id}' {date_filter}
                    AND contracts.status = 'active'
                """
                
                result = await db.execute(text(query_text))
                row = result.first()
                
                # Calculate average savings
                avg_savings = (
                    (row.total_raw_savings / row.total_optimizations) 
                    if row.total_optimizations > 0 else Decimal("0")
                )
                
                return {
                    "org_id": org_id,
                    "period": {
                        "start": start_date.isoformat() if start_date else "start",
                        "end": end_date.isoformat() if end_date else "end",
                        "type": period,
                    },
                    "total_optimizations": row.total_optimizations or 0,
                    "total_raw_savings_usd": float(row.total_raw_savings) if row.total_raw_savings else 0,
                    "total_fees_earned_usd": float(row.total_fees_earned) if row.total_fees_earned else 0,
                    "average_savings_per_optimization_usd": float(avg_savings) if avg_savings else 0,
                    "average_fee_per_optimization_usd": (
                        float(row.total_fees_earned) / row.total_optimizations 
                        if row.total_optimizations > 0 else 0
                    ),
                    "organizations_served": row.orgs_served or 0,
                    "generated_at": datetime.utcnow().isoformat(),
                }
        
        return await _summary()
    
    @staticmethod
    async def get_top_performing_orgs(
        limit: int = 10,
        period_months: int = 12,
        min_optimizations: int = 1,
    ) -> List[Dict[str, Any]]:
        """Get top organizations by revenue generated."""
        
        async def _top():
            async with AsyncSessionLocal() as db:
                start_date = datetime.utcnow() - timedelta(days=period_months * 30)
                
                result = await db.execute(
                    select(
                        Contract.org_id,
                        func.count(OptimizationJob.id).label("total_optimizations"),
                        func.sum(
                            func.case(
                                (
                                    and_(
                                        OptimizationJob.status == "completed",
                                        OptimizationJob.baseline_cost.isnot(None),
                                        OptimizationJob.financing_cost.isnot(None),
                                    ),
                                    OptimizationJob.baseline_cost - OptimizationJob.financing_cost,
                                ),
                                else_=Decimal("0"),
                            )
                        ).label("total_savings_usd"),
                        func.sum(
                            func.case(
                                (
                                    and_(
                                        OptimizationJob.status == "completed",
                                        OptimizationJob.baseline_cost.isnot(None),
                                        OptimizationJob.financing_cost.isnot(None),
                                        (
                                            (OptimizationJob.baseline_cost - OptimizationJob.financing_cost) / 
                                            NULLIF(OptimizationJob.baseline_cost, 0) >= 0.02
                                        ),
                                        (OptimizationJob.baseline_cost - OptimizationJob.financing_cost) * Decimal("0.1"),
                                        else_=Decimal("0"),
                                    ),
                                ),
                                else_=Decimal("0"),
                            )
                        ).label("total_fees_earned_usd"),
                    )
                    .join(OptimizationJob, OptimizationJob.contract_id == Contract.id)
                    .where(Contract.org_id.isnot(None))
                    .where(OptimizationJob.created_at >= start_date)
                    .group_by(Contract.org_id)
                    .order_by(desc("total_fees_earned_usd"))
                    .limit(limit)
                )
                
                organizations = []
                for row in result:
                    organizations.append({
                        "org_id": str(row.org_id) if row.org_id else "unknown",
                        "total_optimizations": row.total_optimizations or 0,
                        "total_savings_usd": float(row.total_savings_usd) if row.total_savings_usd else 0,
                        "total_fees_earned_usd": float(row.total_fees_earned_usd) if row.total_fees_earned_usd else 0,
                        "average_savings_per_job": float(
                            row.total_savings_usd / row.total_optimizations
                        ) if row.total_optimizations > 0 else 0,
                        "fees_conversion_rate": float(
                            row.total_fees_earned_usd / row.total_savings_usd
                        ) if row.total_savings_usd > 0 else 0,
                    })
                
                return organizations
        
        return await _top()
    
    @staticmethod
    async def get_savings_distribution(
        org_id: str,
        period_months: int = 12,
    ) -> Dict[str, Any]:
        """Get distribution of savings percentages across all optimizations."""
        
        async def _distribution():
            async with AsyncSessionLocal() as db:
                start_date = datetime.utcnow() - timedelta(days=period_months * 30)
                
                # Get all completed jobs with savings data
                result = await db.execute(
                    select(
                        OptimizationJob.baseline_cost,
                        OptimizationJob.financing_cost,
                        OptimizationJob.created_at,
                    )
                    .join(Contract, OptimizationJob.contract_id == Contract.id)
                    .where(Contract.org_id == org_id)
                    .where(OptimizationJob.status == "completed")
                    .where(OptimizationJob.baseline_cost.isnot(None))
                    .where(OptimizationJob.financing_cost.isnot(None))
                    .where(OptimizationJob.created_at >= start_date)
                    .order_by(OptimizationJob.created_at)
                )
                
                rows = result.all()
                
                if not rows:
                    return {
                        "org_id": org_id,
                        "distribution": {},
                        "total_optimizations": 0,
                        "message": "No completed optimizations found for this period",
                    }
                
                # Categorize savings percentages
                categories = {
                    "excellent": {"threshold": Decimal("5"), "count": 0, "savings_usd": Decimal("0")},
                    "very_good": {"threshold": Decimal("3"), "count": 0, "savings_usd": Decimal("0")},
                    "good": {"threshold": Decimal("2"), "count": 0, "savings_usd": Decimal("0")},
                    "minimum": {"threshold": Decimal("0"), "count": 0, "savings_usd": Decimal("0")},
                }
                
                total_savings_usd = Decimal("0")
                total_optimizations = 0
                
                for row in rows:
                    if row.baseline_cost and row.baseline_cost > 0:
                        savings_pct = ((row.baseline_cost - row.financing_cost) / row.baseline_cost) * Decimal("100")
                        raw_savings = row.baseline_cost - row.financing_cost
                        
                        total_savings_usd += raw_savings
                        total_optimizations += 1
                        
                        # Categorize
                        if savings_pct >= categories["excellent"]["threshold"]:
                            categories["excellent"]["count"] += 1
                            categories["excellent"]["savings_usd"] += raw_savings
                        elif savings_pct >= categories["very_good"]["threshold"]:
                            categories["very_good"]["count"] += 1
                            categories["very_good"]["savings_usd"] += raw_savings
                        elif savings_pct >= categories["good"]["threshold"]:
                            categories["good"]["count"] += 1
                            categories["good"]["savings_usd"] += raw_savings
                        else:
                            categories["minimum"]["count"] += 1
                            categories["minimum"]["savings_usd"] += raw_savings
                
                return {
                    "org_id": org_id,
                    "period_months": period_months,
                    "total_optimizations": total_optimizations,
                    "total_savings_usd": float(total_savings_usd) if total_savings_usd else 0,
                    "distribution_by_category": {
                        key: {
                            "count": cat["count"],
                            "percentage_of_total": round(cat["count"] / total_optimizations * 100, 1) if total_optimizations > 0 else 0,
                            "total_savings_usd": float(cat["savings_usd"]) if cat["savings_usd"] else 0,
                            "percentage_of_savings": round(float(cat["savings_usd"] / total_savings_usd) * 100, 1) if total_savings_usd > 0 else 0,
                        }
                        for key, cat in categories.items()
                    },
                    "savings_statistics": {
                        "minimum_savings_pct": "0%",
                        "maximum_savings_pct": "TBD (calculate from data)",
                        "average_savings_pct": "TBD (calculate from data)",
                        "median_savings_pct": "TBD (calculate from data)",
                    },
                    "generated_at": datetime.utcnow().isoformat(),
                }
        
        return await _distribution()
    
    @staticmethod
    async def forecast_yearly_revenue(
        org_id: str,
        current_rate: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """Forecast yearly revenue based on historical trends."""
        
        async def _forecast():
            async with AsyncSessionLocal() as db:
                # Get historical data from last 12 months
                start_date = datetime.utcnow() - timedelta(days=365)
                
                result = await db.execute(
                    select(
                        func.extract('month', OptimizationJob.created_at).label("month"),
                        func.count(OptimizationJob.id).label("jobs_this_month"),
                        func.sum(
                            func.case(
                                (
                                    and_(
                                        OptimizationJob.status == "completed",
                                        OptimizationJob.baseline_cost.isnot(None),
                                        OptimizationJob.financing_cost.isnot(None),
                                    ),
                                    OptimizationJob.baseline_cost - OptimizationJob.financing_cost,
                                ),
                                else_=Decimal("0"),
                            )
                        ).label("monthly_savings_usd"),
                        func.sum(
                            func.case(
                                (
                                    and_(
                                        OptimizationJob.status == "completed",
                                        OptimizationJob.baseline_cost.isnot(None),
                                        OptimizationJob.financing_cost.isnot(None),
                                        (
                                            (OptimizationJob.baseline_cost - OptimizationJob.financing_cost) / 
                                            NULLIF(OptimizationJob.baseline_cost, 0) >= 0.02
                                        ),
                                        (OptimizationJob.baseline_cost - OptimizationJob.financing_cost) * Decimal("0.1"),
                                        else_=Decimal("0"),
                                    ),
                                ),
                                else_=Decimal("0"),
                            )
                        ).label("monthly_fees_usd"),
                    )
                    .join(Contract, OptimizationJob.contract_id == Contract.id)
                    .where(Contract.org_id == org_id)
                    .where(OptimizationJob.created_at >= start_date)
                    .group_by(func.extract('month', OptimizationJob.created_at))
                    .order_by(func.extract('month', OptimizationJob.created_at))
                )
                
                months_data = result.fetchall()
                
                # Build monthly breakdown
                monthly_breakdown = {}
                total_yearly_fees = Decimal("0")
                total_yearly_savings = Decimal("0")
                
                for month_row in months_data:
                    month_num = int(month_row.month) if month_row.month else 0
                    jobs = month_row.jobs_this_month or 0
                    savings = month_row.monthly_savings_usd or Decimal("0")
                    fees = month_row.monthly_fees_usd or Decimal("0")
                    
                    monthly_breakdown[month_num] = {
                        "jobs": jobs,
                        "savings_usd": float(savings) if savings else 0,
                        "fees_earned_usd": float(fees) if fees else 0,
                    }
                    
                    total_yearly_fees += fees
                    total_yearly_savings += savings
                
                # Fill in missing months with zeros
                for month in range(1, 13):
                    if month not in monthly_breakdown:
                        monthly_breakdown[month] = {
                            "jobs": 0,
                            "savings_usd": 0,
                            "fees_earned_usd": 0,
                        }
                
                # Sort by month
                sorted_breakdown = {
                    k: monthly_breakdown[k] for k in sorted(monthly_breakdown.keys())
                }
                
                # Calculate growth rate vs previous year
                prev_year_result = await db.execute(
                    select(
                        func.sum(
                            func.case(
                                (
                                    and_(
                                        OptimizationJob.status == "completed",
                                        OptimizationJob.baseline_cost.isnot(None),
                                        OptimizationJob.financing_cost.isnot(None),
                                    ),
                                    OptimizationJob.baseline_cost - OptimizationJob.financing_cost,
                                ),
                                else_=Decimal("0"),
                            )
                        ).label("prev_year_savings"),
                        func.sum(
                            func.case(
                                (
                                    and_(
                                        OptimizationJob.status == "completed",
                                        OptimizationJob.baseline_cost.isnot(None),
                                        OptimizationJob.financing_cost.isnot(None),
                                        (
                                            (OptimizationJob.baseline_cost - OptimizationJob.financing_cost) / 
                                            NULLIF(OptimizationJob.baseline_cost, 0) >= 0.02
                                        ),
                                        (OptimizationJob.baseline_cost - OptimizationJob.financing_cost) * Decimal("0.1"),
                                        else_=Decimal("0"),
                                    ),
                                ),
                                else_=Decimal("0"),
                            )
                        ).label("prev_year_fees"),
                    )
                    .join(Contract, OptimizationJob.contract_id == Contract.id)
                    .where(Contract.org_id == org_id)
                    .where(OptimizationJob.created_at >= datetime.utcnow() - timedelta(days=730))
                    .where(OptimizationJob.created_at < datetime.utcnow() - timedelta(days=365))
                )
                
                prev_year_row = prev_year_result.first()
                
                prev_year_savings = prev_year_row.prev_year_savings or Decimal("0")
                prev_year_fees = prev_year_row.prev_year_fees or Decimal("0")
                
                savings_growth_pct = (
                    ((total_yearly_savings - prev_year_savings) / prev_year_savings) * Decimal("100")
                    if prev_year_savings > 0 else Decimal("0")
                )
                fees_growth_pct = (
                    ((total_yearly_fees - prev_year_fees) / prev_year_fees) * Decimal("100")
                    if prev_year_fees > 0 else Decimal("0")
                )
                
                return {
                    "org_id": org_id,
                    "forecast_period": "12 months",
                    "yearly_projection": {
                        "total_savings_usd": float(total_yearly_savings),
                        "total_fees_earned_usd": float(total_yearly_fees),
                        "total_savings_volume_usd": float(total_yearly_savings),
                        "fees_as_percentage_of_savings": round(float(total_yearly_fees / total_yearly_savings) * 100, 1) if total_yearly_savings > 0 else 0,
                    },
                    "monthly_breakdown": sorted_breakdown,
                    "growth_vs_prev_year": {
                        "savings_growth_percentage": float(savings_growth_pct),
                        "fees_growth_percentage": float(fees_growth_pct),
                        "previous_year_savings_usd": float(prev_year_savings),
                        "previous_year_fees_usd": float(prev_year_fees),
                    },
                    "assumptions": {
                        "current_fee_percentage": float(current_rate or Decimal("10")),
                        "current_savings_threshold": "2%",
                        "projection_based_on": "last 12 months of optimization data",
                    },
                    "generated_at": datetime.utcnow().isoformat(),
                }
        
        return await _forecast()