#!/usr/bin/env python3
"""SFANDOM shared sports clock: never equate ET/venue date with Korean calendar date.

Sports supported: soccer, basketball and baseball. All input must have a year and
either a UTC offset or an IANA source timezone. No guesswork for DST gaps/folds.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
KST = ZoneInfo("Asia/Seoul")
SPORTS = frozenset(("soccer", "basketball", "baseball"))
DEFAULT_MAX_AGE = timedelta(minutes=20)


def attach_local_clock(local_naive: datetime, tz_name: str, *, fold=None) -> datetime:
    """Only for sources that provide a bare venue-local time.

    Nonexistent DST times are rejected. Ambiguous DST times require explicit fold.
    """
    if local_naive.tzinfo is not None:
        raise ValueError("local_naive must have no timezone; use aware ISO input directly")
    tz = ZoneInfo(tz_name)
    options = [local_naive.replace(tzinfo=tz, fold=f) for f in (0, 1)]
    valid = [x for x in options if x.astimezone(UTC).astimezone(tz).replace(tzinfo=None) == local_naive]
    if not valid:
        raise ValueError("nonexistent local time (DST gap)")
    if valid[0].utcoffset() != valid[-1].utcoffset() and fold is None:
        raise ValueError("ambiguous local time (DST fold); specify fold")
    if fold not in (None, 0, 1):
        raise ValueError("fold must be 0, 1, or None")
    selected = options[fold or 0]
    if selected not in valid:
        raise ValueError("invalid fold")
    return selected


def parse_aware(iso: str) -> datetime:
    if not isinstance(iso, str) or not iso.strip():
        raise ValueError("missing ISO timestamp")
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp must include UTC offset or Z")
    return dt


def event_clock(sport: str, provider: str, event_id: str, starts_at: str, venue_zone: str) -> dict:
    if sport not in SPORTS:
        raise ValueError("unsupported sport")
    if not provider or not event_id or "|" in provider or "|" in event_id:
        raise ValueError("provider and event id required")
    tz = ZoneInfo(venue_zone)
    original = parse_aware(starts_at)
    when_utc = original.astimezone(UTC)
    when_kst = when_utc.astimezone(KST)
    when_local = when_utc.astimezone(tz)
    if not (datetime(2000, 1, 1, tzinfo=UTC) <= when_utc <= datetime(2100, 1, 1, tzinfo=UTC)):
        raise ValueError("event datetime outside accepted range")
    return {
        "event_key": "|".join((sport, provider, event_id)),
        "sport": sport, "provider": provider, "provider_event_id": event_id,
        "source_time": original.isoformat(),
        "start_utc": when_utc.isoformat(),
        "start_kst": when_kst.isoformat(),
        "date_kst": when_kst.date().isoformat(),
        "venue_zone": venue_zone,
        "start_venue": when_local.isoformat(),
        "date_venue": when_local.date().isoformat(),
        "crosses_calendar_day": when_kst.date() != when_local.date(),
    }


def freshness(source_iso: str, observed_iso: str, checked_iso: str,
              *, max_source_age_minutes=90, max_job_delay_minutes=5) -> dict:
    """Data is current only when provider report and collection clocks make sense.

    source_at: provider-reported publication timestamp; observed_at: actual
    collection moment; checked_at: script processing moment, NOT scheduled cron.
    """
    source = parse_aware(source_iso).astimezone(UTC)
    observed = parse_aware(observed_iso).astimezone(UTC)
    checked = parse_aware(checked_iso).astimezone(UTC)
    clock_skew = timedelta(minutes=2)
    if source > observed + clock_skew or observed > checked + clock_skew:
        return {"state": "BLOCKED", "reason": "clock_order_conflict"}
    if checked - source > timedelta(minutes=max_source_age_minutes):
        return {"state": "STALE", "reason": "source_too_old"}
    if checked - observed > timedelta(minutes=max_job_delay_minutes):
        return {"state": "STALE", "reason": "collection_processing_delay"}
    return {"state": "CURRENT", "reason": None}


def scheduled_run_health(planned_iso: str, actual_iso: str, *, tolerance_minutes=4) -> dict:
    planned = parse_aware(planned_iso).astimezone(UTC)
    actual = parse_aware(actual_iso).astimezone(UTC)
    seconds = (actual - planned).total_seconds()
    if seconds < -120:
        return {"state": "BLOCKED", "delay_seconds": seconds}
    return {"state": "DELAYED" if seconds > tolerance_minutes * 60 else "ON_TIME",
            "delay_seconds": seconds}
