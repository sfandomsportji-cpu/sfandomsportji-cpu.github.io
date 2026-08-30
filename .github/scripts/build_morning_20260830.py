from pathlib import Path

index_path = Path('index.html')
archive_path = Path('archive/media/index.html')
index = index_path.read_text(encoding='utf-8')
archive = archive_path.read_text(encoding='utf-8')

start_marker = '    <section id="daily-news-slot"'
end_marker = '    <section id="signature-moments"'
start = index.index(start_marker)
end = index.index(end_marker, start)
old_block = index[start:end].rstrip() + '\n'

required_archive_tokens = [
    'ARCHIVE 05 · COMPLETE',
    '37세의 100.1마일.',
    'Chourio의 4안타·2홈런.',
    'No Fireballs?',
    'Mize vs McClanahan.',
    'TAMPA BAY ML',
    '../../assets/morning-20260829/chris-sale.jpg',
    '../../assets/morning-20260829/shane-mcclanahan.jpg',
]
for token in required_archive_tokens:
    if token not in archive:
        raise SystemExit(f'Archive verification failed: {token}')

snapshot_path = Path('archive/snapshots/2026-08-29-main-fragment.html')
snapshot_path.parent.mkdir(parents=True, exist_ok=True)
if snapshot_path.exists() and snapshot_path.read_text(encoding='utf-8') != old_block:
    raise SystemExit('Existing exact snapshot differs from current main fragment')
snapshot_path.write_text(old_block, encoding='utf-8')

