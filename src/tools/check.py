#!/usr/bin/env python3
"""SFANDOM 저장소 점검. 올리기 전과 매일 자동 점검에서 같은 기준으로 씁니다.

    python3 src/tools/check.py            # 저장소 루트에서 실행

찌꺼기 파일, 쓰이지 않는 코드·스타일, 깨진 링크, 페이지 형식, 금지어, 사이트맵·검색 색인, 설정을 확인합니다.
실패 항목이 있으면 종료 코드 1."""
import ast, json, pathlib, re, shutil, subprocess, sys, tempfile, html.parser

R = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[2]
SELF = 'src/tools/check.py'
res = []


def check(name, bad, note=''):
    bad = list(bad) if not isinstance(bad, (list, bool)) else bad
    ok = (bad is False) or (bad == [])
    res.append((ok, name, '' if ok else (note or str(bad)[:300])))


def sh(*a, cwd=R):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)


tracked = sh('git', 'ls-files').stdout.split('\n')[:-1]
pages = [p for p in tracked if p.endswith('.html') and not p.startswith('src/')]
H = {p: (R / p).read_text(encoding='utf-8') for p in pages}
SRC = (R / 'src/build.py').read_text(encoding='utf-8')
JS = (R / 'assets/js/site.js').read_text(encoding='utf-8')
CSS = (R / 'assets/css/site.css').read_text(encoding='utf-8')
text_files = [p for p in tracked if p != SELF and not p.startswith('assets/teams/') and p.endswith(('.html', '.css', '.js', '.py', '.json', '.md', '.txt', '.xml', '.yml', '.svg'))]
ALL = {p: (R / p).read_text(encoding='utf-8', errors='ignore') for p in text_files}
visible = lambda s: re.sub(r'<script.*?</script>|<style.*?</style>|<[^>]+>', ' ', s, flags=re.S)

# ── 저장소 · 이전 자료 ──
check('02 가지가 main 하나뿐', [b for b in sh('git', 'branch', '--format=%(refname:short)').stdout.split() if b != 'main'])
old_paths = [p for p in tracked if p.startswith(('archive/', 'scripts/')) or p in (
    'analysis.html', 'content.html', 'about.html', 'terms.html', 'privacy.html', 'community-policy.html', 'legal-notice.html',
    'home.css', 'daily-edition.css', 'morning-content.css', 'visitor-counter.js') or (p.count('/') == 0 and p.endswith(('.css', '.js')))]
check('03 이전 사이트 페이지 · 스타일 · 스크립트 파일 없음', old_paths)
check('05 이전 이미지(avif · webp · 옛 로고) 없음', [p for p in tracked if p.lower().endswith(('.avif', '.webp')) or 'logo-official' in p or p.startswith('assets/sfandom-logo.')])
gone = ['sfandom-logo-official', 'padres-analysis', 'padres-result', 'kairo-feature-rays-pitcher', 'daily-edition', 'morning-content.css', 'home.css',
        'visitor-counter', 'generate_edition', 'edition_prompt', 'legal-notice.html', 'community-policy.html', 'content.html']
check('06 지운 파일을 가리키는 참조 없음', [(p, g) for p, t in ALL.items() for g in gone if g in t])
check('07 저장소 밖 경로 · 임시 경로 · 로컬 주소 없음', [(p, m.group(0)) for p, t in ALL.items() for m in re.finditer(r'localhost|127\.0\.0\.1|/tmp/|scratchpad|/home/claude|/mnt/user-data', t)])
mail = [(p, m.group(0)) for p, t in ALL.items() for m in re.finditer(r'[\w.+-]+@gmail\.com|mailto:', t)]
mail += sorted({x for x in sh('git', 'log', '--all', '--format=%ae %ce').stdout.split() if not x.endswith(('@users.noreply.github.com', '@github.com'))})
check('07b 메일 주소가 파일과 커밋 기록 어디에도 없음 (커밋은 noreply 주소만)', mail)
check('08 추적되지 않은 잉여 파일 없음', [x for x in sh('git', 'status', '--porcelain').stdout.split('\n') if x.strip()])

# ── 빌더 코드 ──
try:
    tree = ast.parse(SRC); err = []
