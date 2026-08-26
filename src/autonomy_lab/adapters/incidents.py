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
    )
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
    )
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
