"""Deterministic in-memory incident evidence for the demonstration."""

from autonomy_lab.domain.autonomy import EvidenceItem, Incident


class IncidentNotFoundError(KeyError):
    """Raised when a requested demonstration incident does not exist."""


_INCIDENTS = {
    "INC-001": Incident(
        incident_id="INC-001",
        service="checkout-api",
        started_at="14:05",
        symptom="HTTP 5xx increased from 0.2% to 8.7%",
    ),
    "INC-002": Incident(
        incident_id="INC-002",
        service="checkout-api",
        started_at="09:12",
        symptom="HTTP 5xx increased from 0.3% to 9.4% after a release",
    ),
    "INC-003": Incident(
        incident_id="INC-003",
        service="payments-api",
        started_at="16:42",
        symptom="HTTP 503 increased from 0.1% to 12.6%",
    ),
    "INC-004": Incident(
        incident_id="INC-004",
        service="profile-api",
        started_at="11:20",
        symptom="p95 latency increased from 180ms to 1450ms with intermittent 5xx",
    ),
}


_EVIDENCE = {
    "INC-001": (
        EvidenceItem(
            source="metrics",
            summary=(
                "Error rate: 13:55=0.2%, 14:05=4.1%, 14:10=8.7%. "
                "p95 latency: 13:55=310ms, 14:10=2840ms."
            ),
        ),
        EvidenceItem(
            source="deployments",
            summary=(
                "checkout-api v2.18.4 deployed at 13:58; change: new payment-provider "
                "timeout configuration."
            ),
        ),
        EvidenceItem(
            source="dependencies",
            summary="payment-provider latency increased shortly after 14:00; no confirmed outage.",
        ),
        EvidenceItem(
            source="runbook",
            summary=(
                "For elevated 5xx after a release: compare dependency latency and deployment "
                "timing; prefer reversible mitigation; do not claim causality from correlation."
            ),
        ),
        EvidenceItem(
            source="previous-incidents",
            summary=(
                "INC-884 had similar symptoms caused by an upstream timeout mismatch; this is "
                "historical context, not evidence of the current root cause."
            ),
        ),
    ),
    "INC-002": (
        EvidenceItem(
            source="metrics",
            summary=(
                "Error rate: 09:05=0.3%, 09:12=6.8%, 09:18=9.4%, 09:30=0.4%. "
                "p95 latency: 09:05=290ms, 09:18=2510ms, 09:30=320ms."
            ),
        ),
        EvidenceItem(
            source="deployments",
            summary=(
                "checkout-api v2.19.1 deployed at 09:08 with payment-provider timeout reduced "
                "from 3s to 800ms. Rollback at 09:24 restored the prior timeout and recovery "
                "followed. A controlled replay reproduced the failure with v2.19.1. Root cause "
                "confirmed for INC-002: the v2.19.1 800ms timeout regression caused the checkout "
                "errors."
            ),
        ),
        EvidenceItem(
            source="dependencies",
            summary=(
                "payment-provider latency remained within its normal range during INC-002; no "
                "provider outage was reported."
            ),
        ),
        EvidenceItem(
            source="runbook",
            summary=(
                "Rollback plus controlled reproduction can establish deployment causality when "
                "the failure disappears after rollback and reproduces with the changed build."
            ),
        ),
        EvidenceItem(
            source="previous-incidents",
            summary=(
                "INC-901 was a separate checkout incident caused by malformed cache headers; it "
                "is historical context and unrelated to INC-002."
            ),
        ),
    ),
    "INC-003": (
        EvidenceItem(
            source="metrics",
            summary=(
                "HTTP 503 rate: 16:35=0.1%, 16:42=7.9%, 16:48=12.6%, 17:12=0.2%. "
                "p95 latency: 16:35=240ms, 16:48=3180ms, 17:12=260ms."
            ),
        ),
        EvidenceItem(
            source="deployments",
            summary=(
                "No payments-api deployment or configuration change occurred in the six hours "
                "before INC-003."
            ),
        ),
        EvidenceItem(
            source="dependencies",
            summary=(
                "payment-provider declared regional incident PP-772 at 16:40 and recovered at "
                "17:05. Root cause confirmed for INC-003: the payment-provider regional outage "
                "caused the downstream 503 errors. payments-api recovery followed provider "
                "recovery."
            ),
        ),
        EvidenceItem(
            source="runbook",
            summary=(
                "An explicit provider incident confirmation, aligned failure and recovery, and no "
                "local change can establish dependency causality."
            ),
        ),
        EvidenceItem(
            source="previous-incidents",
            summary=(
                "INC-744 had payment failures caused by a local certificate expiry; it is not "
                "evidence for the cause of INC-003."
            ),
        ),
    ),
    "INC-004": (
        EvidenceItem(
            source="metrics",
            summary=(
                "p95 latency: 11:10=180ms, 11:20=920ms, 11:28=1450ms, 11:40=1180ms. "
                "HTTP 5xx rate: 11:10=0.1%, 11:28=2.3%, 11:40=1.7%."
            ),
        ),
        EvidenceItem(
            source="deployments",
            summary=(
                "profile-api v4.6.0 deployed at 08:30, nearly three hours before INC-004; no "
                "deployment or configuration change occurred around 11:20."
            ),
        ),
        EvidenceItem(
            source="dependencies",
            summary=(
                "identity-provider latency fluctuated between 11:15 and 11:35 with no confirmed "
                "outage; it returned to baseline while profile-api latency remained elevated."
            ),
        ),
        EvidenceItem(
            source="runbook",
            summary=(
                "Root cause remains unconfirmed for INC-004. Capture distributed traces, database "
                "saturation, and runtime resource evidence before attributing cause; do not promote "
                "timing correlation to causality."
            ),
        ),
        EvidenceItem(
            source="previous-incidents",
            summary=(
                "INC-655 showed similar profile-api latency during memory pressure, but this is "
                "historical context only and does not establish the cause of INC-004."
            ),
        ),
    ),
}


class InMemoryIncidentStore:
    """Read-only fixture store shared by every architecture pattern."""

    def get_incident(self, incident_id: str) -> Incident:
        """Return a known incident or fail with a stable domain-facing error."""
        try:
            return _INCIDENTS[incident_id]
        except KeyError as exc:
            raise IncidentNotFoundError(incident_id) from exc

    def get_evidence(self, incident: Incident) -> tuple[EvidenceItem, ...]:
        """Return evidence for a known incident without external I/O."""
        try:
            return _EVIDENCE[incident.incident_id]
        except KeyError as exc:
            raise IncidentNotFoundError(incident.incident_id) from exc
