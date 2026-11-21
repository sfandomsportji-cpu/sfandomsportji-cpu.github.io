#!/usr/bin/env python3
"""SFANDOM NBA official injury watcher. AUDIT ONLY: never publishes to the website.

Reads only NBA's public injury-report listing and linked PDF. A missing player is
UNKNOWN, not AVAILABLE. This report does NOT establish starting lineups.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import sports_clock
import injury_quality

LISTINGS = (
    "https://www.nba.com/players/injury-report",
    "https://official.nba.com/nba-injury-report-2026-27-season/",
)
PDF_PATTERN = re.compile(r"^/referee/injury/Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})(AM|PM)\.pdf$")
STATUSES = {
    "Probable": ("probable", "출전 예정", "green"),
    "Available": ("available", "출전 가능", "blue"),
    "Out": ("out", "출전 불가", "red"),
    "Questionable": ("questionable", "출전 미정", "gray"),
    "Doubtful": ("doubtful", "출전 불확실", "gray"),
}
# Relative PDF table boundaries: date, time, matchup, team, player, status, reason.
BOUNDARIES = (0.12, 0.23, 0.30, 0.495, 0.67, 0.78)
MAX_PDF_BYTES = 12 * 1024 * 1024
MAX_AGE = timedelta(minutes=90)
UA = "SFANDOM-NBA-injury-audit/1.0 (https://sfandom.com/)"


class ListingLinks(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base = base
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        url = urljoin(self.base, href)
        p = urlparse(url)
        if p.scheme == "https" and p.hostname == "ak-static.cms.nba.com" and PDF_PATTERN.fullmatch(p.path):
            self.links.append(url)


def report_datetime(url):
    m = PDF_PATTERN.fullmatch(urlparse(url).path)
    if not m:
        raise ValueError("unrecognized NBA report URL")
    raw = f"{m[1]} {m[2]}:{m[3]}{m[4]}"
    # NBA filename is ET, without a numeric offset. Reject ambiguous DST-hour
    # reports rather than choosing the wrong UTC/KST instant.
    naive = datetime.strptime(raw, "%Y-%m-%d %I:%M%p")
    return sports_clock.attach_local_clock(naive, "America/New_York")


def choose_latest(html_text, base_url, now=None):
    now = now or datetime.now(timezone.utc)
    parser = ListingLinks(base_url)
    parser.feed(html_text)
    valid = []
    for url in set(parser.links):
        try:
            reported = report_datetime(url)
        except ValueError:
            continue  # malformed timestamp or DST ambiguity: never guess
        if reported.astimezone(timezone.utc) <= now + timedelta(minutes=5):
            valid.append((reported, url))
    if not valid:
        raise ValueError("no verified official NBA PDF link")
    when, url = max(valid, key=lambda pair: pair[0])
    if now - when.astimezone(timezone.utc) > MAX_AGE:
        raise ValueError("official report link is stale")
    return url, when


def fetch_bytes(url, max_bytes):
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/pdf"})
    with urllib.request.urlopen(request, timeout=16) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("NBA response too large")
    return data


def fetch_official(now=None):
    errors = []
    for listing in LISTINGS:
        try:
            html_text = fetch_bytes(listing, 3_000_000).decode("utf-8", errors="replace")
            url, reported = choose_latest(html_text, listing, now)
            pdf = fetch_bytes(url, MAX_PDF_BYTES)
            if not pdf.startswith(b"%PDF-"):
                raise ValueError("NBA report is not a PDF")
            return url, reported, pdf
        except (OSError, ValueError, UnicodeError, TimeoutError) as exc:
            errors.append(f"{urlparse(listing).hostname}:{type(exc).__name__}")
    raise RuntimeError("NBA official source unavailable: " + "; ".join(errors))


def lines_on_page(page):
    """Group PDF words into visual lines, preserving their horizontal columns."""
    words = sorted(page.extract_words(x_tolerance=1.5, y_tolerance=2.5),
                   key=lambda w: (float(w["top"]), float(w["x0"])))
    groups = []
    for word in words:
        if not groups or abs(float(word["top"]) - float(groups[-1][0]["top"])) > 2.5:
            groups.append([word])
        else:
            groups[-1].append(word)
    for group in groups:
        cells = [""] * 7
        for word in sorted(group, key=lambda w: float(w["x0"])):
            x = float(word["x0"]) / float(page.width)
            index = sum(x >= edge for edge in BOUNDARIES)
            cells[index] = (cells[index] + " " + word["text"]).strip()
        yield cells


def parse_pages(pages):
    """Conservative table parser: if ambiguous, skip instead of guessing."""
    rows = {}
    game_date = matchup = team = ""
    for page in pages:
        for date_cell, _time, match_cell, team_cell, player_cell, status_cell, _reason in lines_on_page(page):
            # Repeated title on every PDF page falls into the TEAM column.
            # Without this guard, continued player rows are silently assigned
            # to fake team "Injury Report:" instead of the previous real team.
            if team_cell.strip().startswith("Injury Report:"):
                continue
            if "Game Date" in date_cell or "Injury Report" in date_cell:
                continue
            date_match = re.search(r"\b\d{2}/\d{2}/\d{4}\b", date_cell)
            if date_match:
                game_date = datetime.strptime(date_match.group(), "%m/%d/%Y").date().isoformat()
            match = re.search(r"\b[A-Z]{2,3}@[A-Z]{2,3}\b", match_cell)
            if match:
                matchup = match.group()
                team = ""  # never carry team across matchups
            if team_cell:
                team = team_cell.strip()
            status = status_cell.strip()
            player = player_cell.strip()
            # Valid-looking status without a team/matchup is NOT silently
            # discarded: a PDF column shift can attach it to the wrong game.
            if status in STATUSES or "," in player:
                if not game_date or not matchup or not team:
                    raise injury_quality.DataQualityError(
                        "status row without a verified game/date/team")
                if status not in STATUSES or "," not in player:
                    raise injury_quality.DataQualityError(
                        "unexpected status/player column alignment")
            else:
                continue
            # A valid status must belong to one of the two teams named in the
            # matchup. This is not inferred from a player's name or old row.
            injury_quality.validate_team_matchup(matchup, team)
            state, label, color = STATUSES[status]
            key = "|".join((game_date, matchup, team, player))
            if key in rows:
                raise injury_quality.DataQualityError(
                    "duplicate player identity in official report")
            rows[key] = {
                "game_date": game_date, "matchup": matchup, "team": team,
                "player": player, "official_status": status,
                "state": state, "label_ko": label, "color": color,
                "lineup": "not_verified",  # injury report is NOT a starter report
            }
    if not rows:
        raise ValueError("no unambiguous player statuses parsed; previous data retained")
    return rows


def validate_report_header(first_page_text: str, expected_time: datetime) -> None:
    """Ensure PDF body matches the timestamp claimed by the official PDF URL.

    A valid filename with an outdated or corrupted PDF body is not trustworthy.
    """
    found = re.search(
        r"Injury\s+Report:\s*(\d{1,2}/\d{1,2}/\d{2,4})\s+"
        r"(\d{1,2}:\d{2})\s*(AM|PM)",
        first_page_text or "", flags=re.IGNORECASE)
    if not found:
        raise injury_quality.DataQualityError(
            "official PDF title or report timestamp is missing")
    stamp = f"{found[1]} {found[2]} {found[3].upper()}"
    fmt = "%m/%d/%Y %I:%M %p" if len(found[1].split("/")[-1]) == 4 else "%m/%d/%y %I:%M %p"
    actual_local = datetime.strptime(stamp, fmt)
    if actual_local != expected_time.replace(tzinfo=None):
        raise injury_quality.DataQualityError(
            "official PDF title timestamp does not match filename")


def parse_pdf(pdf_bytes, *, expected_report_time=None):
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("pdfplumber dependency unavailable") from exc
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        if not 1 <= len(pdf.pages) <= 40:
            raise ValueError("NBA PDF page count outside safety bounds")
        if expected_report_time is not None:
            validate_report_header(
                pdf.pages[0].extract_text() or "", expected_report_time)
        return parse_pages(pdf.pages)


def compare(previous, current):
    if not previous or not previous.get("players"):
        return [], True
    old = previous["players"]
    changes = []
    for key, item in current["players"].items():
        prior = old.get(key)
        # Disappearance is NOT availability, and a newly appearing row is
        # reported as NEW, not a reversal of a previously established status.
        if prior is None:
            changes.append({"type": "new", "key": key, "before": None,
                            "after": item["official_status"]})
        elif prior["official_status"] != item["official_status"]:
            changes.append({"type": "changed", "key": key,
                            "before": prior["official_status"],
                            "after": item["official_status"]})
    return changes, False


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--previous", default=".monitor/previous.json")
    ap.add_argument("--output", default=".monitor/current.json")
    ap.add_argument("--changes", default=".monitor/changes.json")
    args = ap.parse_args(argv)
    previous = {}
    if Path(args.previous).is_file():
        previous = json.loads(Path(args.previous).read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    url, reported, pdf = fetch_official(now)
    rows = parse_pdf(pdf, expected_report_time=reported)
    checked = datetime.now(timezone.utc)
    age = sports_clock.freshness(
        reported.astimezone(timezone.utc).isoformat(),
        checked.isoformat(), checked.isoformat(),
        max_source_age_minutes=90)
    if age["state"] != "CURRENT":
        raise ValueError("official source age or clock is not valid: " + age["reason"])
    quality = injury_quality.validate_snapshot(previous, rows, reported.isoformat())
    current = {
        "league": "NBA", "source": "NBA official injury report",
        "checked_at_utc": checked.isoformat(),
        "checked_at_kst": checked.astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
        "freshness": age["state"],
        "quality": quality,
        "public_display_allowed": False,
        "source_url": url, "report_at_et": reported.isoformat(),
        "report_at_utc": reported.astimezone(timezone.utc).isoformat(),
        "lineup_source_verified": False, "publication_status": "NOT_APPROVED",
        "players": rows,
    }
    changes, baseline = compare(previous, current)
    previous_checked = previous.get("checked_at_utc")
    if previous_checked:
        gap_minutes = (checked - sports_clock.parse_aware(previous_checked).astimezone(timezone.utc)).total_seconds() / 60
        current["check_gap_minutes"] = round(gap_minutes, 2)
        current["schedule_gap_alert"] = gap_minutes > 22
        # A missed run must trigger human audit, not permanently lock out
        # recovery: a freshly verified report may become the new baseline.
        current["review_required"] = current["schedule_gap_alert"]
    else:
        current["check_gap_minutes"] = None
        current["schedule_gap_alert"] = None
        current["review_required"] = True  # no history to compare yet
    atomic_json(args.output, current)
    atomic_json(args.changes, {
        "source_url": url, "initial_baseline": baseline, "changes": changes,
        "publication_status": "NOT_APPROVED",
    })
    print(json.dumps({"report_at_utc": current["report_at_utc"],
                      "players": len(rows), "changes": len(changes),
                      "initial_baseline": baseline, "publish": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        # Fail closed: no new snapshot is written and no old state is made fresh.
        print(f"INJURY_MONITOR_FAILED: {type(exc).__name__}: {str(exc)[:220]}", file=sys.stderr)
        sys.exit(1)
