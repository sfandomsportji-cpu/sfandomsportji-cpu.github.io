#!/usr/bin/env python3
"""KBO·NPB 자동 수집용 자료원 점검 (일회성). robots.txt가 허용하는 주소만 받아 src/probe/ 에 견본을 저장합니다.
견본을 보고 수집기(sync_kbo_npb.py)를 만듭니다. 사이트 빌드에는 쓰이지 않습니다."""
import pathlib, urllib.request, urllib.robotparser, urllib.parse, datetime as dt

OUT = pathlib.Path(__file__).resolve().parents[1] / "probe"
UA = "SFANDOM-site-scoreboard/1.0 (https://sfandom.com/)"
TARGETS = {
    "kbo-schedule": "https://www.koreabaseball.com/Schedule/Schedule.aspx",
    "kbo-scoreboard": "https://www.koreabaseball.com/Schedule/ScoreBoard.aspx",
    "kbo-postseason": "https://www.koreabaseball.com/Schedule/Schedule.aspx?seriesId=3,4,5,7",
    "npb-top": "https://npb.jp/",
    "npb-games": "https://npb.jp/games/2026/",
    "npb-cs": "https://npb.jp/bis/2026/stats/",
    "npb-scores-today": "https://npb.jp/scores/",
}
OUT.mkdir(exist_ok=True)
report = [f"probe {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC"]
robots = {}
for name, url in TARGETS.items():
    host = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(url))
    if host not in robots:
        rp = urllib.robotparser.RobotFileParser(host + "/robots.txt")
        try:
            rp.read()
        except Exception as exc:
            rp = None
            report.append(f"{host}: robots.txt 읽기 실패 {exc!r} → 받지 않음")
        robots[host] = rp
    rp = robots[host]
    if rp is None or not rp.can_fetch(UA, url):
        report.append(f"{name}: robots.txt 불허 또는 확인 불가 → 받지 않음 ({url})")
        continue
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(400_000)
            (OUT / f"{name}.html").write_bytes(body)
            report.append(f"{name}: HTTP {r.status} {len(body)} bytes")
    except Exception as exc:
        report.append(f"{name}: 실패 {exc!r}")
(OUT / "report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
print("\n".join(report))
