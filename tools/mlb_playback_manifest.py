#!/usr/bin/env python3
import json, re, requests
from pathlib import Path

API='https://statsapi.mlb.com/api/v1'
DATE='2026-09-04'
s=requests.Session(); s.headers.update({'User-Agent':'SFANDOM-Manifest/1.0'})

BAD=['interview','exclusive angle','statcast','data visualization','radio call','all calls','curtain call','field view','press conference','postgame']
GOOD={'walk-off':120,'walk off':120,'grand slam':100,'go-ahead':90,'go ahead':90,'home run':80,'homer':80,'three-run':70,'two-run':65,'rbi':55,'double':45,'triple':45,'single':35,'final out':60,'strikeout':30}

def get(url):
    r=s.get(url,timeout=25); r.raise_for_status(); return r.json()

def norm(x): return re.sub(r'\s+',' ',(x or '').strip().lower().replace('’',"'"))
def tags(item): return norm(' | '.join(str(k.get('displayName') or k.get('value') or k.get('name') or '') for k in (item.get('keywordsAll') or [])))
def score(item):
    h=norm(item.get('title'))+' | '+tags(item)
    if any(x in h for x in BAD): return -9999
    v=80 if ('in-game highlight' in h or 'in game highlight' in h) else 0
    if 'condensed game' in h or 'game summary' in h: v-=60
    for k,p in GOOD.items():
        if k in h: v+=p
    if item.get('playbacks'): v+=50
    return v

def pbq(p):
    u=p.get('url') or ''; mp4=1 if '.mp4' in u.lower() else 0
    w=int(p.get('width') or 0); h=int(p.get('height') or 0)
    m=re.search(r'(\d{3,4})x(\d{3,4})',u)
    if m and not (w and h): w,h=map(int,m.groups())
    return (mp4,w*h,w,h)

sched=get(f'{API}/schedule?sportId=1&date={DATE}')
games=[g for d in sched.get('dates',[]) for g in d.get('games',[]) if (g.get('status') or {}).get('abstractGameState')=='Final']
out=[]
for g in games:
    content=get(f"{API}/game/{g['gamePk']}/content")
    items=(((content.get('highlights') or {}).get('highlights') or {}).get('items') or [])
    chosen=None
    for item in sorted(items,key=score,reverse=True):
        if score(item)<0: continue
        pbs=[p for p in (item.get('playbacks') or []) if p.get('url')]
        if not pbs: continue
        pbs.sort(key=pbq,reverse=True)
        chosen=(item,pbs[0]); break
    away=g['teams']['away']; home=g['teams']['home']
    rec={'gamePk':g['gamePk'],'away':away['team']['name'],'home':home['team']['name'],'awayScore':away.get('score'),'homeScore':home.get('score')}
    if chosen:
        item,pb=chosen
        rec.update({'title':item.get('title'),'url':pb.get('url'),'playbackName':pb.get('name'),'width':pb.get('width'),'height':pb.get('height')})
    else:
        rec.update({'title':None,'url':None})
    out.append(rec)
Path('playback_manifest.json').write_text(json.dumps({'date':DATE,'finalGames':len(games),'games':out},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'date':DATE,'finalGames':len(games),'withPlayback':sum(1 for x in out if x.get('url'))},ensure_ascii=False))
