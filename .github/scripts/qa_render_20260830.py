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
        time.sleep(1)
        data = driver.execute_script('''
          const imgs = Array.from(document.images).map(i => ({
            src: i.getAttribute('src'),
            complete: i.complete,
            naturalWidth: i.naturalWidth,
            naturalHeight: i.naturalHeight,
            renderedWidth: Math.round(i.getBoundingClientRect().width),
            renderedHeight: Math.round(i.getBoundingClientRect().height)
          }));
          const content = document.querySelector('#daily-news-slot');
          const pick = document.querySelector('#pick-slot');
          return {
            innerWidth: window.innerWidth,
            docScrollWidth: document.documentElement.scrollWidth,
            bodyScrollWidth: document.body.scrollWidth,
            overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth,
            brokenImages: imgs.filter(i => !i.complete || i.naturalWidth === 0 || i.naturalHeight === 0),
            images: imgs,
            contentTop: content ? Math.round(content.getBoundingClientRect().top + scrollY) : null,
            pickBottom: pick ? Math.round(pick.getBoundingClientRect().bottom + scrollY) : null
          };
        ''')
        logs = driver.get_log('browser')
        severe = [x for x in logs if x.get('level') == 'SEVERE']
        data['browserSevere'] = severe
        data['viewportRequested'] = [width, height]
        data['screenshot'] = f'qa-render/{width}.png'
        driver.save_screenshot(data['screenshot'])
        results.append(data)
        if data['overflow'] != 0:
            raise SystemExit(f'Horizontal overflow at {width}px: {data["overflow"]}')
        if data['brokenImages']:
            raise SystemExit(f'Broken images at {width}px: {data["brokenImages"]}')
        if severe:
            raise SystemExit(f'Browser severe errors at {width}px: {severe}')
finally:
    driver.quit()

Path('qa-render/results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(results, ensure_ascii=False, indent=2))
