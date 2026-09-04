"""Data Classification and Permitted-Use Policy."""

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.data_classification")


CLASSIFICATIONS = {
    "public": {"level": 0, "description": "Freely available information",
        "allowed_in_system": True, "encryption_required": False, "backup_required": False},
    "internal": {"level": 1, "description": "Internal business information",
        "allowed_in_system": True, "encryption_required": True, "backup_required": True},
    "confidential": {"level": 2, "description": "Sensitive business information",
        "allowed_in_system": True, "encryption_required": True, "backup_required": True},
    "restricted": {"level": 3, "description": "Highly sensitive - sovereign debt, financial data",
        "allowed_in_system": False, "encryption_required": True, "backup_required": True,
        "requires_written_approval": True},
    "regulated": {"level": 4, "description": "PII, PHI, government classified, trade secrets",
        "allowed_in_system": False, "encryption_required": True, "backup_required": True,
        "requires_written_approval": True, "requires_legal_review": True},
}

PROHIBITED_DATA_TYPES = [
    "personal_identifiable_information",
    "protected_health_information",
    "financial_account_numbers",
    "classified_government_data",
    "trade_secrets",
    "authentication_credentials",
    "encryption_keys",
]


class DataClassifier:

    def __init__(self, db: Session):
        self.db = db

    def classify(self, data_type: str, customer_id: str) -> dict:
        classification = CLASSIFICATIONS.get(data_type, CLASSIFICATIONS["confidential"])
        return {"data_type": data_type, "classification": classification,
            "customer_id": customer_id, "classified_at": datetime.now(timezone.utc).isoformat()}

    def check_permitted(self, data_type: str) -> dict:
        classification = CLASSIFICATIONS.get(data_type, CLASSIFICATIONS["confidential"])
        if not classification["allowed_in_system"]:
            return {"permitted": False, "reason": f"{data_type} requires written approval",
                "classification": data_type, "action_required": "obtain written approval from security_lead and legal"}
        return {"permitted": True, "classification": data_type}

    def check_prohibited(self, data_description: str) -> dict:
        desc_lower = data_description.lower()
        for prohibited in PROHIBITED_DATA_TYPES:
            if prohibited.replace("_", " ") in desc_lower or prohibited.replace("_", "-") in desc_lower:
                return {"prohibited": True, "type": prohibited,
                    "message": f"{prohibited} is prohibited in Quantive. Cannot process."}
        return {"prohibited": False}