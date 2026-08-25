import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class UserCreate(BaseModel):
    email: EmailStr = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    org_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError("Password must contain at least one special character")
        # Check against common passwords
        common = {'password', 'password1', 'qwerty', '12345678', 'letmein', 'admin', 'welcome', 'monkey', 'dragon', 'master'}
        if v.lower() in common:
            raise ValueError("This password is too common. Please choose a stronger one.")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    org_id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefresh(BaseModel):
    refresh_token: str


class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class OrgResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class DebtInstrumentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    instrument_type: str
    currency: str = Field(default="USD", min_length=3, max_length=3)
    principal_outstanding: float = Field(..., gt=0, le=1e15)
    coupon_rate: float = Field(..., ge=-10, le=100)
    maturity_date: str
    issue_date: str
    is_callable: bool = False
    call_date: Optional[str] = None
    call_price: Optional[float] = None
    spread_bps: float = Field(default=0.0, ge=-1000, le=5000)

    @field_validator("maturity_date", "issue_date", "call_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not DATE_PATTERN.match(v):
            raise ValueError(f"Date must be in YYYY-MM-DD format, got: {v}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.upper().strip()
        valid = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "INR", "BRL"}
        if v not in valid:
            raise ValueError(f"Invalid currency. Must be one of: {', '.join(sorted(valid))}")
        return v


class DebtInstrumentResponse(BaseModel):
    id: str
    name: str
    instrument_type: str
    currency: str
    principal_outstanding: float
    coupon_rate: float
    maturity_date: str
    issue_date: str
    is_callable: bool
    call_date: Optional[str]
    call_price: Optional[float]
    spread_bps: float
    created_at: datetime

    class Config:
        from_attributes = True


class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    instruments: list[DebtInstrumentCreate] = []


class PortfolioResponse(BaseModel):
    id: str
    name: str
    description: str
    org_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    instruments: list[DebtInstrumentResponse] = []

    class Config:
        from_attributes = True


class PortfolioListResponse(BaseModel):
    portfolios: list[PortfolioResponse]
    total: int


class ScenarioConfig(BaseModel):
    num_scenarios: int = Field(default=10000, ge=100, le=50000)
    horizon_years: float = Field(default=5.0, ge=0.5, le=30.0)
    rate_volatility: float = Field(default=0.02, ge=0.001, le=0.5)
    rate_drift: float = Field(default=0.0, ge=-0.5, le=0.5)
    inflation_mean: float = Field(default=0.03, ge=-0.1, le=0.5)
    inflation_volatility: float = Field(default=0.01, ge=0.001, le=0.3)
    fx_volatility: float = Field(default=0.1, ge=0.0, le=2.0)
    correlation_matrix: Optional[dict] = None


class OptimizationCreate(BaseModel):
    portfolio_id: str
    name: str = Field(default="Untitled Optimization", max_length=255)
    optimization_type: str = "minimize_cost"
    objectives: dict = Field(default_factory=dict)
    constraints: dict = Field(default_factory=dict)
    solver_config: dict = Field(default_factory=dict)
    scenario_config: dict = Field(default_factory=dict)
    random_seed: int = 42


class OptimizationResponse(BaseModel):
    id: str
    portfolio_id: str
    org_id: str
    created_by: str
    name: str
    status: str
    optimization_type: str
    objectives: dict
    constraints: dict
    solver_config: dict
    scenario_config: dict
    random_seed: int
    model_version: str
    progress: float
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategyResponse(BaseModel):
    id: str
    name: str
    description: str
    allocations: dict
    metrics: dict
    stress_test_results: Optional[dict]
    rank: int
    created_at: datetime

    class Config:
        from_attributes = True


class BenchmarkResponse(BaseModel):
    id: str
    solver_name: str
    execution_time_seconds: float
    objective_value: float
    feasible: bool
    iterations: int
    metrics: dict
    created_at: datetime

    class Config:
        from_attributes = True


class OptimizationResultResponse(BaseModel):
    id: str
    strategy_id: Optional[str]
    metrics: dict
    allocation: dict
    created_at: datetime

    class Config:
        from_attributes = True


class AuditEventResponse(BaseModel):
    id: str
    actor_id: Optional[str]
    actor_email: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    org_id: Optional[str]
    metadata_json: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ReportRequest(BaseModel):
    job_id: str
    format: str = "json"


class ErrorResponse(BaseModel):
    detail: str
    code: str = "error"


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class InstrumentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    instrument_type: Optional[str] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    principal_outstanding: Optional[float] = Field(None, gt=0, le=1e15)
    coupon_rate: Optional[float] = Field(None, ge=-10, le=100)
    maturity_date: Optional[str] = None
    issue_date: Optional[str] = None
    is_callable: Optional[bool] = None
    call_date: Optional[str] = None
    call_price: Optional[float] = None
    spread_bps: Optional[float] = Field(None, ge=-1000, le=5000)

    @field_validator("maturity_date", "issue_date", "call_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not DATE_PATTERN.match(v):
            raise ValueError(f"Date must be in YYYY-MM-DD format, got: {v}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.upper().strip()
            valid = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "INR", "BRL"}
            if v not in valid:
                raise ValueError(f"Invalid currency. Must be one of: {', '.join(sorted(valid))}")
        return v


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError("Password must contain at least one special character")
        common = {'password', 'password1', 'qwerty', '12345678', 'letmein', 'admin', 'welcome', 'monkey', 'dragon', 'master'}
        if v.lower() in common:
            raise ValueError("This password is too common. Please choose a stronger one.")
        return v


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None


class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
