from pathlib import Path
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

out = Path('qa-render')
out.mkdir(exist_ok=True)

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--disable-gpu')
opts.add_argument('--hide-scrollbars')
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

driver = webdriver.Chrome(options=opts)
results = []
try:
    for width, height in [(1440, 1200), (390, 844)]:
        driver.set_window_size(width, height)
        driver.get('http://127.0.0.1:8000/index.html')
        WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.readyState === 'complete'"))
        WebDriverWait(driver, 20).until(lambda d: d.execute_script("return Array.from(document.images).every(i => i.complete)"))
        driver.execute_script("document.querySelectorAll('video').forEach(v=>v.pause())")
        time.sleep(0.5)
        data = driver.execute_script('''
          const imgs = Array.from(document.images).map(i => ({
            src: i.getAttribute('src'),
            complete: i.complete,
            naturalWidth: i.naturalWidth,
            naturalHeight: i.naturalHeight,
            renderedWidth: Math.round(i.getBoundingClientRect().width),
            renderedHeight: Math.round(i.getBoundingClientRect().height)
          }));
          const ids = ['daily-news-slot','kairo-feature-slot','next-match-slot','pick-slot'];
          const sections = Object.fromEntries(ids.map(id => {
            const e = document.getElementById(id);
            if (!e) return [id, null];
            const r = e.getBoundingClientRect();
            return [id, {width: Math.round(r.width), height: Math.round(r.height), left: Math.round(r.left), right: Math.round(r.right)}];
          }));
          return {
            innerWidth: window.innerWidth,
            docScrollWidth: document.documentElement.scrollWidth,
            bodyScrollWidth: document.body.scrollWidth,
            overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
            brokenImages: imgs.filter(i => !i.complete || i.naturalWidth === 0 || i.naturalHeight === 0),
            images: imgs,
            sections
          };
        ''')
        logs = driver.get_log('browser')
        severe = [x for x in logs if x.get('level') == 'SEVERE' and 'favicon.ico' not in x.get('message','')]
        data['browserSevere'] = severe
        data['viewportRequested'] = [width, height]

        for sec_id, label in [
            ('daily-news-slot','daily'),
            ('kairo-feature-slot','kairo'),
            ('next-match-slot','next'),
            ('pick-slot','pick'),
        ]:
            el = driver.find_element('id', sec_id)
            driver.execute_script("arguments[0].scrollIntoView({block:'start'});", el)
            time.sleep(0.25)
            driver.save_screenshot(str(out / f'{width}-{label}-top.png'))
            sec_height = data['sections'][sec_id]['height']
            if sec_height > height:
                driver.execute_script("window.scrollBy(0, Math.min(arguments[0], arguments[1] * 0.72));", sec_height - height, height)
                time.sleep(0.2)
                driver.save_screenshot(str(out / f'{width}-{label}-mid.png'))

        results.append(data)
        Path('qa-render/results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        if data['overflow'] != 0:
            raise SystemExit(f'Horizontal overflow at {width}px: {data["overflow"]}')
        if data['brokenImages']:
            raise SystemExit(f'Broken images at {width}px: {data["brokenImages"]}')
        if severe:
            raise SystemExit(f'Browser severe errors at {width}px: {severe}')
        for sec_id, rect in data['sections'].items():
            if rect is None or rect['left'] < 0 or rect['right'] > data['innerWidth'] + 1:
                raise SystemExit(f'Section outside viewport at {width}px: {sec_id}={rect}')
finally:
    driver.quit()

print(json.dumps(results, ensure_ascii=False, indent=2))
