#!/usr/bin/env python3
import argparse
import json
import math
import os
import re
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

API = "https://statsapi.mlb.com/api/v1"
UA = "SFANDOM-HighlightBuilder/1.0"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})

TEAM_ABBR = {
    "Arizona Diamondbacks": "AZ", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Athletics": "ATH", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH"
}

BAD_TERMS = [
    "interview", "exclusive angle", "statcast", "data visualization", "radio call",
    "all calls", "curtain call", "field view", "press conference", "postgame"
]
GOOD_TERMS = {
    "walk-off": 120, "walk off": 120, "grand slam": 100, "go-ahead": 90,
    "go ahead": 90, "home run": 80, "homers": 80, "homer": 80,
    "three-run": 70, "two-run": 65, "rbi": 55, "double": 45, "triple": 45,
    "single": 35, "strikes out": 30, "strikeout": 30, "save": 25, "final out": 60,
}


def run(cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True)


def get_json(url):
    r = SESSION.get(url, timeout=40)
    r.raise_for_status()
    return r.json()


def normalize(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower().replace("’", "'"))


def tags_text(item):
    vals = []
    for k in item.get("keywordsAll") or []:
        vals.append(str(k.get("displayName") or k.get("value") or k.get("name") or ""))
    return normalize(" | ".join(vals))


def score_item(item):
    title = normalize(item.get("title"))
    tags = tags_text(item)
    hay = title + " | " + tags
    if any(term in hay for term in BAD_TERMS):
        return -10000
    score = 0
    if "in-game highlight" in tags or "in game highlight" in tags:
        score += 80
    if "game summary" in tags or "condensed game" in title:
        score -= 70
    for term, pts in GOOD_TERMS.items():
        if term in hay:
            score += pts
    playbacks = [p for p in (item.get("playbacks") or []) if p.get("url")]
    if playbacks:
        score += 50
    return score


def playback_quality(p):
    url = p.get("url") or ""
    mp4 = 1 if re.search(r"\.mp4(?:\?|$)", url, re.I) else 0
    w = p.get("width") or 0
    h = p.get("height") or 0
    if not w or not h:
        m = re.search(r"(\d{3,4})x(\d{3,4})", url)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
    return (mp4, int(w) * int(h), int(w), int(h))


def choose_playback(item):
    pbs = [p for p in (item.get("playbacks") or []) if p.get("url")]
    if not pbs:
        return None
    pbs.sort(key=playback_quality, reverse=True)
    return pbs[0]


def choose_highlight(content):
    items = (((content.get("highlights") or {}).get("highlights") or {}).get("items") or [])
    ranked = sorted(items, key=score_item, reverse=True)
    for item in ranked:
        if score_item(item) < 0:
            continue
        pb = choose_playback(item)
        if pb:
            return item, pb
    return None, None


def ffprobe_has_audio(path):
    cp = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
        "stream=index", "-of", "csv=p=0", str(path)
    ], capture_output=True, text=True)
    return bool(cp.stdout.strip())


def download_media(url, dest):
    if re.search(r"\.mp4(?:\?|$)", url, re.I):
        with SESSION.get(url, stream=True, timeout=90) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)
        return
    # HLS or other ffmpeg-readable official playback
    run(["ffmpeg", "-y", "-loglevel", "warning", "-i", url, "-c", "copy", str(dest)])


def font_path(bold=False):
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise RuntimeError("No usable font found")


def fit_text(draw, text, path, max_size, min_size, max_width):
    for size in range(max_size, min_size - 1, -2):
        f = ImageFont.truetype(path, size)
        box = draw.textbbox((0, 0), text, font=f)
        if box[2] - box[0] <= max_width:
            return f
    return ImageFont.truetype(path, min_size)


