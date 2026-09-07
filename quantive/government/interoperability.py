"""FpML/XBRL Interoperability Support.

Enables data exchange with central banks, IMF, and World Bank
using standard financial data formats.

This addresses the "No Interoperability Standards" issue from
the Government Procurement Stress Test.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from xml.etree import ElementTree as ET


class DataFormat(str, Enum):
    """Supported data formats."""
    FPML = "fpml"
    XBRL = "xbrl"
    SWIFT = "swift"
    ISO_20022 = "iso_20022"
    CSV = "csv"
    JSON = "json"


class InstrumentType(str, Enum):
    """Financial instrument types."""
    BOND = "bond"
    BILL = "bill"
    NOTE = "note"
    TIPS = "tips"
    FRN = "frn"
    SWAP = "swap"
    CDS = "cds"


@dataclass
class FpMLTrade:
    """FpML trade representation."""
    trade_id: str
    trade_date: datetime
    instrument_type: InstrumentType
    notional_amount: float
    currency: str
    coupon_rate: float
    maturity_date: datetime
    issuer: str
    counterparty: str
    settlement_date: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class XBRLFact:
    """XBRL fact representation."""
    concept: str
    value: Any
    unit: str | None = None
    dimensions: dict[str, str] = field(default_factory=dict)
    decimals: int | None = None


class FpMLConverter:
    """Converts between internal models and FpML format."""

    def __init__(self):
        self._fpml_namespace = "http://www.fpml.org/FpML-5/confirmation"

    def instrument_to_fpml(self, instrument: dict) -> str:
        """Convert an internal instrument to FpML XML."""
        root = ET.Element("trade")
        root.set("xmlns", self._fpml_namespace)

        trade_header = ET.SubElement(root, "tradeHeader")
        trade_id_elem = ET.SubElement(trade_header, "tradeId")
        trade_id_elem.text = instrument.get("id", str(uuid.uuid4()))

        product = ET.SubElement(root, "product")
        ET.SubElement(product, "productId").text = instrument.get("instrument_type", "bond")

        bond = ET.SubElement(product, "bond")
        ET.SubElement(bond, "issuerName").text = instrument.get("issuer", "Government")
        ET.SubElement(bond, "couponRate").text = str(instrument.get("coupon_rate", 0))
        ET.SubElement(bond, "maturityDate").text = instrument.get("maturity_date", "")

        notional = ET.SubElement(root, "notionalAmount")
        notional.set("currency", instrument.get("currency", "USD"))
        notional.text = str(instrument.get("principal_outstanding", 0))

        return ET.tostring(root, encoding="unicode")

    def fpml_to_instrument(self, fpml_xml: str) -> dict:
        """Convert FpML XML to internal instrument format."""
        root = ET.fromstring(fpml_xml)

        # Extract data from FpML
        bond = root.find(".//{http://www.fpml.org/FpML-5/confirmation}bond")
        notional = root.find(".//{http://www.fpml.org/FpML-5/confirmation}notionalAmount")

        return {
            "id": root.findtext(".//{http://www.fpml.org/FpML-5/confirmation}tradeId", ""),
            "instrument_type": root.findtext(".//{http://www.fpml.org/FpML-5/confirmation}productId", "bond"),
            "issuer": bond.findtext("{http://www.fpml.org/FpML-5/confirmation}issuerName", "") if bond is not None else "",
            "coupon_rate": float(bond.findtext("{http://www.fpml.org/FpML-5/confirmation}couponRate", "0")) if bond is not None else 0,
            "maturity_date": bond.findtext("{http://www.fpml.org/FpML-5/confirmation}maturityDate", "") if bond is not None else "",
            "principal_outstanding": float(notional.text) if notional is not None else 0,
            "currency": notional.get("currency", "USD") if notional is not None else "USD",
        }

    def portfolio_to_fpml(self, portfolio: dict) -> str:
        """Convert a portfolio to FpML trades list."""
        trades = []
        for instrument in portfolio.get("instruments", []):
            trade_xml = self.instrument_to_fpml(instrument)
            trades.append(trade_xml)
        return "\n".join(trades)


class XBRLConverter:
    """Converts between internal models and XBRL format."""

    def __init__(self):
        self._xbrl_namespace = "http://www.xbrl.org/2003/instance"

    def debt_to_xbrl(self, debt_data: dict) -> str:
        """Convert debt data to XBRL instance document."""
        root = ET.Element("xbrl")
        root.set("xmlns", self._xbrl_namespace)
        root.set("xmlns:debt", "http://quantive.com/taxonomy/debt")

        # Add context
        context = ET.SubElement(root, "context")
        context.set("id", "current_period")
        entity = ET.SubElement(context, "entity")
        identifier = ET.SubElement(entity, "identifier")
        identifier.set("scheme", "http://quantive.com")
        identifier.text = debt_data.get("entity_id", "")

        period = ET.SubElement(context, "period")
        instant = ET.SubElement(period, "instant")
        instant.text = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Add facts
        facts = [
            ("debt:TotalDebtOutstanding", debt_data.get("total_debt", 0), "USD"),
            ("debt:AnnualIssuance", debt_data.get("annual_issuance", 0), "USD"),
            ("debt:DebtToGDP", debt_data.get("debt_to_gdp", 0), "pure"),
            ("debt:WeightedAverageMaturity", debt_data.get("weighted_avg_maturity", 0), "years"),
            ("debt:WeightedAverageCoupon", debt_data.get("weighted_avg_coupon", 0), "pure"),
            ("debt:FXExposure", debt_data.get("fx_exposure", 0), "pure"),
            ("debt:FloatingRateExposure", debt_data.get("floating_rate_exposure", 0), "pure"),
        ]

        for concept, value, unit in facts:
            fact = ET.SubElement(root, "debt:fact")
            fact.set("contextRef", "current_period")
            fact.set("unitRef", unit)
            fact.text = str(value)

        return ET.tostring(root, encoding="unicode")

    def xbrl_to_data(self, xbrl_xml: str) -> dict:
        """Convert XBRL instance to internal data format."""
        root = ET.fromstring(xbrl_xml)

        data = {}
        for fact in root.findall(".//{http://www.xbrl.org/2003/instance}fact"):
            concept = fact.get("concept", "")
            value = fact.text
            if "TotalDebtOutstanding" in concept:
                data["total_debt"] = float(value) if value else 0
            elif "AnnualIssuance" in concept:
                data["annual_issuance"] = float(value) if value else 0
            elif "DebtToGDP" in concept:
                data["debt_to_gdp"] = float(value) if value else 0

        return data


class SWIFTConverter:
    """Converts between internal models and SWIFT message formats."""

    def mt3_to_instruments(self, mt3_message: str) -> list[dict]:
        """Parse SWIFT MT3 message to extract instruments."""
        instruments = []

        # Simplified MT3 parsing (in production, use proper MT3 library)
        lines = mt3_message.split("\n")
        for line in lines:
            if line.startswith(":35A:"):  # Instrument identification
                parts = line[5:].split("/")
                if len(parts) >= 2:
                    instruments.append({
                        "instrument_type": "bond",
                        "isin": parts[0] if parts else "",
                        "currency": parts[1] if len(parts) > 1 else "",
                    })

        return instruments

    def instrument_to_mt3(self, instrument: dict) -> str:
        """Convert instrument to SWIFT MT3 message format."""
        # Simplified MT3 generation
        mt3 = f":20:{instrument.get('trade_id', 'REF001')}\n"
        mt3 += f":35A:{instrument.get('isin', '')}/{instrument.get('currency', 'USD')}\n"
        mt3 += f":32B:{instrument.get('currency', 'USD')}{instrument.get('principal_outstanding', 0):,.2f}\n"
        mt3 += f":98A:{instrument.get('settlement_date', '')}\n"
        return mt3


class InteroperabilityEngine:
    """Manages data format conversions and integrations."""

    def __init__(self):
        self._fpml_converter = FpMLConverter()
        self._xbrl_converter = XBRLConverter()
        self._swift_converter = SWIFTConverter()
        self._supported_formats = [f.value for f in DataFormat]

    def convert(
        self,
        data: dict,
        source_format: DataFormat,
        target_format: DataFormat,
    ) -> dict | str:
        """Convert data between formats."""
        # Convert to internal format first
        internal_data = data

        # Convert to target format
        if target_format == DataFormat.FPML:
            return self._fpml_converter.instrument_to_fpml(internal_data)
        elif target_format == DataFormat.XBRL:
            return self._xbrl_converter.debt_to_xbrl(internal_data)
        elif target_format == DataFormat.SWIFT:
            return self._swift_converter.instrument_to_mt3(internal_data)
        elif target_format == DataFormat.JSON:
            return json.dumps(internal_data, indent=2)
        elif target_format == DataFormat.CSV:
            return self._to_csv(internal_data)
        else:
            raise ValueError(f"Unsupported target format: {target_format}")

    def _to_csv(self, data: dict) -> str:
        """Convert dictionary to CSV format."""
        if not data:
            return ""

        headers = list(data.keys())
        values = [str(data[h]) for h in headers]
        return ",".join(headers) + "\n" + ",".join(values)

    def get_supported_formats(self) -> list[str]:
        """Get list of supported data formats."""
        return self._supported_formats

    def validate_format(self, data: str, format: DataFormat) -> bool:
        """Validate that data matches the specified format."""
        if format == DataFormat.JSON:
            try:
                json.loads(data)
                return True
            except json.JSONDecodeError:
                return False
        elif format == DataFormat.FPML:
            try:
                ET.fromstring(data)
                return True
            except ET.ParseError:
                return False
        elif format == DataFormat.XBRL:
            try:
                ET.fromstring(data)
                return True
            except ET.ParseError:
                return False
        return True

    def get_integration_endpoints(self) -> list[dict]:
        """Get available integration endpoints."""
        return [
            {
                "name": "IMF Data Mapper",
                "description": "Map debt data to IMF DSA framework",
                "formats": ["xbrl", "csv"],
                "endpoint": "/api/interoperability/imf",
            },
            {
                "name": "World Bank Debt Platform",
                "description": "Export to World Bank International Debt Statistics",
                "formats": ["xbrl", "csv"],
                "endpoint": "/api/interoperability/worldbank",
            },
            {
                "name": "Bloomberg Terminal Import",
                "description": "Import from Bloomberg Excel exports",
                "formats": ["csv"],
                "endpoint": "/api/interoperability/bloomberg",
            },
            {
                "name": "Reuters Eikon",
                "description": "Import from Reuters data feeds",
                "formats": ["csv", "json"],
                "endpoint": "/api/interoperability/reuters",
            },
        ]


# Global instance
_interoperability_engine: InteroperabilityEngine | None = None


def get_interoperability_engine() -> InteroperabilityEngine:
    """Get the global interoperability engine."""
    global _interoperability_engine
    if _interoperability_engine is None:
        _interoperability_engine = InteroperabilityEngine()
    return _interoperability_engine
