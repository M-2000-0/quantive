"""SOC 2 Type II Security System for Quantive.

Maps to AICPA Trust Service Criteria:
- CC6: Logical and Physical Access Controls
- CC7: System Operations
- CC8: Change Management
- CC9: Risk Mitigation

Trust Service Criteria:
1. Security (Common Criteria) — All controls below
2. Availability — Uptime, DR, backup verification
3. Processing Integrity — Accuracy, completeness of processing
4. Confidentiality — Encryption, access controls
5. Privacy — Data handling, retention, consent
"""
from app.security.soc2.audit_log import SOC2AuditLogger
from app.security.soc2.access_control import AccessControlManager
from app.security.soc2.change_management import ChangeManagementController
from app.security.soc2.incident_response import IncidentResponseManager
from app.security.soc2.vendor_risk import VendorRiskManager
from app.security.soc2.evidence_collector import ComplianceEvidenceCollector
from app.security.soc2.evidence_autocapture import EvidenceAutoCapture
from app.security.soc2.pentest_scanner import PentestReadinessScanner
from app.security.soc2.dr_runbook import DisasterRecoveryRunbookGenerator
from app.security.soc2.data_protection import DataProtectionManager
from app.security.soc2.cicd_security import CICDSecurityPipeline
from app.security.soc2.alerting import AlertingManager
from app.security.soc2.temporal_evidence import TemporalEvidenceManager
from app.security.soc2.employee_security import EmployeeSecurityManager

__all__ = [
    "SOC2AuditLogger",
    "AccessControlManager",
    "ChangeManagementController",
    "IncidentResponseManager",
    "VendorRiskManager",
    "ComplianceEvidenceCollector",
    "EvidenceAutoCapture",
    "PentestReadinessScanner",
    "DisasterRecoveryRunbookGenerator",
    "DataProtectionManager",
    "CICDSecurityPipeline",
    "AlertingManager",
    "TemporalEvidenceManager",
    "EmployeeSecurityManager",
]
