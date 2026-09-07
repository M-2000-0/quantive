"""Source Code Escrow Agreement Template.

Provides a standard escrow agreement template for government contracts.
Addresses the "No Vendor Viability Proof" issue from the
Government Procurement Stress Test.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EscrowStatus(str, Enum):
    """Status of escrow agreement."""
    DRAFT = "draft"
    PENDING_SIGNATURE = "pending_signature"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    RELEASED = "released"
    TERMINATED = "terminated"


class ReleaseCondition(str, Enum):
    """Conditions for escrow release."""
    BANKRUPTCY = "bankruptcy"
    INSOLVENCY = "insolvency"
    ABANDONMENT = "abandonment"
    MATERIAL_BREACH = "material_breach"
    FAILURE_TO_MAINTAIN = "failure_to_maintain"
    GOVERNMENT_REQUEST = "government_request"


@dataclass
class EscrowParty:
    """Party to the escrow agreement."""
    name: str
    role: str  # depositor, beneficiary, escrow_agent
    address: str
    contact_name: str
    contact_email: str
    contact_phone: str = ""


@dataclass
class EscrowAgreement:
    """Complete escrow agreement."""
    agreement_id: str
    status: EscrowStatus
    depositor: EscrowParty  # Quantive
    beneficiary: EscrowParty  # Government
    escrow_agent: EscrowParty  # Independent trustee

    effective_date: datetime
    termination_date: datetime | None

    # Source code details
    software_description: str
    version: str
    repository_url: str
    build_instructions: str
    dependency_list: str

    # Release conditions
    release_conditions: list[ReleaseCondition]
    release_procedure: str
    verification_period_days: int = 30

    # Financial terms
    escrow_fee_annual: float = 0.0
    release_fee: float = 0.0

    # Maintenance obligations
    update_frequency: str = "quarterly"
    last_update_date: datetime | None = None
    update_verification: bool = True

    # Additional terms
    confidentiality_clause: str = ""
    license_terms: str = ""
    support_obligations: str = ""

    metadata: dict[str, Any] = field(default_factory=dict)


class EscrowManager:
    """Manages source code escrow agreements."""

    def __init__(self):
        self._agreements: dict[str, EscrowAgreement] = {}

    def create_agreement(
        self,
        depositor: EscrowParty,
        beneficiary: EscrowParty,
        escrow_agent: EscrowParty,
        software_description: str,
        version: str,
        repository_url: str,
    ) -> EscrowAgreement:
        """Create a new escrow agreement."""
        agreement_id = f"escrow-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{beneficiary.name[:3].upper()}"

        agreement = EscrowAgreement(
            agreement_id=agreement_id,
            status=EscrowStatus.DRAFT,
            depositor=depositor,
            beneficiary=beneficiary,
            escrow_agent=escrow_agent,
            effective_date=datetime.now(timezone.utc),
            termination_date=None,
            software_description=software_description,
            version=version,
            repository_url=repository_url,
            build_instructions="See README.md in repository root",
            dependency_list="requirements.txt, package.json",
            release_conditions=[
                ReleaseCondition.BANKRUPTCY,
                ReleaseCondition.INSOLVENCY,
                ReleaseCondition.ABANDONMENT,
                ReleaseCondition.MATERIAL_BREACH,
                ReleaseCondition.FAILURE_TO_MAINTAIN,
            ],
            release_procedure=(
                "1. Beneficiary notifies Escrow Agent of release event\n"
                "2. Escrow Agent verifies trigger condition\n"
                "3. Depositor has 30 days to dispute\n"
                "4. If undisputed, Escrow Agent releases source code\n"
                "5. Beneficiary receives full source code and build instructions"
            ),
            verification_period_days=30,
            escrow_fee_annual=15000.0,  # $15K/year
            release_fee=5000.0,  # $5K per release
            confidentiality_clause=(
                "Beneficiary agrees to maintain confidentiality of source code "
                "and use it solely for maintaining and operating the software."
            ),
            license_terms=(
                "Upon release, Beneficiary receives perpetual, non-exclusive license "
                "to use, modify, and distribute the software for internal purposes."
            ),
            support_obligations=(
                "Depositor shall provide quarterly updates to Escrow Agent "
                "including source code, documentation, and build instructions."
            ),
        )

        self._agreements[agreement_id] = agreement
        return agreement

    def get_agreement(self, agreement_id: str) -> EscrowAgreement | None:
        """Get an escrow agreement by ID."""
        return self._agreements.get(agreement_id)

    def list_agreements(
        self,
        status: EscrowStatus | None = None,
    ) -> list[EscrowAgreement]:
        """List all escrow agreements."""
        agreements = list(self._agreements.values())
        if status:
            agreements = [a for a in agreements if a.status == status]
        return agreements

    def trigger_release(
        self,
        agreement_id: str,
        condition: ReleaseCondition,
        evidence: str,
    ) -> dict:
        """Trigger a release of escrowed source code."""
        agreement = self._agreements.get(agreement_id)
        if not agreement:
            raise ValueError(f"Agreement {agreement_id} not found")

        if condition not in agreement.release_conditions:
            raise ValueError(f"Condition {condition.value} not in agreement")

        agreement.status = EscrowStatus.TRIGGERED

        return {
            "agreement_id": agreement_id,
            "condition": condition.value,
            "evidence": evidence,
            "status": "triggered",
            "verification_period_days": agreement.verification_period_days,
            "message": f"Release triggered. {agreement.verification_period_days}-day verification period begins.",
        }

    def update_source_code(
        self,
        agreement_id: str,
        version: str,
        commit_hash: str,
        changelog: str,
    ) -> dict:
        """Record a source code update."""
        agreement = self._agreements.get(agreement_id)
        if not agreement:
            raise ValueError(f"Agreement {agreement_id} not found")

        agreement.version = version
        agreement.last_update_date = datetime.now(timezone.utc)

        return {
            "agreement_id": agreement_id,
            "version": version,
            "commit_hash": commit_hash,
            "changelog": changelog,
            "updated_at": agreement.last_update_date.isoformat(),
            "status": "recorded",
        }

    def get_agreement_status(self, agreement_id: str) -> dict:
        """Get the status of an escrow agreement."""
        agreement = self._agreements.get(agreement_id)
        if not agreement:
            raise ValueError(f"Agreement {agreement_id} not found")

        return {
            "agreement_id": agreement_id,
            "status": agreement.status.value,
            "depositor": agreement.depositor.name,
            "beneficiary": agreement.beneficiary.name,
            "escrow_agent": agreement.escrow_agent.name,
            "software": agreement.software_description,
            "version": agreement.version,
            "effective_date": agreement.effective_date.isoformat(),
            "last_update": agreement.last_update_date.isoformat() if agreement.last_update_date else None,
            "update_frequency": agreement.update_frequency,
        }

    def generate_agreement_document(self, agreement: EscrowAgreement) -> str:
        """Generate a plain text agreement document."""
        doc = f"""