def overlay_png(path, game, item_title, index, total):
    W, H = 1080, 1920
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    bold = font_path(True)
    reg = font_path(False)
    d.rounded_rectangle((46, 88, W - 46, 292), radius=24, fill=(0, 0, 0, 188), outline=(255, 255, 255, 30), width=2)
    d.rounded_rectangle((46, 1510, W - 46, 1748), radius=24, fill=(0, 0, 0, 190), outline=(255, 255, 255, 30), width=2)
    d.text((82, 120), f"SFANDOM · MLB · {index:02d}/{total:02d}", font=ImageFont.truetype(bold, 30), fill=(244, 244, 246, 255))
    away = game["away_abbr"]
    home = game["home_abbr"]
    score = f"{away} {game['away_score']}  —  {game['home_score']} {home}"
    score_font = fit_text(d, score, bold, 58, 40, 900)
    d.text((82, 182), score, font=score_font, fill=(255, 255, 255, 255))
    d.text((82, 1538), "오늘의 MLB, 결정적 순간만.", font=ImageFont.truetype(bold, 34), fill=(255, 255, 255, 255))
    d.text((82, 1590), "Today’s MLB. Only the moments that mattered.", font=ImageFont.truetype(reg, 26), fill=(210, 210, 216, 255))
    title = re.sub(r"\s+", " ", item_title or "Official MLB highlight").strip()
    if len(title) > 72:
        title = title[:69].rstrip() + "…"
    title_font = fit_text(d, title, reg, 27, 21, 900)
    d.text((82, 1652), title, font=title_font, fill=(178, 178, 186, 255))
    img.save(path)


def make_intro(path, date_text, total):
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), (8, 8, 10))
    d = ImageDraw.Draw(img)
    bold = font_path(True); reg = font_path(False)
    for y in range(0, H, 150):
        s = 10 + ((y // 150) % 2) * 3
        d.rectangle((0, y, W, y + 149), fill=(s, s, s + 2))
    d.rectangle((0, 0, W, 16), fill=(225, 35, 42))
    d.text((72, 108), "SFANDOM · MLB DAILY HIGHLIGHTS", font=ImageFont.truetype(bold, 36), fill=(245,245,247))
    d.text((72, 164), f"{date_text} · {total} FINAL GAMES", font=ImageFont.truetype(reg, 25), fill=(150,150,158))
    d.text((72, 472), "오늘의 MLB,", font=ImageFont.truetype(bold, 76), fill=(255,255,255))
    d.text((72, 570), "결정적 순간만.", font=ImageFont.truetype(bold, 76), fill=(225,35,42))
    d.text((72, 700), "Today’s MLB. Only the moments that mattered.", font=ImageFont.truetype(reg, 31), fill=(195,195,202))
    d.text((72, 1520), "OFFICIAL MLB PLAYBACKS", font=ImageFont.truetype(bold, 30), fill=(235,235,238))
    d.text((72, 1570), "PREVIEW · Ji approval required before publishing", font=ImageFont.truetype(reg, 23), fill=(150,150,158))
    img.save(path)


def make_end(path):
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), (8, 8, 10))
    d = ImageDraw.Draw(img)
    bold = font_path(True); reg = font_path(False)
    d.rectangle((0, 0, W, 16), fill=(225, 35, 42))
    d.text((72, 450), "SFANDOM", font=ImageFont.truetype(bold, 86), fill=(255,255,255))
    d.text((72, 570), "경기는 끝나도, 데이터는 남습니다.", font=ImageFont.truetype(bold, 38), fill=(245,245,247))
    d.text((72, 632), "The game ends. The data keeps telling the story.", font=ImageFont.truetype(reg, 28), fill=(190,190,198))
    d.text((72, 1510), "PREVIEW ONLY", font=ImageFont.truetype(bold, 30), fill=(225,35,42))
    d.text((72, 1560), "No publishing before Ji approval.", font=ImageFont.truetype(reg, 24), fill=(155,155,162))
    img.save(path)


def still_to_video(png, out, dur):
    run([
        "ffmpeg", "-y", "-loglevel", "warning", "-loop", "1", "-t", str(dur), "-i", str(png),
        "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-vf", "scale=1080:1920,fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)
    ])