new_block = '''    <section id="daily-news-slot" class="section morning-edition reveal" aria-labelledby="daily-news-title">
      <header class="morning-edition-head"><div><p class="eyebrow">DAILY NEWS · 2026.08.30 KST</p><h2 id="daily-news-title">Yesterday’s Sports.<br><span>Today’s Evidence.</span></h2></div><p>발행 시점까지 공식 기록·신뢰 출처와 이미지 권리를 다시 대조해 고른 두 장면입니다.</p></header>
      <div class="morning-news-grid">
        <article class="morning-story">
          <div class="morning-story-photo"><img src="assets/morning-20260830/gwak-been.jpg" alt="Doosan Bears pitcher Gwak Been photographed in 2023" width="1200" height="1500"><span>01 · 160.3 KM/H SHOWCASE</span></div>
          <div class="morning-story-copy"><p class="morning-meta">DOOSAN 7–2 KIWOOM · 2026.08.29 KST</p><h3>160.3km, 그리고 MLB 5개 구단.<br>곽빈이 잠실을 쇼케이스로 만들었다.</h3><p>두산 곽빈은 키움전에서 6이닝 5피안타 3볼넷 8탈삼진 2실점으로 승리를 따냈고, 1회 케스턴 히우라를 상대로 개인 최고 160.3km/h를 찍었습니다. 현장에는 다저스·양키스·파드리스·블루제이스·로열스 스카우트가 모였습니다.</p><div class="morning-stats"><span><strong>6.0</strong>IP</span><span><strong>8</strong>SO</span><span><strong>2</strong>R</span><span><strong>160.3</strong>KM/H</span></div><div class="morning-read"><small>SFANDOM READ</small><p>이날의 핵심은 단순 최고 구속이 아닙니다. 가장 많은 시선이 몰린 경기에서 96구 동안 선발 역할을 지키며 구속과 결과를 동시에 증명했다는 점입니다.</p></div><p class="morning-en"><b>EN</b> Gwak Been touched a career-high 160.3 km/h and delivered six strong innings with scouts from five MLB clubs watching at Jamsil.</p><div class="morning-links"><a href="https://www.koreabaseball.com/MediaNews/News/BreakingNews/View.aspx?bdSe=62186" target="_blank" rel="noopener noreferrer">KBO OFFICIAL ↗</a><a href="https://www.koreabaseball.com/MediaNews/News/Interview/View.aspx?bdSe=62194" target="_blank" rel="noopener noreferrer">KBO INTERVIEW ↗</a></div><p class="morning-credit">PHOTO · SEOHAE1999 · CC BY-SA 3.0 · WIKIMEDIA COMMONS · GWAK BEEN · DOOSAN BEARS #47</p></div>
        </article>
        <article class="morning-story">
          <div class="morning-story-photo"><img src="assets/morning-20260830/tottenham-hotspur-stadium.jpg" alt="Tottenham Hotspur Stadium in London" width="2276" height="1280"><span>02 · PREMIER LEAGUE WARNING</span></div>
          <div class="morning-story-copy"><p class="morning-meta">TOTTENHAM 0–2 NEWCASTLE · KICKOFF 2026.08.30 01:30 KST · FT</p><h3>£300m을 썼는데 리그 골은 아직 0.<br>토트넘의 새 출발이 흔들린다.</h3><p>토트넘은 홈에서 뉴캐슬에 0–2로 패해 개막 2연패와 리그 2경기 연속 무득점을 기록했습니다. 전반의 개선된 흐름을 살리지 못한 채 후반 Anthony Elanga와 Yoane Wissa에게 연속 실점했습니다.</p><div class="morning-stats"><span><strong>0</strong>LEAGUE GOALS</span><span><strong>2</strong>LOSSES</span><span><strong>21/39</strong>HOME L</span><span><strong>£300M+</strong>SUMMER</span></div><div class="morning-read"><small>SFANDOM READ</small><p>투자 규모보다 더 큰 문제는 실점 뒤 경기 구조가 무너졌다는 점입니다. 전반 경기력의 개선만으로는 홈에서 반복되는 패배 패턴을 끊었다고 보기 어렵습니다.</p></div><p class="morning-en"><b>EN</b> Tottenham fell 2–0 at home to Newcastle, leaving Roberto De Zerbi’s side winless and scoreless through its first two league matches.</p><div class="morning-links"><a href="https://www.reuters.com/sports/soccer/spurs-second-half-collapse-shows-size-de-zerbis-task-2026-08-29/" target="_blank" rel="noopener noreferrer">REUTERS CHECK ↗</a><a href="https://www.tottenhamhotspur.com/news/1087374/spurs-vs-newcastle-how-to-watch-team-news-kit-colours-key-information" target="_blank" rel="noopener noreferrer">SPURS OFFICIAL ↗</a></div><p class="morning-credit">PHOTO · STADIUM SPOTTER · CC BY-SA 4.0 · WIKIMEDIA COMMONS · TOTTENHAM HOTSPUR STADIUM</p></div>
        </article>
      </div>
    </section>

    <section id="kairo-feature-slot" class="section kairo-feature reveal" aria-labelledby="kairo-feature-title">
      <div class="kairo-feature-photo"><img src="assets/morning-20260830/pete-crow-armstrong.jpg" alt="Chicago Cubs outfielder Pete Crow-Armstrong photographed in 2023" width="1361" height="1789"></div><div class="kairo-feature-copy"><p class="eyebrow">KAIRO FEATURE · DATA + STORY</p><h2 id="kairo-feature-title">Three Swings.<br><span>One Statement.</span></h2><p>Pete Crow-Armstrong은 신시내티전에서 개인 첫 3홈런 경기와 6타점을 기록하며 컵스의 17–5 승리를 이끌었습니다. 마지막 홈런은 시즌 36호였고, 한 경기에서 장타 생산력을 폭발시키며 MVP 레이스에 다시 강한 장면을 남겼습니다.</p><div class="kairo-feature-data"><span><strong>3</strong>HR</span><span><strong>6</strong>RBI</span><span><strong>36</strong>SEASON HR</span><span><strong>17–5</strong>SCORE</span></div><div class="morning-read"><small>KAIRO’S NOTE</small><p>한 경기 3홈런은 결과지만 더 중요한 것은 세 타석에서 서로 다른 카운트와 투구를 장타로 연결했다는 점입니다. 시즌 후반의 한 경기 폭발이 MVP 서사에 남기는 영향은 숫자 이상입니다.</p></div><a class="kairo-feature-link" href="https://www.mlb.com/video/pete-crow-armstrong-homers-36-on-a-fly-ball-to-center-field-pedro-ramirez?t=long-home-runs" target="_blank" rel="noopener noreferrer">WATCH THE THIRD HOMER · MLB.COM ↗</a><div class="morning-links"><a href="https://www.reuters.com/sports/baseball/cubs-pete-crow-armstrong-blasts-3-homers-drives-6-thrash-reds--flm-2026-08-29/" target="_blank" rel="noopener noreferrer">REUTERS CHECK ↗</a></div><p class="morning-credit">PHOTO · MINDA HAAS KUHLMANN · CC BY 2.0 · WIKIMEDIA COMMONS · PETE CROW-ARMSTRONG</p></div>
    </section>

    <section id="next-match-slot" class="section next-match-edition reveal" aria-labelledby="next-match-title">
      <header class="next-match-head"><div><p class="eyebrow">NEXT MATCH · MLB</p><h2 id="next-match-title">Sánchez vs Johnson.<br><span>Ace Edge, Heavy Price.</span></h2></div><p>2026.08.30 KST · 11:07<br>PHILADELPHIA @ LA ANGELS · ANGEL STADIUM</p></header>
      <div class="starter-stage">
        <article class="starter-card"><div class="starter-photo"><img src="assets/morning-20260830/cristopher-sanchez.jpg" alt="Philadelphia Phillies starting pitcher Cristopher Sanchez official MLB profile portrait" width="1200" height="1803"></div><div class="starter-copy"><span>PHILADELPHIA PHILLIES · #61 · LHP</span><h3>CRISTOPHER <b>SÁNCHEZ</b></h3><div><em><strong>16–4</strong>RECORD</em><em><strong>2.62</strong>ERA</em><em><strong>194</strong>SO</em></div></div></article>
        <div class="starter-versus"><strong>PHI</strong><span>AT</span><strong>LAA</strong></div>
        <article class="starter-card"><div class="starter-photo"><img src="assets/morning-20260830/ryan-johnson.jpg" alt="Los Angeles Angels starting pitcher Ryan Johnson official MLB profile portrait" width="1200" height="1803"></div><div class="starter-copy"><span>LOS ANGELES ANGELS · #32 · RHP</span><h3>RYAN <b>JOHNSON</b></h3><div><em><strong>3–7</strong>RECORD</em><em><strong>5.75</strong>ERA</em><em><strong>50</strong>SO</em></div></div></article>
      </div>
      <div class="next-match-read"><small>SFANDOM READ</small><p>선발 비교는 Philadelphia 쪽으로 분명합니다. 다만 좋은 선발과 좋은 베팅 가격은 같은 뜻이 아닙니다. Sánchez의 우위는 NEXT MATCH의 핵심이지만, 시장 가격까지 검증해야 Pick이 됩니다.</p><a href="https://www.mlb.com/probable-pitchers/2026-08-29" target="_blank" rel="noopener noreferrer">MLB PROBABLE PITCHERS ↗</a></div>
    </section>

    <section id="pick-slot" class="section morning-pick reveal" aria-labelledby="morning-pick-title">
      <header class="morning-pick-head"><div><p class="eyebrow">SFANDOM &amp; KAIRO PICK</p><h2 id="morning-pick-title">Good Team.<br><span>Wrong Price.</span></h2></div><p>최종 시장 점검 · 2026.08.30 08:46 KST</p></header>
      <div class="morning-pick-grid"><article class="pick-main-card"><div class="pick-card-top"><span>MARKET CHECK · MLB</span><b>PASS</b></div><p class="pick-match">PHILADELPHIA @ LA ANGELS</p><h3>NO PICK · PASS</h3><div class="pick-price">PHI OPEN -239 → CONSENSUS -229 · SHORT PRICE</div><div class="pick-data"><span><strong>16–4 / 2.62</strong>SÁNCHEZ</span><span><strong>3–7 / 5.75</strong>JOHNSON</span><span><strong>64.4%</strong>NUMBERFIRE WIN</span><span><strong>70–72%</strong>COVERS CONSENSUS</span></div><div class="morning-read"><small>KAIRO ONE-LINE</small><p>선발과 팀 흐름은 Philadelphia가 우세하지만, 시장 가격 대비 모델 우위가 얇고 공개 지표는 과열 신호까지 섞여 있습니다. 무엇보다 SFANDOM 4대 자료 중 실제 tickets/handle 통합 원자료가 완전하지 않아 확정 Pick으로 승격하지 않습니다. <b>EN · Strong favorite, insufficient price and market confirmation — PASS.</b></p></div><p class="pick-risk"><b>WHY PASS</b> · VegasInsider 공개 추세는 Philadelphia 쏠림을 90% 이상으로 표시하는 구간이 있고, Covers 컨센서스는 70%대입니다. 서로 다른 공개 지표만으로 실제 구매율을 대체하지 않습니다.</p><div class="morning-links"><a href="https://www.vegasinsider.com/mlb/matchups/angels-vs-phillies/" target="_blank" rel="noopener noreferrer">LINE MOVEMENT ↗</a><a href="https://contests.covers.com/consensus/matchupconsensusdetails/201cac6c-f690-478b-8489-b38c00fc13a3" target="_blank" rel="noopener noreferrer">COVERS CONSENSUS ↗</a><a href="https://www.fanduel.com/research/phillies-vs-angels-mlb-odds-prediction-point-spread-over-under-and-betting-trends-for-8-29-2026" target="_blank" rel="noopener noreferrer">MODEL + ODDS ↗</a></div></article><aside class="pick-side-card"><span class="pick-pass-label">WATCH ONLY</span><h3>PHI ML</h3><p>승리 방향은 유지하지만 가격과 실제 구매율 원자료가 SFANDOM 컷을 통과하기 전까지는 베팅 Pick이 아닙니다.</p><div class="pick-side-data"><span><strong>-239 → -229</strong>OPEN / CONSENSUS</span><span><strong>PASS</strong>NO FORCED PICK</span></div><hr><span class="pick-support-label">SUPPORT PICK</span><h3>NONE</h3><p>4대 핵심자료가 모두 겹치는 보조 선택도 확인되지 않아 오늘은 추가 Pick을 만들지 않습니다.</p></aside></div>
    </section>'''