except SyntaxError as e:
    tree = None; err = [str(e)]
check('09 빌더 문법 오류 없음', err)
fns = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
check('10 쓰이지 않는 함수 없음', [f.name for f in fns if f.name != '__init__' and len(re.findall(r'\b' + re.escape(f.name) + r'\b', SRC)) < 2])
lines = SRC.splitlines(); dead = []
for f in fns:
    body = '\n'.join(lines[f.lineno - 1:f.end_lineno])
    for st in f.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            n = st.targets[0].id
            uses = len(re.findall(r'(?<![\w.])' + re.escape(n) + r'(?!\w)', body))
            if uses < 2:
                dead.append(f'{f.name}.{n}')
check('11 쓰이지 않는 변수 없음', dead)
imps = [a.asname or a.name.split('.')[0] for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names]
check('12 쓰이지 않는 불러오기 없음', [i for i in imps if i != 'annotations' and len(re.findall(r'\b' + re.escape(i) + r'\b', SRC)) < 2])
check('13 같은 이름 함수 중복 정의 없음', sorted({f.name for f in tree.body if isinstance(f, ast.FunctionDef) and [g.name for g in tree.body if isinstance(g, ast.FunctionDef)].count(f.name) > 1}))
check('14 디버그 출력 · 임시 표시 없음', [(p, m.group(0)) for p, t in ALL.items() if p.endswith(('.py', '.js', '.css')) for m in re.finditer(r'console\.log|debugger|TODO|FIXME|XXX|HACK|breakpoint\(', t)])
for tool in sorted((R / 'src/tools').glob('*.py')):
    try:
        ast.parse(tool.read_text())
    except SyntaxError as e:
        err.append(f'{tool.name}: {e}')
check('15 보조 도구 문법 오류 없음', err)

# ── 다시 빌드해도 그대로인지 ──
tmp = pathlib.Path(tempfile.mkdtemp()); cp = tmp / 'r'
shutil.copytree(R, cp, ignore=shutil.ignore_patterns('.git', '*.bundle', '__pycache__'))
b = subprocess.run([sys.executable, 'src/build.py'], cwd=cp, capture_output=True, text=True)
check('16 빌드가 오류 없이 끝남', b.returncode != 0, b.stderr[-300:])
diff = [p for p in tracked if p != 'src/content/blog-feed.json' and (not (cp / p).exists() or (cp / p).read_bytes() != (R / p).read_bytes())]
# 결과물에는 빌드한 날짜(파일 버전, D-day)가 들어가므로, 오늘 빌드한 저장소일 때만 완전 일치를 봅니다.
import datetime as _dt
_today = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9))).strftime('%Y%m%d')
if f'site.css?v={_today}' in H.get('index.html', ''):
    check('17 다시 빌드해도 결과가 같음 (손으로 고친 결과물 없음)', diff)
extra = [str(p.relative_to(cp)) for p in cp.rglob('*') if p.is_file() and '__pycache__' not in p.parts and str(p.relative_to(cp)) not in tracked]
check('18 빌드가 저장소에 없는 파일을 새로 만들지 않음', extra)
shutil.rmtree(tmp, ignore_errors=True)

# ── 스크립트 · 스타일 ──
n = subprocess.run(['node', '--check', str(R / 'assets/js/site.js')], capture_output=True, text=True)
check('19 스크립트 문법 오류 없음', n.returncode != 0, n.stderr[-200:])
nocom = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)
check('20 스타일 중괄호 짝이 맞음', nocom.count('{') != nocom.count('}'))
used = set()
for t in H.values():
    for m in re.finditer(r'class=(?:"([^"]*)"|([\w-]+))', t):
        used.update((m.group(1) or m.group(2)).split())
