(() => {
  'use strict';

  if (window.__SFANDOM_VISITOR_COUNTER__) return;
  window.__SFANDOM_VISITOR_COUNTER__ = true;

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
  const HIT_ENDPOINT = 'https://countapi.mileshilliard.com/api/v1/hit/' + KEY;

  const parseCount = (raw) => {
    const text = String(raw ?? '').trim();
    if (!/^\d+$/.test(text)) throw new Error('invalid counter value');
    return BigInt(text);
  };

  let cached = null;
  try {
    const saved = localStorage.getItem(CACHE_KEY);
    if (saved !== null) cached = parseCount(saved);
  } catch (_) {}

  value.textContent = cached === null ? '------' : String(cached).padStart(6, '0');
  root.append(label, value);
  brand.insertAdjacentElement('afterend', root);

  fetch(HIT_ENDPOINT, {
    method: 'GET',
    mode: 'cors',
    cache: 'no-store',
    credentials: 'omit'
  })
    .then((response) => {
      if (!response.ok) throw new Error('counter ' + response.status);
      return response.json();
    })
    .then((data) => {
      const serverCount = parseCount(data?.value);
      const displayCount = cached !== null && cached > serverCount ? cached : serverCount;
      value.textContent = String(displayCount).padStart(6, '0');
      try { localStorage.setItem(CACHE_KEY, String(displayCount)); } catch (_) {}
    })
    .catch(() => {
      if (cached !== null) value.textContent = String(cached).padStart(6, '0');
    });
})();
