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
BOUNDARIES = (0.12, 0.235, 0.305, 0.505, 0.70, 0.80)
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
    return datetime.strptime(raw, "%Y-%m-%d %I:%M%p").replace(tzinfo=ZoneInfo("America/New_York"))


def choose_latest(html_text, base_url, now=None):
    now = now or datetime.now(timezone.utc)
    parser = ListingLinks(base_url)
    parser.feed(html_text)
    valid = [(report_datetime(url), url) for url in set(parser.links)]
    valid = [(when, url) for when, url in valid if when.astimezone(timezone.utc) <= now + timedelta(minutes=5)]
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
            if not game_date or not matchup or not team:
                continue
            status = status_cell.strip()
            player = player_cell.strip()
            if status not in STATUSES or not player or "," not in player:
                continue
            state, label, color = STATUSES[status]
            key = "|".join((game_date, matchup, team, player))
            rows[key] = {
                "game_date": game_date, "matchup": matchup, "team": team,
                "player": player, "official_status": status,
                "state": state, "label_ko": label, "color": color,
                "lineup": "not_verified",  # injury report is NOT a starter report
            }
    if not rows:
        raise ValueError("no unambiguous player statuses parsed; previous data retained")
    return rows


def parse_pdf(pdf_bytes):
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("pdfplumber dependency unavailable") from exc
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        if not 1 <= len(pdf.pages) <= 40:
            raise ValueError("NBA PDF page count outside safety bounds")
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
    rows = parse_pdf(pdf)
    current = {
        "league": "NBA", "source": "NBA official injury report",
        "source_url": url, "report_at_et": reported.isoformat(),
        "report_at_utc": reported.astimezone(timezone.utc).isoformat(),
        "lineup_source_verified": False, "publication_status": "NOT_APPROVED",
        "players": rows,
    }
    changes, baseline = compare(previous, current)
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
