"""Interoperability API endpoints.

Exposes FpML, XBRL, and SWIFT data format conversions for government integration.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/interoperability", tags=["interoperability"])


# ── Request Models ─────────────────────────────────────────────────

class ConvertRequest(BaseModel):
    data: dict = Field(..., description="Data to convert")
    source_format: str = Field(..., description="Source format")
    target_format: str = Field(..., description="Target format")


class ValidateRequest(BaseModel):
    data: str = Field(..., description="Data to validate")
    format: str = Field(..., description="Expected format")


# ── API Endpoints ──────────────────────────────────────────────────

@router.get("/formats")
def get_supported_formats():
    """Get list of supported data formats."""
    from quantive.government.interoperability import get_interoperability_engine

    engine = get_interoperability_engine()
    formats = engine.get_supported_formats()

    return {"formats": formats}


@router.post("/convert")
def convert_data(
    request: ConvertRequest,
    user: User = Depends(get_current_user),
):
    """Convert data between formats."""
    from quantive.government.interoperability import DataFormat, get_interoperability_engine

    engine = get_interoperability_engine()

    format_map = {f.value: f for f in DataFormat}
    source_format = format_map.get(request.source_format)
    target_format = format_map.get(request.target_format)

    if not source_format:
        raise HTTPException(400, f"Invalid source format: {request.source_format}")
    if not target_format:
        raise HTTPException(400, f"Invalid target format: {request.target_format}")

    try:
        result = engine.convert(
            data=request.data,
            source_format=source_format,
            target_format=target_format,
        )
    except Exception as e:
        raise HTTPException(400, str(e))

    return {
        "result": result,
        "source_format": request.source_format,
        "target_format": request.target_format,
    }


@router.post("/validate")
def validate_data(
    request: ValidateRequest,
    user: User = Depends(get_current_user),
):
    """Validate that data matches the specified format."""
    from quantive.government.interoperability import DataFormat, get_interoperability_engine

    engine = get_interoperability_engine()

    format_map = {f.value: f for f in DataFormat}
    data_format = format_map.get(request.format)

    if not data_format:
        raise HTTPException(400, f"Invalid format: {request.format}")

    is_valid = engine.validate_format(data=request.data, format=data_format)

    return {
        "is_valid": is_valid,
        "format": request.format,
    }


@router.get("/integrations")
def get_integrations():
    """Get available integration endpoints."""
    from quantive.government.interoperability import get_interoperability_engine

    engine = get_interoperability_engine()
    integrations = engine.get_integration_endpoints()

    return {"integrations": integrations}


@router.post("/fpml/parse")
def parse_fpml(
    fpml_xml: str,
    user: User = Depends(get_current_user),
):
    """Parse FpML XML to internal instrument format."""
    from quantive.government.interoperability import get_interoperability_engine

    engine = get_interoperability_engine()
    fpml_converter = engine._fpml_converter

    try:
        instrument = fpml_converter.fpml_to_instrument(fpml_xml)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse FpML: {str(e)}")

    return {"instrument": instrument}


@router.post("/fpml/generate")
def generate_fpml(
    instrument: dict,
    user: User = Depends(get_current_user),
):
    """Generate FpML XML from instrument data."""
    from quantive.government.interoperability import get_interoperability_engine

    engine = get_interoperability_engine()
    fpml_converter = engine._fpml_converter

    try:
        fpml_xml = fpml_converter.instrument_to_fpml(instrument)
    except Exception as e:
        raise HTTPException(400, f"Failed to generate FpML: {str(e)}")

    return {"fpml": fpml_xml}


@router.post("/xbrl/parse")
def parse_xbrl(
    xbrl_xml: str,
    user: User = Depends(get_current_user),
):
    """Parse XBRL instance to internal data format."""
    from quantive.government.interoperability import get_interoperability_engine

    engine = get_interoperability_engine()
    xbrl_converter = engine._xbrl_converter

    try:
        data = xbrl_converter.xbrl_to_data(xbrl_xml)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse XBRL: {str(e)}")

    return {"data": data}


@router.post("/xbrl/generate")
def generate_xbrl(
    debt_data: dict,
    user: User = Depends(get_current_user),
):
    """Generate XBRL instance from debt data."""
    from quantive.government.interoperability import get_interoperability_engine

    engine = get_interoperability_engine()
    xbrl_converter = engine._xbrl_converter

    try:
        xbrl_xml = xbrl_converter.debt_to_xbrl(debt_data)
    except Exception as e:
        raise HTTPException(400, f"Failed to generate XBRL: {str(e)}")

    return {"xbrl": xbrl_xml}


@router.post("/swift/parse")
def parse_swift(
    mt3_message: str,
    user: User = Depends(get_current_user),
):
    """Parse SWIFT MT3 message to instruments."""
    from quantive.government.interoperability import get_interoperability_engine

    engine = get_interoperability_engine()
    swift_converter = engine._swift_converter

    try:
        instruments = swift_converter.mt3_to_instruments(mt3_message)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse SWIFT message: {str(e)}")

    return {"instruments": instruments}


@router.post("/swift/generate")
def generate_swift(
    instrument: dict,
    user: User = Depends(get_current_user),
):
    """Generate SWIFT MT3 message from instrument data."""
    from quantive.government.interoperability import get_interoperability_engine

    engine = get_interoperability_engine()
    swift_converter = engine._swift_converter

    try:
        mt3_message = swift_converter.instrument_to_mt3(instrument)
    except Exception as e:
        raise HTTPException(400, f"Failed to generate SWIFT message: {str(e)}")

    return {"mt3": mt3_message}
