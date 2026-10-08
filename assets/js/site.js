/* SFANDOM site script — 메뉴 · 광고 슬롯 · 릴스 · 쪽지 · 팀 로고 · 블로그 · 팬 보드 · 검색 */
(() => {
  'use strict';
  const CFG = window.SFANDOM || {};
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };

  /* 외부 이미지 서버가 차단되어도 콘텐츠 카드가 빈 화면이 되지 않도록 안전하게 표시 */
  const fallbackImage = img => {
    if (!img || img.dataset.fallbackApplied) return;
    const thumb = img.closest('.thumb');
    if (!thumb) return;
    img.dataset.fallbackApplied = '1';
    img.remove();
    thumb.classList.add('thumb-fallback');
    if (!thumb.querySelector('.thumb-fallback-text')) {
      const label = img.closest('.portrait') ? 'NBA' : 'SFANDOM';
      thumb.append(el('span', 'thumb-fallback-text', label));
    }
  };
  document.addEventListener('error', e => {
    if (e.target?.tagName === 'IMG') fallbackImage(e.target);
  }, true);
  $$('img').forEach(img => {
    if (img.complete && img.naturalWidth === 0) fallbackImage(img);
  });

  /* ── 전체 메뉴 · 검색 ── */
  const toggle = (btn, panel, focusSel) => {
    if (!btn || !panel) return;
    btn.addEventListener('click', () => {
      const open = panel.hasAttribute('hidden');
      $$('[data-panel]').forEach(p => p.setAttribute('hidden', ''));
      $$('[aria-controls]').forEach(b => b.setAttribute('aria-expanded', 'false'));
      if (open) {
        panel.removeAttribute('hidden');
        btn.setAttribute('aria-expanded', 'true');
        const f = focusSel && $(focusSel, panel);
        if (f) f.focus();
      }
    });
  };
  toggle($('#searchBtn'), $('#searchBar'), 'input');
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    $$('[data-panel]').forEach(p => p.setAttribute('hidden', ''));
    $$('[aria-controls]').forEach(b => b.setAttribute('aria-expanded', 'false'));
  });

  /* ── 광고 슬롯 ──
     src/site.json 의 ads.slots 에서 unit(광고 단위 ID)이 채워지고 phase 가 현재 단계 이하인 슬롯만 켭니다.
     주소 뒤에 ?adpreview=1 을 붙이면 모든 자리를 빨간 박스로 보여줍니다. */
  const ads = CFG.ads || {};
  const preview = /[?&]adpreview=1/.test(location.search);
  $$('.ad[data-ad]').forEach(box => {
    const id = box.dataset.ad;
    const slot = (ads.slots || {})[id] || {};
    if (preview) {
      box.hidden = false;
      box.classList.add('preview', slot.phase === 1 ? 'p1' : 'p2');
      box.textContent = `${id} · ${slot.phase === 1 ? '1단계 · 심사 중부터' : '2단계 · 승인 후'}`;
      return;
    }
    if (!ads.client || !slot.unit || (slot.phase || 9) > (ads.phase || 0)) return;
    const ins = el('ins', 'adsbygoogle');
    ins.style.display = 'block';
    ins.dataset.adClient = ads.client;
    ins.dataset.adSlot = slot.unit;
    if (slot.format) ins.dataset.adFormat = slot.format;
    if (slot.layout) ins.dataset.adLayout = slot.layout;
    if (slot.responsive !== false) ins.dataset.fullWidthResponsive = 'true';
    box.append(ins);
    box.hidden = false;
    try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (_) {}
  });

  /* ── 첫 화면 배경 영상: 자동재생 + 자동 사운드 복구 ── */
  const heroVideo = $('.hero-video');
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const saveData = navigator.connection && navigator.connection.saveData;

  if (heroVideo && heroVideo.dataset.src && !reduce && !saveData) {
    heroVideo.addEventListener('playing', () => {
      heroVideo.classList.add('on');
      heroVideo.parentElement.classList.add('playing');
    }, { once: true });

    let dimTimer = null;
    const dim = () => {
      if (!heroVideo.classList.contains('on')) return;
      clearTimeout(dimTimer);
      dimTimer = setTimeout(() => heroVideo.classList.add('dim'), 250);
    };
    const undim = () => {
      clearTimeout(dimTimer);
      heroVideo.classList.remove('dim');
    };
    heroVideo.addEventListener('waiting', dim);
    heroVideo.addEventListener('stalled', dim);
    heroVideo.addEventListener('playing', undim);

    if (!heroVideo.getAttribute('src')) heroVideo.src = heroVideo.dataset.src;
    heroVideo.preload = 'auto';
    heroVideo.volume = 0.65;

    const muteToggle = document.createElement('button');
    muteToggle.type = 'button';
    muteToggle.className = 'hero-mute-toggle';
    muteToggle.setAttribute('aria-label', '음악 음소거');
    muteToggle.setAttribute('aria-pressed', 'false');
    muteToggle.innerHTML = '<span aria-hidden="true">🔊</span>';
    muteToggle.style.cssText = 'position:absolute;right:18px;bottom:18px;z-index:12;width:44px;height:44px;border:1px solid rgba(255,255,255,.42);border-radius:50%;background:rgba(11,11,15,.68);color:#fff;font-size:20px;display:flex;align-items:center;justify-content:center;cursor:pointer;backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)';
    heroVideo.closest('.hero')?.append(muteToggle);

    const syncMuteToggle = () => {
      const isMuted = heroVideo.muted;
      muteToggle.innerHTML = isMuted ? '<span aria-hidden="true">🔇</span>' : '<span aria-hidden="true">🔊</span>';
      muteToggle.setAttribute('aria-label', isMuted ? '음악 켜기' : '음악 음소거');
      muteToggle.setAttribute('aria-pressed', String(isMuted));
    };

    muteToggle.addEventListener('click', async () => {
      heroVideo.muted = !heroVideo.muted;
      if (!heroVideo.muted) {
        heroVideo.volume = 0.65;
        try { await heroVideo.play(); } catch (_) {}
      }
      syncMuteToggle();
    });

    heroVideo.addEventListener('volumechange', syncMuteToggle);
    syncMuteToggle();

    // 안정화: 소리는 사용자가 음소거 버튼을 직접 누를 때만 켭니다.
    // 외부 동영상 로딩 실패 시 저장소의 로컬 영상으로 전환합니다.
    const backupHeroVideo = '/assets/sfandom-hero-loop.mp4';
    let backupActive = false;
    const onVideoFailure = () => {
      heroVideo.classList.remove('on', 'dim');
      heroVideo.parentElement?.classList.remove('playing');
      if (!backupActive) {
        backupActive = true;
        heroVideo.src = backupHeroVideo;
        heroVideo.load();
        heroVideo.play().catch(() => {});
      } else {
        heroVideo.pause();
        heroVideo.removeAttribute('src');
        heroVideo.load();
        muteToggle.hidden = true;
      }
    };
    heroVideo.addEventListener('error', onVideoFailure);
    const firstFrameTimer = setTimeout(() => {
      if (!backupActive && heroVideo.readyState < 2) onVideoFailure();
    }, 8500);
    heroVideo.addEventListener('playing', () => clearTimeout(firstFrameTimer), { once: true });
    heroVideo.muted = true;
    syncMuteToggle();
    heroVideo.play().catch(() => {});

    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && heroVideo.paused && heroVideo.src) heroVideo.play().catch(() => {});
    });
  }

  /* ── FAN ZONE 릴스: 인스타그램 화면이 뜨지 않으면 사이트의 브랜드 영상으로 그 자리를 채움 ──
     인스타그램 임베드는 뜨는 즉시 부모 창에 메시지를 보냅니다. 화면에 들어온 뒤 8초 동안 메시지가 없으면 실패로 봅니다. */
  const reel = $('[data-reel]');
  if (reel) {
    const frame = $('iframe', reel), fb = $('.reel-fallback', reel);
    let alive = false, timer = null;
    window.addEventListener('message', e => { if (/^https:\/\/([a-z0-9-]+\.)*instagram\.com$/.test(e.origin || '')) { alive = true; clearTimeout(timer); } });
    const fail = () => {
      if (alive || !fb) return;
      reel.classList.add('failed'); fb.hidden = false;
      if (!fb.getAttribute('src')) fb.src = fb.dataset.src;
      fb.play().catch(() => {});
    };
    if (frame && fb && 'IntersectionObserver' in window) {
      const io = new IntersectionObserver(es => { if (es.some(x => x.isIntersecting)) { io.disconnect(); timer = setTimeout(fail, 8000); } }, { rootMargin: '200px' });
      io.observe(reel);
      frame.addEventListener('error', fail, { once: true });
    }
  }

  /* ── 문의(쪽지) 양식: 메일 주소를 노출하지 않고 사이트 안에서 접수 → 드라이브 "SFANDOM 쪽지함" 시트에 저장 ──
     받는 쪽(Apps Script 웹 앱)은 nick · email · message · page · website 값을 받고, message는 1000자까지 저장합니다. */
  const cf = $('[data-contact]');
  if (cf) {
    const msg = $('[data-contact-msg]', cf), btn = $('button[type=submit]', cf), endpoint = cf.dataset.endpoint, opened = Date.now();
    const say = (t, bad) => { msg.textContent = t; msg.style.color = bad ? 'var(--red)' : ''; };
    cf.addEventListener('submit', async e => {
      e.preventDefault();
      if (!endpoint) return;
      const fd = new FormData(cf), v = k => String(fd.get(k) || '').trim();
      if (v('website')) return;                                   // 자동 프로그램이 채우는 숨은 칸
      if (Date.now() - opened < 4000) return say('잠시 뒤에 다시 눌러 주세요.', true);
      if (v('title').length < 2 || v('body').length < 10) return say('제목과 내용을 조금 더 적어 주세요.', true);
      if (v('reply') && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v('reply'))) return say('이메일 주소 형식을 확인해 주세요.', true);
      if (!fd.get('agree')) return say('수집·보관 동의에 체크해 주세요.', true);
      const message = `[${v('type')}] ${v('title').slice(0, 100)}\n\n${v('body').slice(0, 850)}`.slice(0, 1000);
      btn.disabled = true; say('보내는 중입니다…');
      try {
        // 받는 쪽이 다른 주소라 응답 내용은 읽을 수 없습니다. 전송이 끝나면 접수 안내만 보여 줍니다.
        await fetch(endpoint, { method: 'POST', mode: 'no-cors',
          body: new URLSearchParams({ nick: v('name').slice(0, 40), email: v('reply').slice(0, 120), message, website: '', page: location.pathname }) });
        cf.reset(); cf.classList.add('sent'); say('쪽지가 전달됐습니다. 확인 후 필요한 경우 회신드리겠습니다.');
      } catch (err) {
        btn.disabled = false; say('전송하지 못했습니다. 잠시 뒤 다시 시도해 주세요.', true);
      }
    });
  }

  /* ── 팀 로고: 못 불러오면 팀 색 약자 칩으로 ── */
  $$('img.tlogo').forEach(im => {
    const fail = () => im.parentNode && im.parentNode.classList.add('nologo');
    if (im.complete && im.naturalWidth === 0 && im.currentSrc) fail(); else im.addEventListener('error', fail, { once: true });
  });

  /* ── 오늘의 분석 카드: 휴대폰에서 세 칸 펼치기 ── */
  $$('[data-ta-toggle]').forEach(btn => btn.addEventListener('click', () => {
    const open = btn.closest('.ta-card').classList.toggle('open');
    btn.setAttribute('aria-expanded', open);
    btn.textContent = open ? '접기' : '선발 · 흐름 · 변수 펼치기';
  }));

  /* ── 매거진: 구글 블로그(Blogger) 최신 글을 브라우저에서 바로 받아 합치기 ──
     네이버 글은 빌드 때 받아 HTML에 들어 있고, 구글 글은 여기서 JSONP로 최신 상태를 가져옵니다. */
  const grids = $$('[data-blog-grid]');
  const blogUrl = grids[0]?.dataset.blogger;
  if (grids.length && blogUrl) {
    // 정적 글이 이미 있는 경우 외부 API 실패와 무관하게 대기 문구를 즉시 숨깁니다.
    grids.forEach(g => { const e = g.nextElementSibling; if (e?.classList.contains('blog-empty') && $('a.mag', g).length) e.hidden = true; });
    const cb = '__sfBlogger' + Date.now();
    const bigImg = u => (u || '').replace(/\/[sw]\d+(?:-[a-z]+\d*)*\//, '/w800-rj/').replace(/=[sw]\d+(?:-[a-z]+\d*)*$/, '=w800-rj');
    const strip = h => { const d = document.createElement('div'); d.innerHTML = h || ''; return (d.textContent || '').replace(/\s+/g, ' ').trim(); };
    window[cb] = data => {
      const entries = data?.feed?.entry || [];
      const posts = entries.map(e => {
        const link = (e.link || []).find(l => l.rel === 'alternate')?.href || '';
        let img = e.media$thumbnail?.url || '';
        if (!img) { const m = (e.content?.$t || '').match(/<img[^>]+src="([^"]+)"/i); img = m ? m[1] : ''; }
        return { title: e.title?.$t || '', link, date: (e.published?.$t || '').slice(0, 10), img: bigImg(img),
                 summary: (s => s.length > 320 ? s.slice(0, 319).trimEnd() + '…' : s)(strip(e.summary?.$t || e.content?.$t)) };
      }).filter(p => p.link);
      grids.forEach(grid => {
        const have = new Set($$('a[href]', grid).map(a => a.href));
        const core = grid.dataset.core ? new RegExp(grid.dataset.core, 'i') : null;   // 홈: NBA·MLB 글만
        posts.forEach(p => {
          if (have.has(p.link) || (core && !core.test(p.title + ' ' + p.summary))) return;
          const a = el('a', 'mag lift'); a.href = p.link; a.target = '_blank'; a.rel = 'noopener';
          a.dataset.date = p.date; a.dataset.src = 'google';
          const th = el('div', 'thumb' + (p.img ? '' : ' blog-thumb'));
          if (p.img) { const im = el('img'); im.src = p.img; im.alt = ''; im.loading = 'lazy'; im.referrerPolicy = 'no-referrer'; th.append(im); } else th.append(el('span', null, 'G'));
          const body = el('div', 'body');
          body.append(el('span', 'tag red', grid.dataset.label || 'GOOGLE BLOG'), el('h3', null, p.title), el('p', null, p.summary),
                      el('span', 'tag', `${p.date.replace(/-/g, '.')} · 블로그에서 읽기 ↗`));
          a.append(th, body); grid.append(a);
        });
        const cards = $$('a.mag', grid).sort((x, y) => (y.dataset.date || '').localeCompare(x.dataset.date || ''));
        const limit = Number(grid.dataset.limit || 6);
        cards.forEach((c, i) => { if (i < limit) grid.append(c); else c.remove(); });
        const empty = grid.nextElementSibling;
        if (empty && empty.classList.contains('blog-empty')) empty.hidden = cards.length > 0;
      });
      delete window[cb];
    };
    const sc = document.createElement('script');
    sc.src = `${blogUrl.replace(/\/$/, '')}/feeds/posts/default?alt=json-in-script&max-results=24&callback=${cb}`;
    sc.async = true;
    sc.onerror = () => grids.forEach(g => { const e = g.nextElementSibling; if (e && !$$('a.mag', g).length) e.textContent = '블로그 글을 불러오지 못했습니다. 아래 블로그 바로가기를 이용해 주세요.'; });
    document.head.append(sc);
  }

  /* ── Supabase 공통 ── */
  const SB = CFG.supabase || {};
  const request = async (path, options = {}) => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 8000);
    try {
      const res = await fetch(SB.url + path, {
        ...options, signal: ctrl.signal, cache: 'no-store', credentials: 'omit',
        headers: { apikey: SB.key, Accept: 'application/json', ...(options.headers || {}) }
      });
      if (!res.ok) { const err = new Error('http ' + res.status); err.status = res.status; throw err; }
      return res;
    } finally { clearTimeout(timer); }
  };
  const fmtTime = raw => {
    const d = new Date(raw);
    if (!raw || Number.isNaN(d.getTime())) return '';
    const diff = (Date.now() - d.getTime()) / 60000;
    if (diff < 1) return '방금';
    if (diff < 60) return Math.floor(diff) + '분 전';
    if (diff < 1440) return Math.floor(diff / 60) + '시간 전';
    return new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', month: '2-digit', day: '2-digit' }).format(d);
  };

  /* ── 팬 보드 ──
     채널·경기 스레드·한 줄 평은 글 제목 앞의 [머리말]로 구분합니다. 예) "[NBA] 제목", "[PHI@NYK] 제목", "[한줄] 내용"
     게시판 저장소(posts 표)는 그대로 쓰고, 목록을 불러올 때 제목 머리말로 걸러 냅니다. */
  const QUICK = '한줄';
  const splitTag = title => { const m = /^\[([^\]]{1,20})\]\s*(.*)$/.exec(title || ''); return m ? [m[1], m[2]] : ['자유', title || '']; };
  const likeTag = t => 'like.' + encodeURIComponent('[' + t + ']') + '*';
  const throttled = () => { let last = 0; try { last = Number(localStorage.getItem('sfandom_community_last_post_at') || 0); } catch (_) {} return Date.now() - last < 15000; };
  const stamp = () => { try { localStorage.setItem('sfandom_community_last_post_at', String(Date.now())); } catch (_) {} };
  const sendPost = (nickname, title, body) => request('/functions/v1/community-post', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nickname, title, body }) });
  const postError = err => err && err.status === 429 ? '연속 등록 방지를 위해 잠시 후 다시 작성해 주세요.' : '게시하지 못했습니다. 잠시 후 다시 시도해 주세요.';

  const renderPosts = (list, rows, total, page, size) => {
    list.replaceChildren();
    if (!rows.length) { list.append(el('div', 'empty', '아직 글이 없습니다. 첫 글을 남겨보세요.')); return; }
    rows.forEach((p, i) => {
      const [tag, title] = splitTag(p.title);
      const a = el('article', 'post');
      a.append(el('span', 'post-no', String(Math.max(1, total - ((page - 1) * size + i)))));
      const b = el('div', 'post-body');
      const meta = el('span', 'post-meta');
      meta.append(el('b', null, '#' + tag), document.createTextNode(` · ${p.nickname || 'ANON'} · ${fmtTime(p.created_at)}`));
      b.append(meta, el('strong', null, title || '(제목 없음)'), el('p', null, p.body || ''));
      a.append(b);
      list.append(a);
    });
  };

  const params = new URLSearchParams(location.search);
  const channel = (params.get('ch') || '').slice(0, 20), thread = (params.get('thread') || '').slice(0, 20);
  const onBoardPage = !!$('[data-board-form]');
  $$('[data-chips] a').forEach(a => { if (onBoardPage && !thread && a.dataset.ch === channel) a.setAttribute('aria-current', 'page'); });

  const board = $('[data-board]');
  if (board && SB.url) {
    const size = Number(board.dataset.size || 10);
    const list = $('[data-board-list]', board);
    const pager = $('[data-board-pager]', board);
    const form = $('[data-board-form]');
    const status = $('[data-board-status]');
    const scope = onBoardPage ? (thread || channel) : '';
    let page = 1, total = 0, busy = false;

    const head = $('[data-thread-head]', board);
    if (head && thread) { head.hidden = false; $('[data-thread-name]', head).textContent = thread.replace('@', ' @ '); }
    const sel = form && form.querySelector('[name="channel"]');
    if (sel && thread) { const o = el('option', null, thread.replace('@', ' @ ') + ' 경기 스레드'); o.value = thread; sel.append(o); sel.value = thread; }
    else if (sel && channel && [...sel.options].some(o => o.value === channel)) sel.value = channel;

    const renderPager = () => {
      if (!pager) return;
      pager.replaceChildren();
      const pages = Math.max(1, Math.ceil(total / size));
      const mk = (label, target, disabled, current) => {
        const b = el('button', null, label);
        b.type = 'button'; b.disabled = disabled;
        if (current) b.setAttribute('aria-current', 'page');
        b.addEventListener('click', () => { if (!busy && target !== page) { page = target; load(); } });
        pager.append(b);
      };
      mk('‹', Math.max(1, page - 1), page === 1);
      const start = Math.max(1, Math.min(page - 2, Math.max(1, pages - 4)));
      for (let p = start; p <= Math.min(pages, start + 4); p++) mk(String(p), p, false, p === page);
      mk('›', Math.min(pages, page + 1), page === pages);
    };

    const load = async () => {
      busy = true;
      const from = (page - 1) * size;
      // 한 줄 평은 QUICK TALK에만 보이게 일반 목록에서 뺍니다. '자유'는 머리말이 없는 글도 포함합니다.
      const filter = scope === '자유' ? '&title=not.like.' + encodeURIComponent('[') + '*'
        : scope ? '&title=' + likeTag(scope) : '&title=not.' + likeTag(QUICK);
      try {
        const res = await request('/rest/v1/posts?select=id,title,body,nickname,created_at&status=eq.published&order=created_at.desc' + filter, {
          headers: { Prefer: 'count=exact', 'Range-Unit': 'items', Range: `${from}-${from + size - 1}` }
        });
        const rows = await res.json();
        const m = (res.headers.get('content-range') || '').match(/\/(\d+)$/);
        total = m ? Number(m[1]) : rows.length;
        renderPosts(list, rows, total, page, size);
        renderPager();
      } catch (_) {
        list.replaceChildren(el('div', 'empty', '팬 보드 연결이 잠시 원활하지 않습니다. 잠시 후 다시 시도해 주세요.'));
        if (pager) pager.replaceChildren();
      } finally { busy = false; }
    };

    form?.addEventListener('submit', async e => {
      e.preventDefault();
      if (busy) return;
      const fd = new FormData(form);
      if (String(fd.get('website') || '').trim()) return;
      const nickname = String(fd.get('nickname') || '').trim().slice(0, 30) || 'ANON';
      const ch = String(fd.get('channel') || '자유').trim().slice(0, 20);
      const raw = String(fd.get('title') || '').trim().replace(/^\[[^\]]*\]\s*/, '').slice(0, 100);
      const body = String(fd.get('body') || '').trim().slice(0, 2000);
      if (raw.length < 2 || body.length < 2) { status.textContent = '제목과 내용을 2자 이상 입력해 주세요.'; return; }
      if (throttled()) { status.textContent = '연속 등록 방지를 위해 잠시 후 다시 작성해 주세요.'; return; }
      const title = (ch === '자유' ? raw : `[${ch}] ${raw}`).slice(0, 120);
      busy = true; status.textContent = '게시 중입니다…';
      const btn = form.querySelector('button[type="submit"]'); if (btn) btn.disabled = true;
      try {
        await sendPost(nickname, title, body);
        stamp();
        const keep = sel ? sel.value : '';
        form.reset(); if (sel && keep) sel.value = keep;
        page = 1; status.textContent = '게시되었습니다.';
        busy = false; await load();
      } catch (err) {
        status.textContent = postError(err);
      } finally { busy = false; if (btn) btn.disabled = false; }
    });

    // 글의 "토론하기"에서 넘어오면 제목을 미리 채웁니다. "[NBA] …"처럼 채널 머리말이 있으면 채널도 맞춥니다.
    const pre = params.get('topic');
    if (pre && form) {
      const [tag, rest] = splitTag(pre);
      const t = form.querySelector('[name="title"]');
      if (sel && [...sel.options].some(o => o.value === tag)) { sel.value = tag; if (t && !t.value) t.value = rest.slice(0, 100); }
      else if (t && !t.value) t.value = pre.slice(0, 100);
    }
    load();
  }

  /* ── QUICK TALK: 한 줄 평 ── */
  const quick = $('[data-quick]');
  if (quick && SB.url) {
    const qList = $('[data-quick-list]', quick), qForm = $('[data-quick-form]', quick), qStatus = $('[data-quick-status]', quick);
    const qSize = Number(quick.dataset.size || 4);
    let qBusy = false;
    const qLoad = async () => {
      try {
        const res = await request('/rest/v1/posts?select=id,title,nickname,created_at&status=eq.published&order=created_at.desc&title=' + likeTag(QUICK), {
          headers: { 'Range-Unit': 'items', Range: `0-${qSize - 1}` } });
        const rows = await res.json();
        qList.replaceChildren();
        if (!rows.length) { qList.append(el('div', 'empty', '첫 한 줄 평을 남겨보세요.')); return; }
        rows.forEach(p => {
          const row = el('div', 'quick-row');
          row.append(el('span', 'quick-text', splitTag(p.title)[1]), el('span', 'quick-meta', `${p.nickname || 'ANON'} · ${fmtTime(p.created_at)}`));
          qList.append(row);
        });
      } catch (_) { qList.replaceChildren(el('div', 'empty', '한 줄 평을 불러오지 못했습니다.')); }
    };
    qForm?.addEventListener('submit', async e => {
      e.preventDefault();
      if (qBusy) return;
      const fd = new FormData(qForm);
      if (String(fd.get('website') || '').trim()) return;
      const text = String(fd.get('text') || '').trim().replace(/\s+/g, ' ').slice(0, 60);
      if (text.length < 2) { qStatus.textContent = '2자 이상 적어 주세요.'; return; }
      if (throttled()) { qStatus.textContent = '연속 등록 방지를 위해 잠시 후 다시 작성해 주세요.'; return; }
      qBusy = true; qStatus.textContent = '등록 중입니다…';
      const btn = qForm.querySelector('button'); if (btn) btn.disabled = true;
      try { await sendPost('ANON', `[${QUICK}] ${text}`, text); stamp(); qForm.reset(); qStatus.textContent = '등록되었습니다.'; await qLoad(); }
      catch (err) { qStatus.textContent = postError(err); }
      finally { qBusy = false; if (btn) btn.disabled = false; }
    });
    qLoad();
  }

  /* ── 홈의 "SFANDOM과 대화하기" 쪽지 칸: 문의 페이지와 같은 쪽지함으로 전송 ── */
  const mf = $('[data-message]');
  if (mf && mf.dataset.endpoint) {
    const mStatus = $('[data-message-status]', mf), mBtn = $('button[type=submit]', mf), mOpened = Date.now();
    const mSay = (t, bad) => { mStatus.textContent = t; mStatus.style.color = bad ? 'var(--red)' : ''; };
    mf.addEventListener('submit', async e => {
      e.preventDefault();
      const fd = new FormData(mf), v = k => String(fd.get(k) || '').trim();
      if (v('website')) return;
      if (Date.now() - mOpened < 4000) return mSay('잠시 뒤에 다시 눌러 주세요.', true);
      if (v('body').length < 5) return mSay('내용을 조금 더 적어 주세요.', true);
      if (v('reply') && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v('reply'))) return mSay('이메일 주소 형식을 확인해 주세요.', true);
      mBtn.disabled = true; mSay('보내는 중입니다…');
      try {
        await fetch(mf.dataset.endpoint, { method: 'POST', mode: 'no-cors',
          body: new URLSearchParams({ nick: v('name').slice(0, 40), email: v('reply').slice(0, 120), message: ('[홈 쪽지] ' + v('body')).slice(0, 1000), website: '', page: location.pathname }) });
        mf.reset(); mSay('쪽지가 전달됐습니다. 확인 후 필요한 경우 회신드리겠습니다.');
      } catch (err) { mSay('전송하지 못했습니다. 잠시 뒤 다시 시도해 주세요.', true); }
      finally { mBtn.disabled = false; }
    });
  }

  /* ── 검색 ── */
  const results = $('[data-search-results]');
  if (results) {
    const q = (new URLSearchParams(location.search).get('q') || '').trim();
    const input = $('#searchPageInput'); if (input) input.value = q;
    const count = $('[data-search-count]');
    if (!q) { if (count) count.textContent = '검색어를 입력해 주세요.'; return; }
    fetch(CFG.root + 'search-index.json', { cache: 'no-cache' }).then(r => r.json()).then(items => {
      const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
      const hits = items.map(it => {
        const hay = (it.t + ' ' + it.s + ' ' + it.k + ' ' + it.x).toLowerCase();
        const score = terms.reduce((n, w) => n + (hay.includes(w) ? (it.t.toLowerCase().includes(w) ? 3 : 1) : -99), 0);
        return { it, score };
      }).filter(h => h.score > 0).sort((a, b) => b.score - a.score || (a.it.d < b.it.d ? 1 : -1));
      if (count) count.textContent = `“${q}” 검색 결과 ${hits.length}건`;
      results.replaceChildren();
      hits.slice(0, 50).forEach(({ it }) => {
        const a = el('a', 'li'); a.href = it.u;
        const box = el('div');
        box.append(el('span', 'tag red', `${it.k} · ${it.d}`), el('h2', null, it.t), el('p', null, it.x));
        a.append(el('div'), box);
        a.style.gridTemplateColumns = '1fr';
        a.firstChild.remove();
        results.append(a);
      });
      if (!hits.length) results.append(el('div', 'empty', '검색 결과가 없습니다. 다른 단어로 찾아보세요.'));
    }).catch(() => { if (count) count.textContent = '검색을 불러오지 못했습니다.'; });
  }
})();
