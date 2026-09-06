import json, os, re, subprocess, sys, textwrap, time
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont

DATE_US = "2026-09-05"
DATE_KST = "SEP 06 · KST"
OUTDIR = Path("mlb_20260906_output")
RAW = OUTDIR / "raw"
SEG = OUTDIR / "segments"
CARDS = OUTDIR / "cards"
for p in (OUTDIR, RAW, SEG, CARDS):
    p.mkdir(parents=True, exist_ok=True)

TARGETS = [
    {
        "pair": {"Detroit Tigers", "Cleveland Guardians"},
        "player": "Riley Greene", "keywords": ["riley greene", "homer"],
        "ko": "그린, 오늘 두 번째 대포.", "en": "GREENE GOES DEEP AGAIN."
    },
    {
        "pair": {"Tampa Bay Rays", "Texas Rangers"},
        "player": "Jonathan Aranda", "keywords": ["jonathan aranda", "homer"],
        "ko": "연장 10회, 아란다의 3점포.", "en": "ARANDA BREAKS IT OPEN IN THE 10TH."
    },
    {
        "pair": {"San Francisco Giants", "New York Mets"},
        "player": "Rafael Devers", "keywords": ["rafael devers", "homer"],
        "ko": "디버스, 멀티홈런 폭발.", "en": "DEVERS. TWO-HOMER DAY."
    },
    {
        "pair": {"Arizona Diamondbacks", "Houston Astros"},
        "player": "Ketel Marte", "keywords": ["ketel marte", "home run"],
        "ko": "8회 동점. 마르테의 한 방.", "en": "MARTE TIES IT IN THE 8TH."
    },
    {
        "pair": {"Washington Nationals", "Los Angeles Dodgers"},
        "player": "Tommy Edman", "keywords": ["tommy edman", "home run"],
        "ko": "7회 역전 3점포.", "en": "EDMAN FLIPS IT WITH THREE."
    },
    {
        "pair": {"Atlanta Braves", "Philadelphia Phillies"},
        "player": "Kyle Schwarber", "keywords": ["kyle schwarber", "homer"],
        "ko": "슈와버 41호, 435FT.", "en": "SCHWARBER: NO. 41."
    },
    {
        "pair": {"Minnesota Twins", "Chicago White Sox"},
        "player": "Munetaka Murakami", "keywords": ["munetaka murakami", "homer"],
        "ko": "무라카미, 시즌 30호.", "en": "MURAKAMI REACHES 30."
    },
]

session = requests.Session()
session.headers.update({"User-Agent": "SFANDOM-highlight-builder/1.0"})

def run(cmd, check=True):
    print("+", " ".join(map(str, cmd)), flush=True)
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def ffprobe(path):
    p = run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,codec_type,width,height,sample_rate,channels,bit_rate","-of","json",str(path)])
    return json.loads(p.stdout)

def has_audio(path):
    info = ffprobe(path)
    return any(s.get("codec_type") == "audio" for s in info.get("streams", []))

