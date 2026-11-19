#!/usr/bin/env python3
"""MLB·NBA·WK리그 공식 팀 로고를 한 번 받아 저장소에 보관합니다 (사이트는 외부 핫링크 없이 자체 파일만 사용).

    python3 src/tools/fetch_logos.py          # 없는 것만 받기
    python3 src/tools/fetch_logos.py --force  # 전부 다시 받기

저장 위치: assets/teams/mlb/<약자>.svg, assets/teams/nba/<약자>.svg
GitHub Actions(site-build.yml)가 빌드 전에 자동 실행합니다.
"""
import pathlib
import hashlib
import json
import xml.etree.ElementTree as ET
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]

MLB = {'ARI': 109, 'ATL': 144, 'BAL': 110, 'BOS': 111, 'CHC': 112, 'CWS': 145, 'CIN': 113, 'CLE': 114, 'COL': 115,
       'DET': 116, 'HOU': 117, 'KC': 118, 'LAA': 108, 'LAD': 119, 'MIA': 146, 'MIL': 158, 'MIN': 142, 'NYM': 121,
       'NYY': 147, 'ATH': 133, 'PHI': 143, 'PIT': 134, 'SD': 135, 'SF': 137, 'SEA': 136, 'STL': 138, 'TB': 139,
       'TEX': 140, 'TOR': 141, 'WSH': 120}
NBA = {'ATL': 37, 'BOS': 38, 'CLE': 39, 'NOP': 40, 'CHI': 41, 'DAL': 42, 'DEN': 43, 'GSW': 44, 'HOU': 45, 'LAC': 46,
       'LAL': 47, 'MIA': 48, 'MIL': 49, 'MIN': 50, 'BKN': 51, 'NYK': 52, 'ORL': 53, 'IND': 54, 'PHI': 55, 'PHX': 56,
       'POR': 57, 'SAC': 58, 'SAS': 59, 'OKC': 60, 'TOR': 61, 'UTA': 62, 'MEM': 63, 'WAS': 64, 'DET': 65, 'CHA': 66}

SOURCES = {
    # 다크 배경용 캡 로고
    'mlb': (MLB, 'https://www.mlbstatic.com/team-logos/team-cap-on-dark/{id}.svg'),
    'nba': (NBA, 'https://cdn.nba.com/logos/nba/16106127{id:02d}/primary/L/logo.svg'),
}



# WK리그 공식 연맹 엠블럼: 원본을 로컬에만 저장하고 두 팀 모두 확보한 뒤 연결한다.
WK_CRESTS = {
    'gyeongju-hanswon': ('경주 한수원', '경주한수원WFC', 'GYEONGJU KHNP'),
    'suwon-fc': ('수원FC 위민', '수원FC위민', 'SUWON FC WOMEN'),
}


def wk_svg_valid(data):
    if len(data) <= 200:
        return False
    try:
        root = ET.fromstring(data)
        return root.tag in ('svg', '{http://www.w3.org/2000/svg}svg')
    except ET.ParseError:
        return False


def fetch_wk_crests():
    out = ROOT / 'assets' / 'teams' / 'soccer' / '2026-27' / 'wk-league'
    out.mkdir(parents=True, exist_ok=True)
    sources = {}
    aliases = {}
    for slug, names in WK_CRESTS.items():
        path = out / (slug + '.svg')
        url = 'https://www.kwff.or.kr/images/teams/' + slug + '.svg'
        try:
            data = path.read_bytes() if path.is_file() else b''
            if not wk_svg_valid(data):
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (sfandom-build)'})
                with urllib.request.urlopen(req, timeout=20) as response:
                    data = response.read()
                if not wk_svg_valid(data):
                    raise ValueError('not a valid SVG')
                path.write_bytes(data)
            sources[path.name] = {'source': url, 'sha256': hashlib.sha256(data).hexdigest()}
            for name in names:
                aliases[name] = 'wk-league/' + path.name
        except Exception as e:
            print(f'  WK League {slug}: {e}', file=sys.stderr)
    if len(sources) != len(WK_CRESTS):
        print('WK League: both official crests not yet available; mappings unchanged', file=sys.stderr)
        return
    manifest = out / 'sources.json'
    manifest.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    mapping = ROOT / 'src' / 'content' / 'soccer_logos.json'
    original = json.loads(mapping.read_text(encoding='utf-8'))
    if any(original.get(name) != rel for name, rel in aliases.items()):
        original.update(aliases)
        mapping.write_text(json.dumps(original, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('WK League: both official crests saved and mapped')


def main():
    force = '--force' in sys.argv
    fails = 0
    for league, (teams, pattern) in SOURCES.items():
        out = ROOT / 'assets' / 'teams' / league
        out.mkdir(parents=True, exist_ok=True)
        got = 0
        for abbr, tid in teams.items():
            f = out / f'{abbr.lower()}.svg'
            if f.exists() and not force and f.stat().st_size > 200:
                continue
            try:
                req = urllib.request.Request(pattern.format(id=tid), headers={'User-Agent': 'Mozilla/5.0 (sfandom-build)'})
                with urllib.request.urlopen(req, timeout=20) as r:
                    data = r.read()
                if b'<svg' not in data[:2000]:
                    raise ValueError('not an svg')
                f.write_bytes(data)
                got += 1
            except Exception as e:  # 실패해도 빌드는 계속 (색 막대로 대체 표시)
                fails += 1
                print(f'  {league} {abbr}: {e}', file=sys.stderr)
        print(f'{league}: {got} downloaded')
    fetch_wk_crests()
    return 0


if __name__ == '__main__':
    sys.exit(main())
