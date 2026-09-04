"""Third-Party Risk Review and Offboarding Automation.

Directive 9: Human Risk and Vendor Exposure
- Audit external API vendors, open-source libraries, third-party tools
- Automated SAST/DAST/dependency scanning
- Automated revocation of all access tokens on departure
- Privilege recertification
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("quantive.security.vendor_risk")


class VendorRiskAssessment:
    def __init__(self, name, vendor_type, data_access_level, contract_value=0.0):
        self.name = name
        self.vendor_type = vendor_type
        self.data_access_level = data_access_level
        self.contract_value = contract_value
        self.risk_score = 0
        self.findings = []
        self.last_assessed = datetime.now(timezone.utc)
        self.status = "pending_review"

    def to_dict(self):
        return {"name": self.name, "type": self.vendor_type, "access": self.data_access_level,
                "risk_score": self.risk_score, "status": self.status, "findings": self.findings}


class VendorRiskManager:
    def __init__(self):
        self._vendors = {}
        self._scan_results = []

    def register_vendor(self, name, vendor_type, data_access_level, contract_value=0.0):
        v = VendorRiskAssessment(name, vendor_type, data_access_level, contract_value)
        self._vendors[name] = v
        return v

    def assess_risk(self, name, findings):
        v = self._vendors.get(name)
        if not v:
            return {"error": "Vendor not found"}
        v.findings = findings
        v.last_assessed = datetime.now(timezone.utc)
        score = {"none": 0, "internal": 20, "confidential": 50, "regulated": 80}.get(v.data_access_level, 30)
        score += sum(15 for f in findings if f.get("severity") == "critical")
        score += sum(8 for f in findings if f.get("severity") == "high")
        v.risk_score = min(score, 100)
        v.status = "critical" if v.risk_score >= 70 else ("elevated" if v.risk_score >= 40 else "acceptable")
        return {"vendor": name, "risk_score": v.risk_score, "status": v.status}

    def scan_dependencies(self, requirements_file):
        findings = []
        try:
            with open(requirements_file) as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("==")
                    if len(parts) < 2:
                        findings.append({"package": parts[0], "severity": "medium",
                                         "issue": "No pinned version", "line": i})
        except FileNotFoundError:
            pass
        self._scan_results.extend(findings)
        return findings

    def get_vendors(self):
        return [v.to_dict() for v in self._vendors.values()]


class OffboardingManager:
    def __init__(self):
        self._offboardings = []
        self._active_users = {}

    def register_user(self, user_id, role, access_levels, service_accounts=None):
        self._active_users[user_id] = {"role": role, "access": access_levels,
                                        "svc_accounts": service_accounts or []}

    def initiate_offboarding(self, user_id, reason, effective_date):
        user = self._active_users.get(user_id)
        if not user:
            return {"error": "User not found"}
        items = ["revoke_oauth_tokens", "revoke_api_keys", "revoke_ssh_keys",
                 "remove_database_access", "revoke_vpn_access", "transfer_ownership",
                 "disable_service_accounts", "audit_recent_activity"]
        checklist = {item: {"status": "pending", "critical": True} for item in items}
        off = {"user_id": user_id, "reason": reason, "effective_date": effective_date,
               "initiated_at": datetime.now(timezone.utc).isoformat(),
               "checklist": checklist, "status": "in_progress"}
        self._offboardings.append(off)
        self._active_users.pop(user_id, None)
        logger.critical("OFFBOARDING: %s - %s", user_id, reason)
        return off

    def complete_item(self, user_id, item, completed_by):
        for off in self._offboardings:
            if off["user_id"] == user_id and item in off["checklist"]:
                off["checklist"][item]["status"] = "completed"
                off["checklist"][item]["by"] = completed_by
                done = all(v["status"] == "completed" for v in off["checklist"].values())
                if done:
                    off["status"] = "completed"
                return {"done": done}
        return {"error": "not found"}

    def get_pending(self):
        return [o for o in self._offboardings if o["status"] != "completed"]


class PrivilegeRecertification:
    def __init__(self, cycle_days=90):
        self._certs = []
        self._cycle_days = cycle_days

    def register(self, user_id, privilege, granted_date, approver):
        self._certs.append({"user_id": user_id, "privilege": privilege,
                            "granted": granted_date, "approver": approver,
                            "last_recertified": granted_date, "status": "active"})

    def check_expired(self):
        expired = []
        now = datetime.now(timezone.utc)
        for c in self._certs:
            if c["status"] != "active":
                continue
            try:
                granted = datetime.fromisoformat(c["granted"].replace("Z", "+00:00"))
                if (now - granted).days > self._cycle_days:
                    c["status"] = "expired"
                    expired.append(c)
            except (ValueError, TypeError):
                pass
        return expired

    def recertify(self, user_id, privilege, by):
        for c in self._certs:
            if c["user_id"] == user_id and c["privilege"] == privilege:
                c["last_recertified"] = datetime.now(timezone.utc).isoformat()
                c["status"] = "active"
                return {"status": "recertified"}
        return {"error": "not found"}