dyn = set(re.findall(r'[A-Za-z_][\w-]*', ' '.join(re.findall(r"'([^']*)'", JS)))) | {'tchip', 'hero-credit', 'blog-thumb', 'seed'}
css_classes = set(re.findall(r'\.([A-Za-z_][\w-]*)', re.sub(r'\{[^{}]*\}', '{}', nocom)))
check('21 쓰이지 않는 스타일 클래스 없음', sorted(c for c in css_classes if c not in used and c not in dyn))
leftovers = re.compile(r'ticker|mega-|megaMenu|visitor|counter|top-stories-old|tbadge|temblem|reel-card|youtube', re.I)
check('22 뺀 기능(움직이는 띠 · 메가 메뉴 · 방문자 카운터 · 옛 로고 방식)의 코드 잔재 없음',
      [(p, m.group(0)) for p in ('src/build.py', 'assets/js/site.js', 'assets/css/site.css', 'src/site.json') for m in leftovers.finditer(ALL[p])])
top = re.sub(r'@media[^{]+\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}', '', nocom)
sel = [s.strip() for s in re.findall(r'(?:^|\})\s*([^{}@]+)\{', top)]
check('23 같은 스타일 규칙이 두 번 정의된 곳 없음', sorted({s for s in sel if sel.count(s) > 1}))
js_sel = set(re.findall(r"\$\$?\('([^']+)'", JS))
miss = []
allhtml = ' '.join(H.values())
for s in js_sel:
    for tok in re.findall(r'[#.][A-Za-z_][\w-]*|\[data-[\w-]+', s):
        key = tok[1:] if tok[0] in '#.' else tok[1:]
        if key not in allhtml and key not in JS.replace(s, ''):
            miss.append((s, tok))
check('24 스크립트가 찾는 요소가 화면에 실제로 있음', miss)

# ── 만들어진 페이지 ──
class P(html.parser.HTMLParser):
    VOID = {'meta', 'link', 'img', 'br', 'input', 'hr', 'source', 'path', 'rect', 'circle', 'line', 'polyline', 'polygon', 'ellipse', 'use'}
    def __init__(s):
        super().__init__(); s.stack = []; s.err = []; s.ids = []; s.noalt = 0; s.empty_href = 0
    def handle_starttag(s, t, a):
        d = dict(a)
        if 'id' in d: s.ids.append(d['id'])
        if t == 'img' and 'alt' not in d: s.noalt += 1
        if t == 'a' and d.get('href', None) in ('', '#', None): s.empty_href += 1
        if t not in s.VOID: s.stack.append(t)
    def handle_startendtag(s, t, a):
        s.handle_starttag(t, a)
        if t not in s.VOID: s.stack.pop()
    def handle_endtag(s, t):
        if t in s.VOID: return
        if not s.stack or s.stack[-1] != t: s.err.append(t)
        else: s.stack.pop()
unbal, dupid, noalt, ehref = [], [], [], []
for p, t in H.items():
    q = P(); q.feed(t)
    if q.err or q.stack: unbal.append((p, q.err[:3], q.stack[:3]))
    d = sorted({i for i in q.ids if q.ids.count(i) > 1})
    if d: dupid.append((p, d))
    if q.noalt: noalt.append((p, q.noalt))
    if q.empty_href: ehref.append((p, q.empty_href))
check('25 모든 페이지의 태그 짝이 맞음', unbal)
check('26 한 페이지 안에 같은 id 중복 없음', dupid)
check('27 모든 이미지에 alt 속성 있음', noalt)
check('28 빈 링크 없음', ehref)
brk = set()
for p, t in H.items():
    for m in re.finditer(r'(?:href|src|poster|data-src)="(/[^"#?]*)', t):
        u = m.group(1)
        if u.startswith('//'): continue
        f = R / u.lstrip('/'); f = f / 'index.html' if u.endswith('/') else f
        if not f.exists(): brk.add((p, u))
check('29 깨진 내부 링크 없음', sorted(brk))
idx = {p: t for p, t in H.items() if 'noindex' not in t}
check('30 모든 페이지에 제목 있음', [p for p, t in H.items() if not re.search(r'<title>[^<]+</title>', t)])
check('31 공개 페이지마다 설명 문구 있음', [p for p, t in idx.items() if not re.search(r'<meta name="description" content="[^"]{10,}"', t)])
titles = {}
for p, t in idx.items(): titles.setdefault(re.search(r'<title>([^<]*)', t).group(1), []).append(p)
check('32 공개 페이지 제목 중복 없음', [v for v in titles.values() if len(v) > 1])
canon = []
for p, t in idx.items():
    m = re.search(r'<link rel="canonical" href="https://sfandom\.com(/[^"]*)"', t)
    want = '/' + (p[:-len('index.html')] if p.endswith('index.html') else p)
    if not m or m.group(1) != want: canon.append((p, m.group(1) if m else None))
