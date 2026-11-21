#!/usr/bin/env python3
"""Failure classification -> recovery stage. Standard library only.

Stage 1: transient collection failure -> bounded retry, official alternate URL.
Stage 2: bad data or code -> quarantine new data, keep last-known-good.
Stage 3: system failure / unknown -> safe mode (publication blocked).

Rules that never change:
- publish is always False here. Resuming needs revalidation AND operator approval.
- Anything unclassified or any internal error escalates to stage 3, never down.
"""
from dataclasses import dataclass, field

MAX_RETRIES = 3          # per 10-minute run, with backoff set by the caller
MAX_GAP_MINUTES = 22     # collection gap that forces safe mode

TRANSIENT = {"source_timeout", "source_http_error", "source_dns_error"}
BAD_DATA = {"invalid_data", "wrong_match", "partial_parse", "layout_changed",
            "time_ambiguous", "time_reversal", "stale_source"}
SYSTEM = {"collector_failed", "build_failed", "clock_module_failed",
          "state_corrupt", "recovery_error"}
# Retrying cannot fix these; go straight to a human.
NO_RETRY = {"time_ambiguous", "time_reversal", "layout_changed"}


@dataclass(frozen=True)
class Decision:
    stage: int
    kind: str
    actions: tuple = field(default_factory=tuple)
    publish: bool = False
    alert_operator: bool = False
    reason: str = ""


SAFE = Decision(3, "unknown",
                ("preserve_last_known_good", "activate_safe_mode", "alert_operator"),
                False, True, "fail_closed_default")


def decide(kind, consecutive_failures=1, gap_minutes=0.0):
    try:
        if kind in SYSTEM:
            return Decision(3, kind, SAFE.actions, False, True, "system_failure")
        if gap_minutes is not None and gap_minutes > MAX_GAP_MINUTES:
            return Decision(3, kind, SAFE.actions, False, True, "collection_gap_over_22m")
        if kind in TRANSIENT:
            if consecutive_failures > MAX_RETRIES:
                return Decision(3, kind, SAFE.actions, False, True, "retries_exhausted")
            return Decision(1, kind,
                            ("retry_with_limits", "try_official_alternate_source",
                             "revalidate_source_and_timestamp"),
                            False, False, "transient")
        if kind in BAD_DATA:
            actions = ("quarantine_new_data", "block_publication",
                       "preserve_last_known_good", "alert_operator")
            if kind not in NO_RETRY:
                actions += ("revalidate_with_known_good_parser",)
            return Decision(2, kind, actions, False, True, "bad_data_or_match")
        return Decision(3, kind, SAFE.actions, False, True, "unclassified")
    except Exception:
        return SAFE


def classify_exception(exc):
    """Map a collector exception to a failure kind. Unknown -> "unknown" (stage 3)."""
    try:
        # A typed error (e.g. ESPNAdapterError.failure_kind) is more reliable than
        # message text. Only kinds this policy knows are trusted; others fall through.
        declared = getattr(exc, "failure_kind", None)
        if isinstance(declared, str) and declared in (TRANSIENT | BAD_DATA | SYSTEM):
            return declared
        name = type(exc).__name__
        msg = str(exc).lower()
        if isinstance(exc, (TimeoutError, ConnectionError)) or "source unavailable" in msg:
            return "source_timeout"
        if "dependency unavailable" in msg:
            return "collector_failed"
        if "ambiguous local time" in msg or "nonexistent local time" in msg or "dst" in msg:
            return "time_ambiguous"
        if "source age or clock" in msg or "link is stale" in msg:
            return "stale_source"
        if ("sharp row drop" in msg or "no unambiguous player statuses" in msg
                or "missing required player field" in msg):
            return "partial_parse"
        if ("page count" in msg or "report header" in msg or "not a pdf" in msg
                or "unrecognized nba report url" in msg or "no verified official" in msg):
            return "layout_changed"
        if name == "DataQualityError":
            return "invalid_data"
        return "unknown"
    except Exception:
        return "unknown"


def may_resume_publication(revalidated, operator_approved):
    """Recovery of collection is automatic; resuming publication is not."""
    return revalidated is True and operator_approved is True