replaced = index[:start] + new_block + '\n\n' + index[end:]
index_path.write_text(replaced, encoding='utf-8')

old_runtime_tokens = [
    '37세의 100.1마일.', 'Chourio의 4안타·2홈런.', 'No Fireballs?',
    'Mize vs McClanahan.', 'TAMPA BAY ML', 'assets/morning-20260829/chris-sale.jpg'
]
for token in old_runtime_tokens:
    if token in replaced:
        raise SystemExit(f'Old runtime residue remains in main: {token}')

new_tokens = ['곽빈이 잠실을 쇼케이스로 만들었다.', '토트넘의 새 출발이 흔들린다.', 'Three Swings.', 'Sánchez vs Johnson.', 'NO PICK · PASS']
for token in new_tokens:
    if replaced.count(token) != 1:
        raise SystemExit(f'New content not unique in main: {token}')

current_start = replaced.index(start_marker)
current_end = replaced.index(end_marker, current_start)
current_block = replaced[current_start:current_end]
for token in ['display:none', 'visibility:hidden', 'opacity:0', '!important']:
    if token in current_block:
        raise SystemExit(f'Forbidden hidden/override code in new content: {token}')

assets = [
    'assets/morning-20260830/gwak-been.jpg',
    'assets/morning-20260830/tottenham-hotspur-stadium.jpg',
    'assets/morning-20260830/pete-crow-armstrong.jpg',
    'assets/morning-20260830/cristopher-sanchez.jpg',
    'assets/morning-20260830/ryan-johnson.jpg',
]
for asset in assets:
    p = Path(asset)
    if not p.exists() or p.stat().st_size <= 0:
        raise SystemExit(f'Missing/empty image: {asset}')
    if current_block.count(asset) != 1:
        raise SystemExit(f'Image path not exactly once in new main block: {asset}')

for wf in ['.github/workflows/fetch-morning-assets.yml', '.github/workflows/build-morning-content.yml', '.github/scripts/build_morning_20260830.py']:
    p = Path(wf)
    if p.exists():
        p.unlink()
