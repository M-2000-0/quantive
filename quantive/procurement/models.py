# ── Procurement Data Models ───────────────────────────────────────────
# Pydantic models for procurement request/response structures.

from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class ProcurementItem(BaseModel):
  """Individual procurement item or line item."""
  id: str = Field(..., description="Unique item identifier")
  name: str = Field(..., description="Item description or name")
  category: str = Field(..., description="Procurement category (e.g., IT, construction, services)")
  estimated_value: float = Field(..., gt=0, description="Estimated contract value in USD")
  currency: str = Field("USD", description="Currency code")
  quantity: float = Field(1, gt=0, description="Quantity or scope size")
  unit: str = Field("each", description="Unit of measure")
  supplier: Optional[str] = Field(None, description="Current or proposed supplier")
  status: str = Field("pending", description="Procurement status: pending, active, completed, cancelled")
  priority: str = Field("medium", description="Priority: low, medium, high, critical")
  estimated_start: Optional[str] = Field(None, description="Expected start date (ISO)")
  estimated_end: Optional[str] = Field(None, description="Expected end date (ISO)")
  requirements: Optional[List[str]] = Field(None, description="Technical or functional requirements")
  constraints: Optional[List[str]] = Field(None, description="Constraints (budget, compliance, timeline)")
  unit_price: float = Field(0, ge=0, description="Unit price in USD")
  unit_price_estimate: float = Field(0, ge=0, description="Estimated unit price in USD")
  quality_score: Optional[float] = Field(None, ge=0, le=100, description="Quality score 0-100")


class ProcurementRequest(BaseModel):
  """Request to initiate or evaluate a procurement process."""
  id: str = Field(..., description="Unique request identifier")
  name: str = Field(..., description="Procurement request name/title")
  description: str = Field(..., description="Detailed description of needs")
  items: List[ProcurementItem] = Field(..., description="List of procurement items")
  budget_cap: Optional[float] = Field(None, gt=0, description="Maximum total budget in USD")
  timeline_days: Optional[int] = Field(None, gt=0, description="Maximum timeline in days")
  department: str = Field(..., description="Requesting department")
  requestor: str = Field(..., description="Requestor name/ID")
  tags: List[str] = Field(default_factory=list, description="Search/filter tags")
  created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
  status: str = Field("pending", description="Request status")


class ProcurementResponse(BaseModel):
  """Response from procurement analysis or optimization."""
  request_id: str = Field(..., description="Original request ID")
  analysis_id: str = Field(..., description="Analysis/run identifier")
  items_evaluated: int = Field(..., description="Number of items analyzed")
  waste_detected: float = Field(0, ge=0, description="Waste percentage identified")
  bottlenecks: List[Dict[str, Any]] = Field(default_factory=list, description="Identified bottlenecks")
  vendor_benchmarks: List[Dict[str, Any]] = Field(default_factory=list, description="Vendor benchmark results")
  forecast: Optional[Dict[str, Any]] = Field(None, description="Outcome forecast")
  recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
  status: str = Field("completed", description="Analysis status")
  completed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WasteAlert(BaseModel):
  """Alert identifying a type of waste in procurement."""
  id: str = Field(..., description="Unique alert identifier")
  request_id: str = Field(..., description="Related procurement request")
  waste_type: str = Field(..., description="Type of waste")
  severity: str = Field(..., description="Severity: low, medium, high, critical")
  title: str = Field(..., description="Short alert title")
  description: str = Field(..., description="Detailed description")
  monetary_impact: float = Field(0, ge=0, description="Estimated monetary impact in USD")
  detected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
  resolved: bool = Field(False, description="Whether alert has been resolved")
  recommendation: str = Field(..., description="Recommended action")


class VendorMetrics(BaseModel):
  """Vendor performance and metrics."""
  vendor_id: str = Field(..., description="Unique vendor identifier")
  vendor_name: str = Field(..., description="Vendor name")
  total_spend: float = Field(0, ge=0, description="Total spend with vendor")
  transaction_count: int = Field(0, ge=0, description="Number of transactions")
  avg_lead_time: float = Field(0, ge=0, description="Average lead time in days")
  on_time_delivery: float = Field(0, ge=0, le=100, description="On-time delivery percentage")
  quality_score: float = Field(0, ge=0, le=100, description="Quality score 0-100")
  cost_variance: float = Field(0, description="Cost variance percentage")
  risk_score: float = Field(0, ge=0, le=100, description="Risk score 0-100")
  categories: List[str] = Field(default_factory=list, description="Procurement categories")
  last_transaction: Optional[str] = Field(None, description="Last transaction date (ISO)")
  compliance_status: str = Field("compliant", description="Compliance status")


class BenchmarkData(BaseModel):
  """Benchmarking data for vendor or category comparison."""
  category: str = Field(..., description="Procurement category")
  metric: str = Field(..., description="Metric being benchmarked (e.g., cost, lead_time, quality)")
  unit: str = Field(..., description="Unit of measurement")
  values: List[float] = Field(..., description="Sample values from peer set")
  percentile: float = Field(0, ge=0, le=100, description="User's percentile rank")
  user_value: float = Field(..., description="User's value")
  peer_median: float = Field(..., description="Peer median value")
  peer_p25: float = Field(..., description="25th percentile")
  peer_p75: float = Field(..., description="75th percentile")
  peer_p10: float = Field(..., description="10th percentile")
  peer_p90: float = Field(..., description="90th percentile")
  insight: str = Field(..., description="Interpretive insight")
  category_benchmark: float = Field(..., description="Category benchmark/reference value")


class ForecastProjection(BaseModel):
  """Procurement outcome forecast projection."""
  projection_id: str = Field(..., description="Unique projection identifier")
  request_id: str = Field(..., description="Related procurement request")
  horizon_days: int = Field(..., gt=0, description="Forecast horizon in days")
  projected_total: float = Field(0, ge=0, description="Projected total cost in USD")
  projected_savings: float = Field(0, ge=0, description="Projected savings vs baseline in USD")
  confidence: float = Field(0, ge=0, le=100, description="Forecast confidence 0-100")
  scenarios: List[Dict[str, Any]] = Field(default_factory=list, description="Scenario outcomes")
  risk_factors: List[str] = Field(default_factory=list, description="Key risk factors")
  generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WasteType(str, Enum):
  """Enumerated waste types in procurement processes."""
  overpayment = "overpayment"
  maverick_spending = "maverick_spending"
  duplicate_orders = "duplicate_orders"
  contract_violations = "contract_violations"
  inefficient_lead_times = "inefficient_lead_times"
  poor_quality_rework = "poor_quality_rework"
  suboptimal_quantities = "suboptimal_quantities"
  redundant_approvals = "redundant_approvals"
  specification_creep = "specification_creep"
  unused_contracts = "unused_contracts"


class BottleneckType(str, Enum):
  """Enumerated bottleneck types in procurement workflow."""
  supplier_dependency = "supplier_dependency"
  approval_chain = "approval_chain"
  compliance_review = "compliance_review"
  budget_approval = "budget_approval"
  specification_revision = "specification_revision"
  contract_negotiation = "contract_negotiation"
  logistics_carrier = "logistics_carrier"
  payment_processing = "payment_processing"
  documentation = "documentation"


# Export enums for external use
WasteType = WasteType  # Already defined above as a str, Enum
BottleneckType = BottleneckType  # Already defined above as a str, Enum