(() => {
  'use strict';

  if (window.__SFANDOM_GLOBAL_COUNTER_V4__) return;
  window.__SFANDOM_GLOBAL_COUNTER_V4__ = true;

  const header = document.querySelector('.site-header.home-header');
  const brand = header?.querySelector('.brand');
  if (!header || !brand) return;

  const root = document.createElement('div');
  root.className = 'sf-basic-counter';
  root.setAttribute('aria-label', 'SFANDOM visitors');

  const label = document.createElement('span');
  label.textContent = 'VISITORS';

  const value = document.createElement('b');

  const CACHE_KEY = 'sfandom-global-counter-v3-last';
  const KEY = 'sfandom-home-global-20260918';
  const API = 'https://countapi.mileshilliard.com/api/v1';

  const parseCount = (raw) => {
    const text = String(raw ?? '').trim();
    if (!/^\d+$/.test(text)) throw new Error('invalid counter value');
    return BigInt(text);
  };

  let last = null;
  try {
    const saved = localStorage.getItem(CACHE_KEY);
    if (saved !== null) last = parseCount(saved);
  } catch (_) {}

  value.textContent = last === null ? '------' : String(last).padStart(6, '0');
  root.append(label, value);
  brand.insertAdjacentElement('afterend', root);

  const saveAndShow = (count) => {
    last = count;
    value.textContent = String(count).padStart(6, '0');
    try { localStorage.setItem(CACHE_KEY, String(count)); } catch (_) {}
  };

  const requestJson = (url) =>
    fetch(url, {
      method: 'GET',
      mode: 'cors',
      cache: 'no-store',
      credentials: 'omit'
    }).then((response) => {
      if (!response.ok) throw new Error('counter ' + response.status);
      return response.json();
    });

  requestJson(API + '/hit/' + KEY)
    .then(async (data) => {
      let serverCount = parseCount(data && data.value);

      if (serverCount <= 1n) {
        const recovered = await requestJson(API + '/set/' + KEY + '?value=200');
        serverCount = parseCount(recovered && recovered.value);
      } else if (last !== null && serverCount < last) {
        const repaired = last + 1n;
        const recovered = await requestJson(API + '/set/' + KEY + '?value=' + repaired.toString());
        serverCount = parseCount(recovered && recovered.value);
      }

      saveAndShow(serverCount);
    })
    .catch(() => {
      if (last !== null) {
        value.textContent = String(last).padStart(6, '0');
      }
    });

  const style = document.createElement('style');
  style.textContent = `
    .sf-basic-counter{display:inline-flex;align-items:center;gap:7px;flex:0 0 auto;height:30px;margin-left:8px;padding:0 10px;border:1px solid rgba(255,255,255,.11);border-radius:2px;background:rgba(255,255,255,.018);color:#e7e7e3;font:700 12px/1 system-ui,-apple-system,"Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",sans-serif;letter-spacing:.08em;white-space:nowrap}
    .sf-basic-counter span{opacity:.52}
    .sf-basic-counter b{min-width:52px;font-size:14px;font-weight:800;letter-spacing:.06em;text-align:right;font-variant-numeric:tabular-nums}
    @media(max-width:900px){.sf-basic-counter{height:28px;padding:0 9px}}
    @media(max-width:720px){.sf-basic-counter{position:absolute;top:calc(100% + 8px);right:18px;z-index:2;margin-left:0;background:rgba(6,6,6,.92)}}
  `;
  document.head.appendChild(style);
})();