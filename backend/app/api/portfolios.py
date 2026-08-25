import json
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DebtInstrument, Portfolio, User, UserRole
from app.pagination import (
    FilterQuery,
    PaginationQuery,
    apply_filters,
    create_paginated_response,
    paginate_query,
)
from app.schemas import (
    DebtInstrumentCreate,
    DebtInstrumentResponse,
    InstrumentUpdate,
    PortfolioCreate,
    PortfolioResponse,
    PortfolioUpdate,
)
from app.security import get_current_user, log_audit_event, require_role
from app.security.portfolio_rbac import (
    PortfolioRole,
    require_portfolio_access,
)

router = APIRouter(prefix="/api/portfolios", tags=["portfolios"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
VALID_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "INR", "BRL"}


@router.get("")
def list_portfolios(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pagination: PaginationQuery = Depends(),
    filters: FilterQuery = Depends(),
):
    query = db.query(Portfolio).filter(Portfolio.org_id == user.org_id)

    # Apply filters
    query = apply_filters(query, filters, Portfolio)

    # Search in name and description
    items, total = paginate_query(
        query,
        limit=pagination.limit,
        offset=pagination.offset,
        cursor=pagination.cursor,
        search=pagination.search,
        search_fields=["name", "description"],
        sort_by=pagination.sort_by or "created_at",
        sort_order=pagination.sort_order,
        model=Portfolio,
    )

    return create_paginated_response(
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
        serializer=lambda p: PortfolioResponse.model_validate(p).model_dump(mode="json"),
    )


@router.post("", response_model=PortfolioResponse, status_code=201)
def create_portfolio(
    data: PortfolioCreate,
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db),
):

    portfolio = Portfolio(
        name=data.name.strip(),
        description=data.description,
        org_id=user.org_id,
        created_by=user.id,
    )
    db.add(portfolio)
    db.flush()

    for inst_data in data.instruments:
        instrument = DebtInstrument(
            portfolio_id=portfolio.id,
            name=inst_data.name.strip(),
            instrument_type=inst_data.instrument_type,
            currency=inst_data.currency.upper(),
            principal_outstanding=inst_data.principal_outstanding,
            coupon_rate=inst_data.coupon_rate,
            maturity_date=inst_data.maturity_date,
            issue_date=inst_data.issue_date,
            is_callable=inst_data.is_callable,
            call_date=inst_data.call_date,
            call_price=inst_data.call_price,
            spread_bps=inst_data.spread_bps,
        )
        db.add(instrument)

    db.commit()
    db.refresh(portfolio)

    log_audit_event(db, user, "portfolio.created", "portfolio", portfolio.id)
    return PortfolioResponse.model_validate(portfolio)


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(
    portfolio_id: str,
    user: User = Depends(require_portfolio_access(PortfolioRole.VIEWER)),
    db: Session = Depends(get_db),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return PortfolioResponse.model_validate(portfolio)


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(
    portfolio_id: str,
    user: User = Depends(require_portfolio_access(PortfolioRole.OWNER)),
    db: Session = Depends(get_db),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    log_audit_event(db, user, "portfolio.deleted", "portfolio", portfolio.id)
    db.delete(portfolio)
    db.commit()


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
def update_portfolio(
    portfolio_id: str,
    data: PortfolioUpdate,
    user: User = Depends(require_portfolio_access(PortfolioRole.EDITOR)),
    db: Session = Depends(get_db),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if data.name is not None:
        portfolio.name = data.name.strip()
    if data.description is not None:
        portfolio.description = data.description

    db.commit()
    db.refresh(portfolio)

    log_audit_event(db, user, "portfolio.updated", "portfolio", portfolio.id)
    return PortfolioResponse.model_validate(portfolio)


@router.delete("/{portfolio_id}/instruments/{instrument_id}", status_code=204)
def delete_instrument(
    portfolio_id: str,
    instrument_id: str,
    user: User = Depends(require_portfolio_access(PortfolioRole.EDITOR)),
    db: Session = Depends(get_db),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    instrument = db.query(DebtInstrument).filter(
        DebtInstrument.id == instrument_id, DebtInstrument.portfolio_id == portfolio_id
    ).first()
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    log_audit_event(db, user, "instrument.deleted", "instrument", instrument.id)
    db.delete(instrument)
    db.commit()


@router.put("/{portfolio_id}/instruments/{instrument_id}", response_model=DebtInstrumentResponse)
def update_instrument(
    portfolio_id: str,
    instrument_id: str,
    data: InstrumentUpdate,
    user: User = Depends(require_portfolio_access(PortfolioRole.EDITOR)),
    db: Session = Depends(get_db),
):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    instrument = db.query(DebtInstrument).filter(
        DebtInstrument.id == instrument_id, DebtInstrument.portfolio_id == portfolio_id
    ).first()
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        if field == "currency" and value is not None:
            value = value.upper().strip()
            if value not in VALID_CURRENCIES:
                raise HTTPException(status_code=422, detail=f"Invalid currency. Must be one of: {VALID_CURRENCIES}")
        setattr(instrument, field, value)

    db.commit()
    db.refresh(instrument)

    log_audit_event(db, user, "instrument.updated", "instrument", instrument.id)
    return DebtInstrumentResponse.model_validate(instrument)


@router.post("/{portfolio_id}/instruments", response_model=DebtInstrumentResponse, status_code=201)
def add_instrument(
    portfolio_id: str,
    data: DebtInstrumentCreate,
    user: User = Depends(require_portfolio_access(PortfolioRole.EDITOR)),
    db: Session = Depends(get_db),
):

    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if data.currency.upper() not in VALID_CURRENCIES:
        raise HTTPException(status_code=422, detail=f"Invalid currency. Must be one of: {VALID_CURRENCIES}")

    instrument = DebtInstrument(
        portfolio_id=portfolio_id,
        name=data.name.strip(),
        instrument_type=data.instrument_type,
        currency=data.currency.upper(),
        principal_outstanding=data.principal_outstanding,
        coupon_rate=data.coupon_rate,
        maturity_date=data.maturity_date,
        issue_date=data.issue_date,
        is_callable=data.is_callable,
        call_date=data.call_date,
        call_price=data.call_price,
        spread_bps=data.spread_bps,
    )
    db.add(instrument)
    db.commit()
    db.refresh(instrument)

    log_audit_event(db, user, "instrument.added", "instrument", instrument.id)
    return DebtInstrumentResponse.model_validate(instrument)


@router.get("/import/template")
def download_import_template():
    """Download an Excel template for portfolio import."""
    from fastapi.responses import StreamingResponse

    from app.excel_import import generate_import_template
    template = generate_import_template()
    return StreamingResponse(
        iter([template]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="portfolio-import-template.xlsx"'},
    )


@router.post("/import", response_model=PortfolioResponse, status_code=201)
async def import_excel_portfolio(
    file: UploadFile = File(...),
    name: str = Form(""),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db),
):
    """Import portfolio from Excel with auto-detected columns."""
    from app.excel_import import parse_excel_portfolio

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    result = parse_excel_portfolio(content, file.filename or "")

    if not result["instruments"]:
        raise HTTPException(status_code=422, detail="No instruments found in file")

    portfolio = Portfolio(
        name=(name or result["name"]).strip(),
        description=f"Imported from {file.filename}" if file.filename else "Imported portfolio",
        org_id=user.org_id,
        created_by=user.id,
    )
    db.add(portfolio)
    db.flush()

    added = 0
    for inst_data in result["instruments"]:
        try:
            instrument = DebtInstrument(
                portfolio_id=portfolio.id,
                name=str(inst_data.get("name", "Unknown")).strip()[:255],
                instrument_type=inst_data.get("instrument_type", "treasury_bond"),
                currency=str(inst_data.get("currency", "USD")).upper()[:3],
                principal_outstanding=float(inst_data.get("principal_outstanding", 0)),
                coupon_rate=float(inst_data.get("coupon_rate", 0)),
                maturity_date=str(inst_data.get("maturity_date", "2030-01-01")),
                issue_date=str(inst_data.get("issue_date", "2020-01-01")),
                is_callable=bool(inst_data.get("is_callable", False)),
                call_date=inst_data.get("call_date"),
                call_price=float(inst_data["call_price"]) if inst_data.get("call_price") else None,
                spread_bps=float(inst_data.get("spread_bps", 0)),
            )
            if instrument.principal_outstanding <= 0:
                continue
            db.add(instrument)
            added += 1
        except (ValueError, TypeError, KeyError):
            continue

    db.commit()
    db.refresh(portfolio)

    log_audit_event(db, user, "portfolio.imported", "portfolio", portfolio.id,
                    metadata={"filename": file.filename, "instrument_count": added, "stats": result["stats"]})

    return PortfolioResponse.model_validate(portfolio)


@router.post("/upload", response_model=PortfolioResponse, status_code=201)
async def upload_portfolio(
    file: UploadFile = File(...),
    name: str = Form("Uploaded Portfolio"),
    description: str = Form(""),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ANALYST)),
    db: Session = Depends(get_db),
):

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    try:
        if file.filename and file.filename.endswith(".json"):
            data = json.loads(content)
        elif file.filename and (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
            import pandas as pd
            df = pd.read_excel(BytesIO(content))
            data = df.to_dict(orient="records")
        else:
            raise HTTPException(status_code=422, detail="Unsupported file format. Use .json or .xlsx")
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON format")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {str(e)[:200]}")

    instruments = data if isinstance(data, list) else data.get("instruments", [])
    if not instruments:
        raise HTTPException(status_code=422, detail="No instruments found in uploaded file")

    portfolio = Portfolio(
        name=name.strip(),
        description=description,
        org_id=user.org_id,
        created_by=user.id,
    )
    db.add(portfolio)
    db.flush()

    for inst_data in instruments:
        try:
            instrument = DebtInstrument(
                portfolio_id=portfolio.id,
                name=str(inst_data.get("name", "Unknown")).strip()[:255],
                instrument_type=inst_data.get("instrument_type", "treasury_bond"),
                currency=str(inst_data.get("currency", "USD")).upper()[:3],
                principal_outstanding=float(inst_data.get("principal_outstanding", 0)),
                coupon_rate=float(inst_data.get("coupon_rate", 0)),
                maturity_date=str(inst_data.get("maturity_date", "2030-01-01")),
                issue_date=str(inst_data.get("issue_date", "2020-01-01")),
                is_callable=bool(inst_data.get("is_callable", False)),
                call_date=inst_data.get("call_date"),
                call_price=float(inst_data["call_price"]) if inst_data.get("call_price") else None,
                spread_bps=float(inst_data.get("spread_bps", 0)),
            )
            if instrument.principal_outstanding <= 0:
                continue
            if instrument.principal_outstanding > 1e15 or abs(instrument.coupon_rate) > 100:
                continue
            db.add(instrument)
        except (ValueError, TypeError, KeyError):
            continue

    db.commit()
    db.refresh(portfolio)

    log_audit_event(db, user, "portfolio.uploaded", "portfolio", portfolio.id,
                    metadata={"filename": file.filename, "instrument_count": len(portfolio.instruments)})
    return PortfolioResponse.model_validate(portfolio)
