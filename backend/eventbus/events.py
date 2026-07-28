"""
Event type constants for the EventBus system.
Defines all topic strings used across the pipeline for pub/sub communication.
"""


class EventType:
    """Centralised event type registry.

    Naming convention: <domain>.<action>.<qualifier>
    Wildcard subscriptions use '*' as the last segment:
        e.g. 'data.*' matches 'data.fetch.start', 'data.fetch.complete', etc.
    """

    # ── Data collection events ────────────────────────────────────────────────
    DATA_FETCH_START = "data.fetch.start"
    DATA_FETCH_COMPLETE = "data.fetch.complete"
    DATA_FETCH_ERROR = "data.fetch.error"

    # ── Analysis events ───────────────────────────────────────────────────────
    ANALYSIS_START = "analysis.start"
    ANALYSIS_COMPLETE = "analysis.complete"
    ANALYSIS_ERROR = "analysis.error"

    # ── Signal events ─────────────────────────────────────────────────────────
    SIGNAL_GENERATED = "signal.generated"
    SIGNAL_ALERT = "signal.alert"

    # ── Scoring events ────────────────────────────────────────────────────────
    SCORING_START = "scoring.start"
    SCORING_COMPLETE = "scoring.complete"

    # ── System events ─────────────────────────────────────────────────────────
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_HEALTH = "system.health"
    SYSTEM_CONFIG_CHANGE = "system.config.change"

    # ── Legacy topic aliases (compatibility with existing WebSocket topics) ───
    GEXMETRIX_SNAPSHOT = "GEXMETRIX_SNAPSHOT"
    SIGNAL = "SIGNAL"
    INCIDENT = "INCIDENT"
    CONFIG = "CONFIG"


# Convenience: all event types as a flat set for validation
ALL_EVENT_TYPES: frozenset[str] = frozenset(
    v for v in vars(EventType).values() if isinstance(v, str) and not v.startswith("_")
)