check('33 대표 주소(canonical)가 실제 경로와 일치', canon)
bad_out = re.compile(r'\bNone\b|\bundefined\b|\{[a-z_]+\}|\bnull\b')
check('34 화면에 None · undefined · 치환 안 된 자리표시 없음', [(p, m.group(0)) for p, t in H.items() for m in bad_out.finditer(visible(t))])
check('35 빈 제목 · 빈 문단 없음', [(p, m.group(0)) for p, t in H.items() for m in re.finditer(r'<h[1-4][^>]*>\s*</h[1-4]>|<p>\s*</p>', t)])
check('36 금지어(베팅 관련) 없음', [(p, m.group(0)) for p, t in H.items() for m in re.finditer(r'배당|베팅|적중|픽스터|토토|wager|\bodds\b', visible(t), re.I)])

# ── 사이트맵 · 검색 · 설정 ──
sm = re.findall(r'<loc>https://sfandom\.com(/[^<]*)</loc>', ALL.get('sitemap.xml', ''))
smbad = [u for u in sm if not ((R / u.lstrip('/') / 'index.html').exists() if u.endswith('/') else (R / u.lstrip('/')).exists())]
want = {'/' + (p[:-len('index.html')] if p.endswith('index.html') else p) for p in idx if p != '404.html'}
check('37 사이트맵 파일의 주소가 모두 실제 페이지이고 빠진 공개 페이지 없음', smbad + sorted(want - set(sm)))
try:
    si = json.loads(ALL['search-index.json']); sib = [e['u'] for e in si if not (R / e['u'].lstrip('/') / 'index.html').exists()]
except Exception as e:
    sib = [str(e)]
check('38 검색 색인의 주소가 모두 실제 페이지', sib)
jbad = []
for p in tracked:
    if p.endswith('.json'):
        try: json.loads((R / p).read_text(encoding='utf-8'))
        except Exception as e: jbad.append((p, str(e)[:60]))
urls = {}
for f in sorted((R / 'src/content/articles').glob('*.md')):
    m = re.match(r'---\n(.*?)\n---\n', f.read_text(encoding='utf-8'), re.S)
    try:
        fm = {l.split(':', 1)[0].strip(): json.loads(l.split(':', 1)[1].strip()) for l in m.group(1).splitlines()}
        if not fm.get('title') or not fm.get('slug'): jbad.append((f.name, '제목 또는 슬러그 없음'))
    except Exception as e:
        jbad.append((f.name, str(e)[:60]))
check('39 데이터 파일과 글 머리말이 모두 올바른 형식', jbad)
ref = ' '.join(ALL.values())
# 보관용으로 남기는 것: 브랜드 필름 원본, 로고 묶음(assets/brand)
orphans = [p for p in tracked if p.startswith('assets/') and not p.startswith(('assets/brand/', 'assets/teams/')) and pathlib.Path(p).name not in ref and p != 'assets/sfandom-brand-film-20260901.mp4']
conf = []
if (R / 'CNAME').read_text().strip() != 'sfandom.com': conf.append('CNAME')
if not (R / 'ads.txt').read_text().strip(): conf.append('ads.txt')
if 'Sitemap: https://sfandom.com/sitemap.xml' not in ALL['robots.txt']: conf.append('robots sitemap')
wf = ALL['.github/workflows/site-build.yml']
conf += [s for s in re.findall(r'python3 (src/[\w/.-]+)', wf) if not (R / s).exists()]
check('40 어디에서도 쓰이지 않는 자산 없음 · 도메인 · 광고 · 자동 작업 설정 정상', orphans + conf)

fails = [r for r in res if not r[0]]
for ok, name, note in res:
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else '\n      → ' + note))
print(f'\n{len(res)}개 항목 · 통과 {len(res) - len(fails)} · 실패 {len(fails)}')
sys.exit(1 if fails else 0)
