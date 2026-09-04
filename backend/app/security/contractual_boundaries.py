"""Contractual Boundary Enforcement.

Directive 6: Contractual Boundaries & Liability Shielding
- SLA enforcement with liability caps
- Scope definition and disclaimers
- Maintenance window enforcement
- No uptime or zero-risk promises
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("quantive.security.sla")


class SLAContract:
    def __init__(self, client_id: str, contract_value: float,
                 liability_cap_months: int = 12, max_consequential: bool = False):
        self.client_id = client_id
        self.contract_value = contract_value
        self.liability_cap_months = liability_cap_months
        self.max_consequential = max_consequential
        self.liability_cap = contract_value  # 12 months of fees
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id, "contract_value": self.contract_value,
            "liability_cap_months": self.liability_cap_months,
            "liability_cap": self.liability_cap,
            "consequential_damages_excluded": not self.max_consequential,
            "created_at": self.created_at,
        }


class SLAEnforcer:
    def __init__(self):
        self._contracts = {}

    def register_contract(self, client_id: str, contract_value: float,
                          liability_cap_months: int = 12, max_consequential: bool = False) -> SLAContract:
        contract = SLAContract(client_id, contract_value, liability_cap_months, max_consequential)
        self._contracts[client_id] = contract
        logger.info("SLA registered for %s: cap=%s over %d months",
                     client_id, contract.liability_cap, liability_cap_months)
        return contract

    def check_liability_cap(self, client_id: str, claim_amount: float) -> dict:
        contract = self._contracts.get(client_id)
        if not contract:
            return {"allowed": False, "reason": "No contract found for client"}
        if claim_amount > contract.liability_cap:
            return {
                "allowed": False,
                "reason": f"Claim {claim_amount} exceeds liability cap {contract.liability_cap}",
                "capped_amount": contract.liability_cap,
                "excess": claim_amount - contract.liability_cap,
            }
        return {"allowed": True, "amount": claim_amount, "cap": contract.liability_cap}

    def get_consequential_damage_exclusion(self, client_id: str) -> dict:
        contract = self._contracts.get(client_id)
        if not contract:
            return {"excluded": True, "reason": "No contract found"}
        return {
            "excluded": not contract.max_consequential,
            "consequential_damages_excluded": not contract.max_consequential,
            "client_id": client_id,
        }


class ScopeEnforcer:
    def __init__(self):
        self._scopes = {}

    def define_scope(self, client_id: str, permitted_data: list, prohibited_data: list,
                     environment: str = "pilot", max_volume: Optional[str] = None):
        self._scopes[client_id] = {
            "permitted_data": permitted_data,
            "prohibited_data": prohibited_data,
            "environment": environment,
            "max_volume": max_volume,
            "defined_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("Scope defined for %s: env=%s", client_id, environment)

    def validate_data_submission(self, client_id: str, data_type: str) -> dict:
        scope = self._scopes.get(client_id)
        if not scope:
            return {"allowed": False, "reason": "No scope defined for client"}
        if data_type in scope["prohibited_data"]:
            return {
                "allowed": False,
                "reason": f"Data type '{data_type}' is PROHIBITED for this client.",
                "prohibited": scope["prohibited_data"],
            }
        if data_type not in scope["permitted_data"] and scope["permitted_data"] != ["*"]:
            return {
                "allowed": False,
                "reason": f"Data type '{data_type}' not in permitted list.",
                "permitted": scope["permitted_data"],
            }
        return {"allowed": True, "data_type": data_type, "environment": scope["environment"]}

    def get_disclaimer(self, client_id: str) -> str:
        return (
            "DISCLAIMER: The System is experimental and may contain defects, errors, " +
            "vulnerabilities, or downtime. Customer shall use the System only for the " +
            "approved use case and only with the data and environment identified in the " +
            "Statement of Work. No production use is authorized without a separate signed " +
            "statement of work. Customer shall maintain independent, current, and verified " +
            "backups. Final decisions remain the responsibility of authorized customer personnel."
        )


class MaintenanceWindowEnforcer:
    def __init__(self):
        self._windows = []

    def register_window(self, name: str, schedule: str, duration_hours: float,
                        description: str):
        self._windows.append({
            "name": name, "schedule": schedule,
            "duration_hours": duration_hours, "description": description,
        })
        logger.info("Maintenance window registered: %s (%s)", name, schedule)

    def is_in_maintenance(self) -> dict:
        now = datetime.now(timezone.utc)
        # Simple Sunday 02:00-06:00 UTC check
        if now.weekday() == 6 and 2 <= now.hour < 6:
            return {"in_maintenance": True, "reason": "Scheduled maintenance window"}
        return {"in_maintenance": False}

    def get_windows(self) -> list:
        return self._windows
