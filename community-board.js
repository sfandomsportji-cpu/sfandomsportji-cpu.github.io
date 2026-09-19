(() => {
  'use strict';

  const root = document.getElementById('sfCommunityLobby');
  if (!root) return;

  const list = document.getElementById('sfCommunityList');
  const pager = document.getElementById('sfCommunityPagination');
  const form = document.getElementById('sfCommunityTester');
  const status = document.getElementById('sfCommunityTesterStatus');
  const PAGE_SIZE = 10;

  let page = 1;
  let localPosts = [];

  const channels = ['HOT TALK', 'MATCH CHAT', 'FAN PICKS'];
  const demoTitles = [
    '애틀랜타, 포스트시즌에서 가장 먼저 점검할 데이터는?',
    '다저스 8회 4홈런, 타선 흐름은 얼마나 달라졌을까?',
    '선발 매치업에서 경기 초반 가장 먼저 볼 지표는?',
    '불펜 교체 타이밍, 승부 흐름을 바꾼 결정적 기준은?',
    '1점 차 승부에서 득점권 타석의 가치가 더 커지는 이유',
    '경기 후반 수비 포지셔닝이 실점 기대값에 미치는 영향',
    '장타보다 출루가 중요한 이닝은 언제일까?',
    '홈과 원정 타격 지표, 실제 경기력 차이는 얼마나 날까?',
    '선발 투수 구속 변화에서 가장 먼저 확인할 신호는?',
    '오늘 경기에서 팬들이 가장 오래 기억할 장면은 무엇일까?'
  ];

  const demo = Array.from({ length: 10 }, (_, i) => ({
    post_id: 'DEMO-' + String(23 - i).padStart(3, '0'),
    created_at_kst:
      '2026-09-' +
      String(19 - Math.floor(i / 8)).padStart(2, '0') +
      ' ' +
      String(2 + (i % 8)).padStart(2, '0') +
      ':' +
      String((i * 7) % 60).padStart(2, '0'),
    channel: channels[i % channels.length],
    nickname: ['KAIRO', 'TESTER', 'SFANDOM'][i % 3],
    title: demoTitles[i],
    comment_count: (i * 3) % 19
  }));

  const text = (tag, value, className) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    el.textContent = value ?? '';
    return el;
  };

  const formatTime = raw => {
    const value = String(raw || '');
    return value.length >= 16 ? value.slice(5, 16) : value;
  };

  const sourcePosts = () => (localPosts.length ? localPosts : demo);

  const renderRows = rows => {
    list.replaceChildren();

    if (!rows.length) {
      list.append(text('div', '아직 게시글이 없습니다.', 'community-empty'));
      return;
    }

    rows.forEach(post => {
      const row = document.createElement('article');
      row.className = 'community-row';

      row.append(
        text('span', post.post_id.replace(/^.*-/, ''), 'community-row-num'),
        text('span', post.channel || 'HOT TALK', 'community-row-channel')
      );

      const main = document.createElement('div');
      main.className = 'community-row-main';
      main.append(
        text('strong', post.title || '(제목 없음)', 'community-row-title'),
        text('small', post.nickname || 'ANON', 'community-row-meta')
      );

      row.append(
        main,
        text('time', formatTime(post.created_at_kst), 'community-row-time'),
        text('span', String(post.comment_count || 0), 'community-row-comments')
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
        page = target;
        render();
      });
      pager.append(button);
    };

    make('‹', Math.max(1, page - 1), page === 1);

    const start = Math.max(1, Math.min(page - 2, pages - 4));
    const end = Math.min(pages, start + 4);
    for (let p = start; p <= end; p += 1) {
      make(String(p), p, false, p === page);
    }

    make('›', Math.min(pages, page + 1), page === pages);
  };

  const render = () => {
    const posts = sourcePosts();
    const start = (page - 1) * PAGE_SIZE;
    renderRows(posts.slice(start, start + PAGE_SIZE));
    renderPager(posts.length);
  };

  form?.addEventListener('submit', event => {
    event.preventDefault();

    const formData = new FormData(form);
    if (String(formData.get('website') || '').trim()) return;

    const nickname = String(formData.get('nickname') || '').trim().slice(0, 30);
    const title = String(formData.get('title') || '').trim().slice(0, 120);
    const body = String(formData.get('body') || '').trim().slice(0, 2000);

    if (title.length < 2 || body.length < 2) {
      status.textContent = '제목과 내용을 2자 이상 입력해 주세요.';
      return;
    }

    if (!localPosts.length) localPosts = [...demo];

    localPosts.unshift({
      post_id: 'LOCAL-' + Date.now(),
      created_at_kst: new Intl.DateTimeFormat('sv-SE', {
        timeZone: 'Asia/Seoul',
        dateStyle: 'short',
        timeStyle: 'short'
      }).format(new Date()),
      channel: 'HOT TALK',
      nickname: nickname || 'ANON',
      title,
      body,
      comment_count: 0
    });

    form.reset();
    page = 1;
    render();
    status.textContent = '프리뷰 글이 추가되었습니다. 새로고침하면 초기화됩니다.';
  });

  render();
})();
