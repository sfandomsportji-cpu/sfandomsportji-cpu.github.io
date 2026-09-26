#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
PROMPT_FILE = ROOT / "scripts" / "edition_prompt.md"
ARCHIVE_ROOT = ROOT / "archive" / "morning"

SLOTS = {
    "daily_news": "daily-news-slot",
    "kairo_feature": "kairo-feature-slot",
    "next_match": "next-match-slot",
    "player_spotlight": "player-spotlight-slot",
}

EXPECTED_CLASSES = {
    "daily-news-slot": "morning-edition",
    "kairo-feature-slot": "kairo-feature",
    "next-match-slot": "next-match-edition",
    "player-spotlight-slot": "player-spotlight",
}


def section_pattern(section_id: str) -> re.Pattern[str]:
    return re.compile(
        rf'<section\b(?=[^>]*\bid=["\']{re.escape(section_id)}["\'])[^>]*>.*?</section>',
        re.IGNORECASE | re.DOTALL,
    )


def extract_section(html: str, section_id: str) -> str:
    match = section_pattern(section_id).search(html)
    if not match:
        raise RuntimeError(f"Could not find section id={section_id!r} in index.html")
    return match.group(0)


def clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def validate_section(section_id: str, html: str) -> None:
    if not isinstance(html, str) or not html.strip():
        raise ValueError(f"{section_id}: empty section HTML")
    value = html.strip()
    if not re.match(r"^<section\b", value, flags=re.IGNORECASE):
        raise ValueError(f"{section_id}: output must start with <section>")
    if not value.lower().endswith("</section>"):
        raise ValueError(f"{section_id}: output must end with </section>")
    if not re.search(rf'\bid=["\']{re.escape(section_id)}["\']', value, flags=re.IGNORECASE):
        raise ValueError(f"{section_id}: required id is missing")
    expected_class = EXPECTED_CLASSES[section_id]
    if not re.search(rf'\bclass=["\'][^"\']*\b{re.escape(expected_class)}\b', value, flags=re.IGNORECASE):
        raise ValueError(f"{section_id}: required class {expected_class!r} is missing")
    lowered = value.lower()
    forbidden = ("<script", "<iframe", "javascript:", "data:text/html")
    if any(token in lowered for token in forbidden):
        raise ValueError(f"{section_id}: forbidden active content detected")
    if len(re.findall(r"<section\b", value, flags=re.IGNORECASE)) != 1:
        raise ValueError(f"{section_id}: nested <section> tags are not allowed")


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    if not INDEX.exists():
        raise FileNotFoundError(f"Missing {INDEX}")
    if not PROMPT_FILE.exists():
        raise FileNotFoundError(f"Missing {PROMPT_FILE}")

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    date_kst = now.strftime("%Y-%m-%d")
    html = INDEX.read_text(encoding="utf-8")
    base_prompt = PROMPT_FILE.read_text(encoding="utf-8").strip()

    current_sections = {
        key: extract_section(html, section_id)
        for key, section_id in SLOTS.items()
    }

    reference = "\n\n".join(
        f"### CURRENT TEMPLATE: {key} / {SLOTS[key]}\n{current_sections[key]}"
        for key in SLOTS
    )

    request = f"""{base_prompt}

TODAY_KST: {date_kst}

Use the following current production sections only as structural/style templates.
Keep their required IDs/classes and overall DOM pattern, but replace stale editorial facts,
dates, copy, source links, official image URLs, and statistics with verified current material.

{reference}

Return ONLY one valid JSON object with exactly these keys:
{{
  "daily_news": {{"section_html": "..."}},
  "kairo_feature": {{"section_html": "..."}},
  "next_match": {{"section_html": "..."}},
  "player_spotlight": {{"section_html": "..."}}
}}

Do not wrap the JSON in Markdown fences.
"""

    model = os.environ.get("OPENAI_MODEL", "gpt-5.6-terra")
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        tools=[{"type": "web_search"}],
        input=request,
    )

    raw = clean_json_text(response.output_text)
    payload = json.loads(raw)

    if set(payload.keys()) != set(SLOTS.keys()):
        raise ValueError(f"Unexpected top-level keys: {sorted(payload.keys())}")

    replacements = {}
    for key, section_id in SLOTS.items():
        block = payload[key]
        if not isinstance(block, dict) or "section_html" not in block:
            raise ValueError(f"{key}: missing section_html")
        section_html = block["section_html"].strip()
        validate_section(section_id, section_html)
        replacements[section_id] = section_html

    if all(current_sections[key].strip() == replacements[SLOTS[key]].strip() for key in SLOTS):
        print("No editorial changes generated.")
        return

    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    archive_name = now.strftime("%Y-%m-%d-%H%M%S") + "-before.html"
    archive_path = ARCHIVE_ROOT / archive_name
    archive_body = [
        "<!-- SFANDOM morning slots snapshot before automated proposal -->",
        f"<!-- Captured: {now.isoformat()} -->",
        "",
    ]
    for key in SLOTS:
        archive_body.append(f"<!-- {key} -->")
        archive_body.append(current_sections[key])
        archive_body.append("")
    archive_path.write_text("\n".join(archive_body), encoding="utf-8")

    updated = html
    for section_id, new_section in replacements.items():
        pattern = section_pattern(section_id)
        updated, count = pattern.subn(lambda _: new_section, updated, count=1)
        if count != 1:
            raise RuntimeError(f"{section_id}: expected one replacement, got {count}")

    for section_id in SLOTS.values():
        if len(section_pattern(section_id).findall(updated)) != 1:
            raise RuntimeError(f"{section_id}: post-write validation failed")

    INDEX.write_text(updated, encoding="utf-8")
    print(f"Updated 4 morning-edition sections for {date_kst} KST")
    print(f"Archived previous slots at {archive_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
