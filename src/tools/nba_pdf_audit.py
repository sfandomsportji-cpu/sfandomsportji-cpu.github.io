#!/usr/bin/env python3
"""Offline independent-engine audit of official NBA injury PDF samples.

Reads LOCAL PDF files only. NO networking, publication, or site writes.
Uses pdfplumber (production parser) and PyMuPDF (independent page word engine)
to compare every (game date, matchup, team, player, status) record.
This checks actual source PDFs; synthetic fixtures alone cannot do that.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

import nba_injury_monitor as monitor
import injury_quality


def extract_independent(pdf_bytes: bytes) -> tuple[dict[str, str], list[int]]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("manual audit requires PyMuPDF") from exc
    rows: dict[str, str] = {}
    counts: list[int] = []
    game_date = matchup = team = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            words = sorted(page.get_text("words"), key=lambda w: (float(w[1]), float(w[0])))
            lines = []
            for word in words:
                if not lines or abs(float(word[1]) - float(lines[-1][0][1])) > 2.5:
                    lines.append([word])
                else:
                    lines[-1].append(word)
            page_count = 0
            for line in lines:
                cells = [""] * 7
                for word in sorted(line, key=lambda w: float(w[0])):
                    col = sum(float(word[0]) / float(page.rect.width) >= edge
                              for edge in monitor.BOUNDARIES)
                    cells[col] = (cells[col] + " " + str(word[4])).strip()
                date_cell, _, match_cell, team_cell, player, status, _ = cells
                if team_cell.startswith("Injury Report:") or team_cell == "Page":
                    continue
                if "Game Date" in date_cell:
                    continue
                date_match = re.search(r"\b\d{2}/\d{2}/\d{4}\b", date_cell)
                if date_match:
                    game_date = datetime.strptime(date_match.group(), "%m/%d/%Y").date().isoformat()
                match = re.search(r"\b[A-Z]{2,3}@[A-Z]{2,3}\b", match_cell)
                if match:
                    matchup = match.group()
                    team = ""
                if team_cell in injury_quality.NBA_TEAMS:
                    team = team_cell
                if status in injury_quality.STATUSES and "," in player:
                    injury_quality.validate_team_matchup(matchup, team)
                    if not game_date:
                        raise injury_quality.DataQualityError("date lost in independent parser")
                    key = "|".join((game_date, matchup, team, player))
                    if key in rows:
                        raise injury_quality.DataQualityError("duplicate independent row")
                    rows[key] = status
                    page_count += 1
            counts.append(page_count)
    return rows, counts


def audit_pdf(path: str, url: str) -> dict:
    pdf = Path(path).read_bytes()
    if not pdf.startswith(b"%PDF-"):
        raise ValueError("not a PDF source")
    expected = monitor.report_datetime(url)
    parsed = monitor.parse_pdf(pdf, expected_report_time=expected)
    quality = injury_quality.validate_rows(parsed)
    original = {key: item["official_status"] for key, item in parsed.items()}
    independent, by_page = extract_independent(pdf)
    missing_or_changed = sorted((key, state, independent.get(key)) for key, state in original.items()
                                if independent.get(key) != state)
    extra = sorted(key for key in independent if key not in original)
    if missing_or_changed or extra or len(parsed) != sum(by_page):
        raise injury_quality.DataQualityError(
            f"PDF engine disagreement: missing_or_changed={len(missing_or_changed)} extra={len(extra)}")
    return {
        "source_url": url,
        "pdf_sha256": hashlib.sha256(pdf).hexdigest(),
        "report_at_et": expected.isoformat(),
        "pages": len(by_page),
        "page_status_counts": by_page,
        "player_status_rows": len(parsed),
        "game_team_groups": quality["game_team_groups"],
        "independent_row_mismatch": 0,
        "publication_status": "NOT_APPROVED",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", nargs=2, metavar=("PDF_PATH", "OFFICIAL_PDF_URL"),
                        action="append", required=True, help="repeat for each report")
    args = parser.parse_args(argv)
    try:
        results = [audit_pdf(path, url) for path, url in args.sample]
        print(json.dumps({"state": "PASS", "samples": results,
                          "rows": sum(r["player_status_rows"] for r in results),
                          "publish": False}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"PDF_AUDIT_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