SOURCE CODE ESCROW AGREEMENT

Agreement ID: {agreement.agreement_id}
Effective Date: {agreement.effective_date.strftime('%B %d, %Y')}

PARTIES:

Depositor: {agreement.depositor.name}
Address: {agreement.depositor.address}
Contact: {agreement.depositor.contact_name}
Email: {agreement.depositor.contact_email}

Beneficiary: {agreement.beneficiary.name}
Address: {agreement.beneficiary.address}
Contact: {agreement.beneficiary.contact_name}
Email: {agreement.beneficiary.contact_email}

Escrow Agent: {agreement.escrow_agent.name}
Address: {agreement.escrow_agent.address}
Contact: {agreement.escrow_agent.contact_name}
Email: {agreement.escrow_agent.contact_email}

SOFTWARE DESCRIPTION:
{agreement.software_description}

Version: {agreement.version}
Repository: {agreement.repository_url}

BUILD INSTRUCTIONS:
{agreement.build_instructions}

DEPENDENCIES:
{agreement.dependency_list}

RELEASE CONDITIONS:
The Escrow Agent shall release the source code to Beneficiary upon occurrence of:
{chr(10).join(f"- {c.value}" for c in agreement.release_conditions)}

RELEASE PROCEDURE:
{agreement.release_procedure}

VERIFICATION PERIOD:
{agreement.verification_period_days} days from notification

FINANCIAL TERMS:
Annual Escrow Fee: ${agreement.escrow_fee_annual:,.2f}
Release Fee: ${agreement.release_fee:,.2f}

MAINTENANCE OBLIGATIONS:
Update Frequency: {agreement.update_frequency}
Last Update: {agreement.last_update_date.strftime('%B %d, %Y') if agreement.last_update_date else 'N/A'}
Update Verification: {'Required' if agreement.update_verification else 'Not Required'}

CONFIDENTIALITY:
{agreement.confidentiality_clause}

LICENSE TERMS:
{agreement.license_terms}

SUPPORT OBLIGATIONS:
{agreement.support_obligations}

SIGNATURES:

Depositor: _________________________ Date: _________

Beneficiary: _________________________ Date: _________

Escrow Agent: _________________________ Date: _________
"""
        return doc.strip()


# Global instance
_escrow_manager: EscrowManager | None = None


def get_escrow_manager() -> EscrowManager:
    """Get the global escrow manager."""
    global _escrow_manager
    if _escrow_manager is None:
        _escrow_manager = EscrowManager()
    return _escrow_manager
