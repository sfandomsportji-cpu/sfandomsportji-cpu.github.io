#!/usr/bin/env python3
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mlb_official_highlight_builder as b

DATE = '2026-09-04'
PINNED = Path('tools/mlb_2026-09-04_playbacks.json')
OUT = Path('pinned_output')
SEG = OUT / 'segments'
OUT.mkdir(exist_ok=True)
SEG.mkdir(exist_ok=True)

payload = json.loads(PINNED.read_text(encoding='utf-8'))
records = payload['games']
if payload.get('finalGames') != 16 or len(records) != 16:
    raise RuntimeError(f'Expected exactly 16 pinned official MLB playbacks, got {len(records)}')
if any(not r.get('url') for r in records):
    raise RuntimeError('Pinned manifest contains a missing playback URL; refusing substitution.')

# Adapt pinned fields to the overlay helper.
for r in records:
    game = {
        'away_abbr': r['awayAbbr'], 'home_abbr': r['homeAbbr'],
        'away_score': r['awayScore'], 'home_score': r['homeScore'],
    }
    overlay = OUT / f"overlay_{r['index']:02d}.png"
    b.overlay_png(overlay, game, r['title'], r['index'], len(records))
    r['overlay'] = str(overlay)
    r['segment'] = str(SEG / f"{r['index']:03d}_{r['gamePk']}.mp4")

b.make_intro(OUT / 'intro.png', DATE, len(records))
b.make_end(OUT / 'end.png')
b.still_to_video(OUT / 'intro.png', SEG / '000_intro.mp4', 2.2)
b.still_to_video(OUT / 'end.png', SEG / '999_end.mp4', 2.2)


def render(r):
    filt = (
        '[0:v]split=2[bg][fg];'
        '[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=18:9[bg2];'
        '[fg]scale=1080:-2:force_original_aspect_ratio=decrease[fg2];'
        '[bg2][fg2]overlay=(W-w)/2:(H-h)/2[base];'
        '[base][1:v]overlay=0:0,fps=30,format=yuv420p[outv]'
    )
    cmd = [
        'ffmpeg','-y','-loglevel','warning','-rw_timeout','20000000',
        '-t','6.0','-i',r['url'],
        '-loop','1','-t','6.0','-i',r['overlay'],
        '-filter_complex',filt,
        '-map','[outv]','-map','0:a:0',
        '-c:v','libx264','-preset','veryfast','-crf','21','-threads','2',
        '-c:a','aac','-ar','48000','-ac','2','-b:a','128k',
        '-shortest','-movflags','+faststart',r['segment']
    ]
    b.run(cmd)
    return r['segment']

# Four concurrent official streams keeps the job fast without hammering MLB media hosts.
with ThreadPoolExecutor(max_workers=4) as ex:
    futures = {ex.submit(render, r): r for r in records}
    for f in as_completed(futures):
        r = futures[f]
        try:
            print('DONE', r['index'], r['awayAbbr'], r['homeAbbr'], f.result(), flush=True)
        except Exception as exc:
            raise RuntimeError(f"Official playback render failed for {r['awayAbbr']}@{r['homeAbbr']}: {exc}") from exc

segments = [SEG / '000_intro.mp4'] + [Path(r['segment']) for r in sorted(records, key=lambda x: x['index'])] + [SEG / '999_end.mp4']
concat = OUT / 'concat.txt'
concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in segments), encoding='utf-8')
final = OUT / f'SFANDOM_MLB_{DATE}_OFFICIAL_16GAME_HIGHLIGHTS_9x16.mp4'
# Re-encode final concat to guarantee a single clean H.264/AAC stream across all segments.
b.run([
    'ffmpeg','-y','-loglevel','warning','-f','concat','-safe','0','-i',str(concat),
    '-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-r','30',
    '-c:a','aac','-ar','48000','-ac','2','-b:a','128k','-movflags','+faststart',str(final)
])

thumb = OUT / f'SFANDOM_MLB_{DATE}_thumbnail.jpg'
# 4.5s lands inside game 1, so the thumbnail is based on an actual MLB game frame.
b.run(['ffmpeg','-y','-loglevel','warning','-ss','4.5','-i',str(final),'-frames:v','1','-q:v','2',str(thumb)])

caption = (
    '오늘 종료된 MLB 16경기, 공식 경기영상의 결정적 순간만 한 편으로 정리했습니다.\n'
    '전체 경기 최종 스코어와 핵심 장면을 빠르게 확인해보세요.\n\n'
    'Today’s MLB. Only the moments that mattered.\n\n'
    '#MLB #메이저리그 #MLBHighlights #야구하이라이트 #Baseball #SFANDOM #오늘의MLB\n'
)
(OUT / f'SFANDOM_MLB_{DATE}_caption.txt').write_text(caption, encoding='utf-8')
(OUT / 'manifest.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print('FINAL=', final, flush=True)
