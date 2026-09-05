#!/usr/bin/env python3
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import mlb_official_highlight_builder as b

DATE = '2026-09-04'
OUT = Path('parallel_output')
SEG = OUT / 'segments'
OUT.mkdir(exist_ok=True)
SEG.mkdir(exist_ok=True)

schedule = b.get_json(f'{b.API}/schedule?sportId=1&date={DATE}')
games_raw = [g for d in schedule.get('dates', []) for g in d.get('games', [])]
finals = [g for g in games_raw if (g.get('status') or {}).get('abstractGameState') == 'Final']
if not finals:
    raise RuntimeError('No Final MLB games')

records = []
for idx, g in enumerate(finals, 1):
    away = g['teams']['away']; home = g['teams']['home']
    away_name = away['team']['name']; home_name = home['team']['name']
    game = {
        'gamePk': g['gamePk'],
        'away_name': away_name, 'home_name': home_name,
        'away_abbr': b.TEAM_ABBR.get(away_name, away_name[:3].upper()),
        'home_abbr': b.TEAM_ABBR.get(home_name, home_name[:3].upper()),
        'away_score': away.get('score', 0), 'home_score': home.get('score', 0),
    }
    content = b.get_json(f"{b.API}/game/{g['gamePk']}/content")
    item, pb = b.choose_highlight(content)
    if not item or not pb:
        print(f"NO PLAYBACK {game['away_abbr']}@{game['home_abbr']}")
        continue
    overlay = OUT / f'overlay_{idx:02d}.png'
    b.overlay_png(overlay, game, item.get('title'), idx, len(finals))
    records.append({**game, 'index': idx, 'title': item.get('title'), 'url': pb['url'], 'overlay': str(overlay), 'segment': str(SEG / f'{idx:03d}_{g["gamePk"]}.mp4')})

if len(records) != len(finals):
    raise RuntimeError(f'Expected official playback for all {len(finals)} Final games; got {len(records)}. Refusing card substitution.')

b.make_intro(OUT / 'intro.png', DATE, len(records))
b.make_end(OUT / 'end.png')
b.still_to_video(OUT / 'intro.png', SEG / '000_intro.mp4', 2.2)
b.still_to_video(OUT / 'end.png', SEG / '999_end.mp4', 2.2)


def render(r):
    url = r['url']; overlay = r['overlay']; out = r['segment']
    filt = (
        '[0:v]split=2[bg][fg];'
        '[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg2];'
        '[fg]scale=1080:-2:force_original_aspect_ratio=decrease[fg2];'
        '[bg2][fg2]overlay=(W-w)/2:(H-h)/2[base];'
        '[base][1:v]overlay=0:0,fps=30,format=yuv420p[outv]'
    )
    cmd = [
        'ffmpeg','-y','-loglevel','warning','-rw_timeout','15000000','-t','5.0','-i',url,
        '-loop','1','-t','5.0','-i',overlay,
        '-filter_complex',filt,'-map','[outv]','-map','0:a:0',
        '-c:v','libx264','-preset','veryfast','-crf','22','-threads','2',
        '-c:a','aac','-ar','48000','-ac','2','-b:a','128k','-shortest','-movflags','+faststart',out
    ]
    b.run(cmd)
    return out

with ThreadPoolExecutor(max_workers=4) as ex:
    futs = {ex.submit(render, r): r for r in records}
    for fut in as_completed(futs):
        r = futs[fut]
        try:
            print('DONE', r['index'], r['away_abbr'], r['home_abbr'], fut.result())
        except Exception as e:
            raise RuntimeError(f"Render failed for {r['away_abbr']}@{r['home_abbr']}: {e}") from e

segments = [SEG/'000_intro.mp4'] + [Path(r['segment']) for r in sorted(records, key=lambda x:x['index'])] + [SEG/'999_end.mp4']
concat = OUT/'concat.txt'
concat.write_text(''.join(f"file '{p.resolve()}'\n" for p in segments), encoding='utf-8')
final = OUT/f'SFANDOM_MLB_{DATE}_OFFICIAL_16GAME_HIGHLIGHTS_9x16.mp4'
b.run(['ffmpeg','-y','-loglevel','warning','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(final)])
thumb = OUT/f'SFANDOM_MLB_{DATE}_thumbnail.jpg'
b.run(['ffmpeg','-y','-loglevel','warning','-ss','3.4','-i',str(final),'-frames:v','1','-q:v','2',str(thumb)])
caption = '오늘 종료된 MLB 16경기, 공식 경기영상의 결정적 순간만 한 편으로 정리했습니다.\n\nToday’s MLB. Only the moments that mattered.\n\n#MLB #메이저리그 #MLBHighlights #야구하이라이트 #Baseball #SFANDOM #오늘의MLB\n'
(OUT/f'SFANDOM_MLB_{DATE}_caption.txt').write_text(caption, encoding='utf-8')
(OUT/'manifest.json').write_text(json.dumps({'date':DATE,'finalGames':len(finals),'clips':records}, ensure_ascii=False, indent=2), encoding='utf-8')
print('FINAL', final)