def audio_non_silent(path):
    p = subprocess.run(["ffmpeg","-hide_banner","-i",str(path),"-af","volumedetect","-f","null","-"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    m = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", p.stderr)
    if not m:
        return False, None
    v = float(m.group(1))
    return v > -70.0, v

def get_json(url):
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def download(url, dest):
    print("DOWNLOAD", url, "->", dest, flush=True)
    with session.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk: f.write(chunk)
    return dest

def choose_playback(item):
    plays = item.get("playbacks") or []
    candidates=[]
    for p in plays:
        url=p.get("url") or ""
        if not url: continue
        name=(p.get("name") or "").lower()
        width=int(p.get("width") or 0); height=int(p.get("height") or 0)
        is_mp4 = ".mp4" in url.lower() or "mp4" in name
        is_hls = ".m3u8" in url.lower() or "hls" in name
        if is_mp4 or is_hls:
            candidates.append((1 if is_mp4 else 0, width*height, width, height, url, p))
    if not candidates:
        raise RuntimeError(f"No usable playback in item {item.get('title')}")
    candidates.sort(reverse=True)
    return candidates[0][4], candidates[0][5]

def item_text(item):
    return " ".join(str(item.get(k) or "") for k in ("title","description","blurb","headline")).lower()

def score_item(item, target):
    txt=item_text(item)
    score=0
    player=target["player"].lower()
    if player in txt: score += 100
    surname=player.split()[-1]
    if surname in txt: score += 25
    for kw in target["keywords"]:
        if kw in txt: score += 20
    if "home run" in txt or "homer" in txt: score += 10
    if "go-ahead" in txt or "game-tying" in txt or "walk-off" in txt: score += 5
    return score

def find_target_game(schedule_games, pair):
    matches=[]
    for g in schedule_games:
        away=g["teams"]["away"]["team"]["name"]
        home=g["teams"]["home"]["team"]["name"]
        if {away,home} == pair:
            matches.append(g)
    if not matches:
        raise RuntimeError(f"Game not found for {pair}")
    finals=[g for g in matches if g.get("status",{}).get("abstractGameState") == "Final" or "Final" in g.get("status",{}).get("detailedState","")]
    return finals[0] if finals else matches[0]

def format_score(g):
    away=g["teams"]["away"]["team"]["name"]
    home=g["teams"]["home"]["team"]["name"]
    ascore=g["teams"]["away"].get("score",0); hscore=g["teams"]["home"].get("score",0)
    return away, home, ascore, hscore

def get_font(size, bold=False):
    cands = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in cands:
        if os.path.exists(c): return ImageFont.truetype(c,size)
    return ImageFont.load_default()

def fit_font(draw, text, maxw, maxsize, minsize=22, bold=True):
    for s in range(maxsize,minsize-1,-1):
        f=get_font(s,bold)
        if draw.textlength(text,font=f) <= maxw: return f
    return get_font(minsize,bold)

def make_card(idx, target, game, title):
    W,H=1080,1920
    img=Image.new("RGB",(W,H),(4,6,10)); d=ImageDraw.Draw(img)
    red=(228,42,48); white=(248,248,248); gray=(175,180,188)
    d.rectangle((0,0,W,14),fill=red)
    d.text((58,70),"SFANDOM  |  MLB",font=get_font(42,True),fill=white)
    d.text((850,82),f"{idx:02d}/07",font=get_font(25,True),fill=red)
    d.text((58,145),DATE_KST,font=get_font(24,False),fill=gray)
    d.text((58,225),target["ko"],font=fit_font(d,target["ko"],964,45,30,True),fill=white)
    d.text((58,290),target["en"],font=fit_font(d,target["en"],964,30,20,True),fill=red)
    away,home,ascore,hscore=format_score(game)
    matchup=f"{away}  {ascore}  —  {hscore}  {home}"
    d.rectangle((58,410,1022,412),fill=(230,230,230))
    d.rectangle((58,412,290,417),fill=red)
    d.text((58,452),matchup,font=fit_font(d,matchup,964,28,19,False),fill=white)
    # 16:9 game window is left empty/black; actual footage overlays here
    d.rectangle((0,600,W,1208),fill=(0,0,0))
    d.rounded_rectangle((36,1305,1044,1515),radius=8,fill=(7,10,14),outline=(30,34,40),width=2)
    d.text((60,1365),"OFFICIAL MLB GAME FOOTAGE",font=get_font(27,False),fill=white)
    d.text((60,1412),"SOURCE · MLB FILM ROOM",font=get_font(24,True),fill=red)
    d.text((60,1595),"오늘의 MLB, 결정적 순간만.",font=get_font(31,True),fill=white)
    d.text((60,1648),"Today’s MLB. Only the moments that mattered.",font=get_font(23,False),fill=gray)
    p=CARDS/f"card_{idx:02d}.png"; img.save(p); return p

# Fetch schedule
sched=get_json(f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={DATE_US}")
games=[]
for d in sched.get("dates",[]): games.extend(d.get("games",[]))
if not games: raise RuntimeError("No games returned")

manifest=[]
for idx,target in enumerate(TARGETS,1):
    game=find_target_game(games,target["pair"])
    gamepk=game["gamePk"]
    content=get_json(f"https://statsapi.mlb.com/api/v1/game/{gamepk}/content")
    items=((content.get("highlights") or {}).get("highlights") or {}).get("items") or []
    if not items:
        # some games use highlights.live.items or media.epg
        items=((content.get("highlights") or {}).get("live") or {}).get("items") or []
    if not items: raise RuntimeError(f"No highlight items for gamePk {gamepk}")
    scored=sorted([(score_item(it,target),it) for it in items], key=lambda x:x[0], reverse=True)
    score,best=scored[0]
    if score < 60:
        print("TOP TITLES", [(s,it.get("title")) for s,it in scored[:10]], flush=True)
        raise RuntimeError(f"Could not confidently match {target['player']} in gamePk {gamepk}; best={best.get('title')}")
    url,pb=choose_playback(best)
    ext=".mp4" if ".mp4" in url.lower() or "mp4" in (pb.get("name") or "").lower() else ".m3u8"
    raw=RAW/f"{idx:02d}_{re.sub('[^A-Za-z0-9_-]+','_',target['player'])}.mp4"
    if ext == ".mp4":
        download(url, raw)
    else:
        run(["ffmpeg","-y","-i",url,"-c","copy",str(raw)])
    info=ffprobe(raw)
    dur=float(info.get("format",{}).get("duration") or 0)
    if dur < 5.2: raise RuntimeError(f"Source too short for {target['player']}: {dur}")
    if not has_audio(raw): raise RuntimeError(f"NO ORIGINAL AUDIO for {target['player']}")
    ok,mean=audio_non_silent(raw)
    if not ok: raise RuntimeError(f"SILENT ORIGINAL AUDIO for {target['player']}, mean={mean}")
    # Start near the action while preserving pitch/contact + immediate result. Most MLB highlight clips open with a short lead-in.
    start=max(1.0, min(5.0, dur*0.16))
    if start+5.0 > dur: start=max(0,dur-5.05)
    card=make_card(idx,target,game,best.get("title") or "")
    seg=SEG/f"seg_{idx:02d}.mp4"
    vf=f"[0:v]trim=start={start}:duration=5,setpts=PTS-STARTPTS,scale=1080:608:force_original_aspect_ratio=decrease,pad=1080:608:(ow-iw)/2:(oh-ih)/2:black[vclip];[1:v][vclip]overlay=0:600:shortest=1[vout]"
    af=f"[0:a]atrim=start={start}:duration=5,asetpts=PTS-STARTPTS,aresample=48000[aout]"
    run(["ffmpeg","-y","-i",str(raw),"-loop","1","-t","5","-i",str(card),"-filter_complex",vf+";"+af,"-map","[vout]","-map","[aout]","-r","30","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-ar","48000","-ac","2","-t","5","-movflags","+faststart",str(seg)])
    if not has_audio(seg): raise RuntimeError(f"Segment lost audio: {target['player']}")
    sok,smean=audio_non_silent(seg)
    if not sok: raise RuntimeError(f"Segment audio silent: {target['player']} mean={smean}")
    away,home,ascore,hscore=format_score(game)
    manifest.append({
        "index":idx,"gamePk":gamepk,"away":away,"home":home,"awayScore":ascore,"homeScore":hscore,
        "player":target["player"],"highlightTitle":best.get("title"),"playback":url,"sourceDuration":dur,
        "cutStart":start,"cutDuration":5.0,"rawMeanVolumeDb":mean,"segmentMeanVolumeDb":smean
    })

# concat 7 segments
concat=OUTDIR/"concat.txt"
concat.write_text("".join(f"file '{(p.resolve())}'\n" for p in sorted(SEG.glob('seg_*.mp4'))),encoding="utf-8")
final=OUTDIR/"SFANDOM_MLB_2026-09-06_7GAMES_FINAL_1080x1920.mp4"
run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-ar","48000","-ac","2","-movflags","+faststart",str(final)])

# final QA
fi=ffprobe(final)
duration=float(fi.get("format",{}).get("duration") or 0)
streams=fi.get("streams",[])
v=next((s for s in streams if s.get("codec_type")=="video"),{})
a=next((s for s in streams if s.get("codec_type")=="audio"),{})
if v.get("width") != 1080 or v.get("height") != 1920: raise RuntimeError(f"Wrong dimensions {v}")
if a.get("codec_name") != "aac" or str(a.get("sample_rate")) != "48000": raise RuntimeError(f"Wrong audio {a}")
if not (34.8 <= duration <= 35.3): raise RuntimeError(f"Wrong duration {duration}")
fok,fmean=audio_non_silent(final)
if not fok: raise RuntimeError(f"Final audio silent mean={fmean}")

# thumbnail from actual first game footage
thumb=OUTDIR/"SFANDOM_MLB_2026-09-06_7GAMES_thumbnail.jpg"
run(["ffmpeg","-y","-ss","2.2","-i",str(final),"-frames:v","1","-q:v","2",str(thumb)])

caption="""오늘의 MLB, 35초로 끝. ⚾\n어제 경기에서 딱 7장면만 골랐습니다. 홈런, 동점포, 역전포—결정적 순간만.\n\nToday’s MLB in 35 seconds. Seven games. Seven moments.\n\n#MLB #메이저리그 #MLBHighlights #Baseball #야구하이라이트 #SFANDOM\n"""
(OUTDIR/"caption.txt").write_text(caption,encoding="utf-8")
(OUTDIR/"source_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
(OUTDIR/"QA.txt").write_text(json.dumps({"duration":duration,"video":v,"audio":a,"finalMeanVolumeDb":fmean},ensure_ascii=False,indent=2),encoding="utf-8")
print("FINAL",final)
print("MEAN_VOLUME_DB",fmean)
print("DONE")