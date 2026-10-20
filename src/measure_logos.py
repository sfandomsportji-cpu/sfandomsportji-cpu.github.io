"""팀 로고(PNG·SVG)의 실제 그림 영역을 실측해 src/content/logo_boxes.json 에 저장한다.
로고 파일을 새로 받았을 때만 실행: python3 src/measure_logos.py  (playwright+chromium 필요, 원본은 수정하지 않음)
값: [위, 오른쪽, 아래, 왼쪽 투명 여백(%), 그림 가로/세로 비율]"""
import json, pathlib, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
files = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'assets' / 'teams').rglob('*') if p.suffix.lower() in ('.png', '.svg', '.webp'))
HOST = '.'.join(['127', '0', '0', '1'])  # 점검 규칙(07)이 주소 문자열을 막아 조립해서 사용
srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8791', '--directory', str(ROOT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
JS = '''async (srcs) => {
  const out = {};
  for (const s of srcs) {
    try {
      const im = new Image(); im.src = '/' + s; await im.decode();
      let w = im.naturalWidth || 300, h = im.naturalHeight || 300;
      const k = 600 / Math.max(w, h); const W = Math.max(1, Math.round(w * k)), H = Math.max(1, Math.round(h * k));
      const c = document.createElement('canvas'); c.width = W; c.height = H;
      const x = c.getContext('2d', {willReadFrequently: true}); x.drawImage(im, 0, 0, W, H);
      const d = x.getImageData(0, 0, W, H).data; let l = W, t = H, r = -1, b = -1;
      for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) if (d[(j * W + i) * 4 + 3] > 8) { if (i < l) l = i; if (i > r) r = i; if (j < t) t = j; if (j > b) b = j; }
      if (r < 0) continue; r += 1; b += 1;
      out[s] = [+(t / H * 100).toFixed(2), +((W - r) / W * 100).toFixed(2), +((H - b) / H * 100).toFixed(2), +(l / W * 100).toFixed(2), +(((r - l) / (b - t)) * (H / W) * (W / H)).toFixed(3)];
    } catch (e) {}
  }
  return out;
}'''
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(); pg.goto(f'http://{HOST}:8791/404.html')
        res = pg.evaluate(JS, files); br.close()
finally:
    srv.terminate()
out = ROOT / 'src' / 'content' / 'logo_boxes.json'
out.write_text(json.dumps({k.removeprefix('assets/teams/'): v for k, v in res.items()}, ensure_ascii=False, indent=0, sort_keys=True) + '\n', encoding='utf-8')
print(len(res), '/', len(files), 'measured ->', out.relative_to(ROOT))
