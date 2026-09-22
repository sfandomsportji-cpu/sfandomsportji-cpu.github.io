(() => {
  'use strict';

  const root = document.getElementById('sfCommunityLobby');
  if (!root) return;

  const list = document.getElementById('sfCommunityList');
  const pager = document.getElementById('sfCommunityPagination');
  const form = document.getElementById('sfCommunityForm');
  const status = document.getElementById('sfCommunityStatus');

  const PAGE_SIZE = 10;
  const API_URL = 'https://yyjjgxzbqvlpatccbpxm.supabase.co';
  const PUBLISHABLE_KEY = 'sb_publishable_ABoOVvaUzGuVPBryIpY02w_tTcdt-Q4';
  const REQUEST_TIMEOUT_MS = 8000;
  const POST_COOLDOWN_MS = 15000;

  let page = 1;
  let totalPosts = 0;
  let loading = false;

  const text = (tag, value, className) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    el.textContent = value ?? '';
    return el;
  };

  const formatTime = raw => {
    if (!raw) return '';
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat('ko-KR', {
      timeZone: 'Asia/Seoul',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    }).format(date);
  };

  const setBusy = busy => {
    loading = busy;
    if (!form) return;
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = busy;
  };

  const request = async (path, options = {}) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(API_URL + path, {
        ...options,
        signal: controller.signal,
        cache: 'no-store',
        credentials: 'omit',
        headers: {
          apikey: PUBLISHABLE_KEY,
          Accept: 'application/json',
          ...(options.headers || {})
        }
      });

      if (!response.ok) {
        const error = new Error('community ' + response.status);
        error.status = response.status;
        throw error;
      }
      return response;
    } finally {
      clearTimeout(timer);
    }
  };

  const renderRows = rows => {
    list.replaceChildren();

    if (!rows.length) {
      list.append(text('div', '아직 게시글이 없습니다. 첫 글을 남겨보세요.', 'community-empty'));
      return;
    }

    rows.forEach((post, index) => {
      const row = document.createElement('article');
      row.className = 'community-row';

      const displayNo = Math.max(1, totalPosts - ((page - 1) * PAGE_SIZE + index));

      row.append(
        text('span', String(displayNo), 'community-row-num'),
        text('span', 'HOT TALK', 'community-row-channel')
      );

      const main = document.createElement('div');
      main.className = 'community-row-main';
      main.append(
        text('strong', post.title || '(제목 없음)', 'community-row-title'),
        text('p', post.body || '', 'community-row-body'),
        text('small', post.nickname || 'ANON', 'community-row-meta')
      );

      row.append(
        main,
        text('time', formatTime(post.created_at), 'community-row-time')
      );

      list.append(row);
    });
  };

  const renderPager = total => {
    pager.replaceChildren();
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    page = Math.min(Math.max(1, page), pages);

    const make = (label, target, disabled, current = false) => {
      const button = text('button', label, 'community-page-btn');
      button.type = 'button';
      button.disabled = disabled;
      if (current) button.setAttribute('aria-current', 'page');

      button.addEventListener('click', () => {
        if (loading || target === page) return;
        page = target;
        loadPosts();
      });

      pager.append(button);
    };

    make('‹', Math.max(1, page - 1), page === 1);

    const start = Math.max(1, Math.min(page - 2, Math.max(1, pages - 4)));
    const end = Math.min(pages, start + 4);

    for (let p = start; p <= end; p += 1) {
      make(String(p), p, false, p === page);
    }

    make('›', Math.min(pages, page + 1), page === pages);
  };

  const showBoardError = () => {
    list.replaceChildren(
      text('div', '게시판 연결이 잠시 원활하지 않습니다. 잠시 후 다시 시도해 주세요.', 'community-empty')
    );
    pager.replaceChildren();
    if (status) status.textContent = '커뮤니티 연결 지연 · 사이트의 다른 기능은 정상 이용할 수 있습니다.';
  };

  const loadPosts = async () => {
    setBusy(true);

    const offset = (page - 1) * PAGE_SIZE;
    const end = offset + PAGE_SIZE - 1;
    const query = '/rest/v1/posts?select=id,title,body,nickname,created_at&status=eq.published&order=created_at.desc';

    try {
      const response = await request(query, {
        method: 'GET',
        headers: {
          Prefer: 'count=exact',
          'Range-Unit': 'items',
          Range: offset + '-' + end
        }
      });

      const rows = await response.json();
      const contentRange = response.headers.get('content-range') || '';
      const match = contentRange.match(/\/(\d+)$/);
      totalPosts = match ? Number(match[1]) : rows.length;

      renderRows(rows);
      renderPager(totalPosts);
      if (status) status.textContent = '최신 게시글 · 10 POSTS / PAGE';
    } catch (_) {
      showBoardError();
    } finally {
      setBusy(false);
    }
  };

  const recentPostBlocked = () => {
    try {
      const last = Number(localStorage.getItem('sfandom_community_last_post_at') || 0);
      return Date.now() - last < POST_COOLDOWN_MS;
    } catch (_) {
      return false;
    }
  };

  const markPosted = () => {
    try {
      localStorage.setItem('sfandom_community_last_post_at', String(Date.now()));
    } catch (_) {}
  };

  form?.addEventListener('submit', async event => {
    event.preventDefault();
    if (loading) return;

    const formData = new FormData(form);
    if (String(formData.get('website') || '').trim()) return;

    const nickname = String(formData.get('nickname') || '').trim().slice(0, 30) || 'ANON';
    const title = String(formData.get('title') || '').trim().slice(0, 120);
    const body = String(formData.get('body') || '').trim().slice(0, 2000);

    if (title.length < 2 || body.length < 2) {
      status.textContent = '제목과 내용을 2자 이상 입력해 주세요.';
      return;
    }

    if (recentPostBlocked()) {
      status.textContent = '연속 등록 방지를 위해 잠시 후 다시 작성해 주세요.';
      return;
    }

    setBusy(true);
    status.textContent = '게시 중입니다…';

    try {
      await request('/functions/v1/community-post', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          nickname,
          title,
          body
        })
      });

      markPosted();
      form.reset();
      page = 1;
      status.textContent = '게시되었습니다.';
      await loadPosts();
    } catch (error) {
      status.textContent = error?.status === 429
        ? '연속 등록 방지를 위해 잠시 후 다시 작성해 주세요.'
        : '게시하지 못했습니다. 잠시 후 다시 시도해 주세요.';
    } finally {
      setBusy(false);
    }
  });

  loadPosts();
})();