def transform_clip(src, overlay, out, seconds=5.0):
    has_audio = ffprobe_has_audio(src)
    filt = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=24:12[bg2];"
        "[fg]scale=1080:-2:force_original_aspect_ratio=decrease[fg2];"
        "[bg2][fg2]overlay=(W-w)/2:(H-h)/2[base];"
        "[base][1:v]overlay=0:0,fps=30,format=yuv420p[outv]"
    )
    cmd = ["ffmpeg", "-y", "-loglevel", "warning", "-t", str(seconds), "-i", str(src), "-loop", "1", "-t", str(seconds), "-i", str(overlay)]
    if has_audio:
        cmd += ["-filter_complex", filt, "-map", "[outv]", "-map", "0:a:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)]
    else:
        cmd += ["-f", "lavfi", "-t", str(seconds), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000", "-filter_complex", filt, "-map", "[outv]", "-map", "2:a:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)]
    run(cmd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--out", default="output")
    args = ap.parse_args()
    outdir = Path(args.out)
    rawdir = outdir / "raw"
    segdir = outdir / "segments"
    outdir.mkdir(parents=True, exist_ok=True)
    rawdir.mkdir(exist_ok=True)
    segdir.mkdir(exist_ok=True)

    schedule = get_json(f"{API}/schedule?sportId=1&date={args.date}")
    games_raw = [g for d in schedule.get("dates", []) for g in d.get("games", [])]
    games_final = [g for g in games_raw if (g.get("status") or {}).get("abstractGameState") == "Final"]
    if not games_final:
        raise RuntimeError("No Final MLB games found for requested date")

    games = []
    for g in games_final:
        away = g["teams"]["away"]; home = g["teams"]["home"]
        away_name = away["team"]["name"]; home_name = home["team"]["name"]
        games.append({
            "gamePk": g["gamePk"],
            "away_name": away_name,
            "home_name": home_name,
            "away_abbr": TEAM_ABBR.get(away_name, away_name[:3].upper()),
            "home_abbr": TEAM_ABBR.get(home_name, home_name[:3].upper()),
            "away_score": away.get("score", 0),
            "home_score": home.get("score", 0),
        })

    make_intro(outdir / "intro.png", args.date, len(games))
    make_end(outdir / "end.png")
    still_to_video(outdir / "intro.png", segdir / "000_intro.mp4", 2.2)

    manifest = []
    missing = []
    for idx, game in enumerate(games, 1):
        print(f"\n=== {idx}/{len(games)} {game['away_abbr']} @ {game['home_abbr']} gamePk={game['gamePk']} ===")
        content = get_json(f"{API}/game/{game['gamePk']}/content")
        item, pb = choose_highlight(content)
        if not item or not pb:
            missing.append(game)
            print("No official playback found; skipping rather than substituting a card.")
            continue
        url = pb["url"]
        raw = rawdir / f"{idx:02d}_{game['gamePk']}.mp4"
        try:
            download_media(url, raw)
        except Exception as e:
            print("Playback download failed:", e)
            missing.append(game)
            continue
        overlay = outdir / f"overlay_{idx:02d}.png"
        overlay_png(overlay, game, item.get("title"), idx, len(games))
        seg = segdir / f"{idx:03d}_{game['gamePk']}.mp4"
        try:
            transform_clip(raw, overlay, seg, 5.0)
        except Exception as e:
            print("Clip transform failed:", e)
            missing.append(game)
            continue
        manifest.append({
            **game,
            "title": item.get("title"),
            "playback": url,
            "playback_name": pb.get("name"),
            "segment": str(seg),
        })

    if not manifest:
        raise RuntimeError("No official MLB playback clips could be downloaded")

    still_to_video(outdir / "end.png", segdir / "999_end.mp4", 2.2)
    segs = [segdir / "000_intro.mp4"] + [Path(m["segment"]) for m in manifest] + [segdir / "999_end.mp4"]
    concat = outdir / "concat.txt"
    concat.write_text("".join(f"file '{p.resolve()}'\n" for p in segs), encoding="utf-8")
    final = outdir / f"SFANDOM_MLB_{args.date}_OFFICIAL_HIGHLIGHTS_9x16.mp4"
    run(["ffmpeg", "-y", "-loglevel", "warning", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(final)])

    # actual-game-frame thumbnail, after intro
    thumb = outdir / f"SFANDOM_MLB_{args.date}_thumbnail.jpg"
    run(["ffmpeg", "-y", "-loglevel", "warning", "-ss", "3.4", "-i", str(final), "-frames:v", "1", "-q:v", "2", str(thumb)])

    caption = (
        "오늘 종료된 MLB 전체 경기의 공식 하이라이트를 한 편으로 정리했습니다.\n"
        "결정적인 장면만 빠르게 확인해보세요.\n\n"
        "EN: Today’s MLB — only the moments that mattered.\n\n"
        "#MLB #메이저리그 #MLBHighlights #야구하이라이트 #Baseball #SFANDOM #오늘의MLB\n"
    )
    (outdir / f"SFANDOM_MLB_{args.date}_caption.txt").write_text(caption, encoding="utf-8")
    (outdir / "manifest.json").write_text(json.dumps({"date": args.date, "final_games": len(games), "clips_built": len(manifest), "missing": missing, "clips": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"FINAL={final}")
    print(f"FINAL_GAMES={len(games)} CLIPS_BUILT={len(manifest)} MISSING={len(missing)}")
    if missing:
        print("WARNING: Some Final games had no downloadable official playback. They were NOT replaced with cards.")

if __name__ == "__main__":
    main()
