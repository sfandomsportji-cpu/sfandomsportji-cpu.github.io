#!/usr/bin/env python3
"""분석 기록 집계 → src/content/track-record.json

비공개 저장소(sfandom-analysis)의 results.csv에서 '분석 방향을 남긴 끝난 경기'만 세어
종목별·월별 승/패 숫자만 사이트 저장소에 남긴다. 경기별 원본은 사이트에 올리지 않는다.

    python3 src/tools/track_record.py /path/to/sfandom-analysis/results.csv

- 포함: 적중여부가 '적중' 또는 '빗나감'인 줄 (분석 방향이 '없음'이거나 아직 결과가 없는 줄은 제외)
- 화면 표기는 '분석 성공/빗나감'(승/패)으로 바꾼다. CSV의 '적중' 단어는 사이트에 노출하지 않는다.
- 종목 구분이 없는 이전 누적(날짜가 '~'로 시작하는 줄)은 세지 않는다. 합계는 site.json의 analysis_record_base가 맡는다.
"""
import csv, json, pathlib, sys
from collections import OrderedDict

OUT = pathlib.Path(__file__).resolve().parents[1] / 'content' / 'track-record.json'
ORDER = ['축구', '농구', '야구', '배구']  # 화면에 보이는 종목 순서(없는 종목은 건너뜀)
OK, MISS = '적중', '빗나감'


def main(csv_path):
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8-sig')))
    use = [r for r in rows if r['적중여부'].strip() in (OK, MISS) and not r['날짜'].startswith('~')]
    if not use:
        raise SystemExit('집계할 줄이 없어요 (적중여부가 채워진 줄 0개)')
    sport, month = {}, {}
    for r in use:
        ok = r['적중여부'].strip() == OK
        for bucket, key in ((sport, r['종목'].strip()), (month, r['날짜'][:7])):
            b = bucket.setdefault(key, {'ok': 0, 'miss': 0})
            b['ok' if ok else 'miss'] += 1
    keys = [k for k in ORDER if k in sport] + sorted(k for k in sport if k not in ORDER)
    data = OrderedDict([
        ('since', min(r['날짜'] for r in use)),
        ('updated', max(r['날짜'] for r in use)),
        ('total', {'ok': sum(v['ok'] for v in sport.values()), 'miss': sum(v['miss'] for v in sport.values())}),
        ('by_sport', OrderedDict((k, sport[k]) for k in keys)),
        ('by_month', OrderedDict((k, month[k]) for k in sorted(month))),
    ])
    assert data['total']['ok'] + data['total']['miss'] == len(use)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'집계 {len(use)}경기 → {OUT.name}: {dict(data["total"])}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '../sfandom-analysis/results.csv')
