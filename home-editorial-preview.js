(() => {
  'use strict';

  const rail = document.querySelector('.content-zone .content-rail');
  if (!rail || rail.dataset.editorialEnhanced === '1') return;

  const STYLE_ID = 'sf-home-editorial-preview-css';
  if (!document.getElementById(STYLE_ID)) {
    const link = document.createElement('link');
    link.id = STYLE_ID;
    link.rel = 'stylesheet';
    link.href = 'home-editorial-preview.css?v=20260915-1';
    document.head.appendChild(link);
  }

  const cards = [
    {
      copy: '최근 20경기 흐름, 선발 ERA, 득실점과 홈·원정 편차, 배당 움직임을 한 화면에서 압축합니다. 결론만 던지지 않고 어떤 숫자가 경기 방향을 만들고 있는지 먼저 보여드립니다. 홈에서는 핵심 수치만 맛보기로 공개하고, 상세 분석과 향후 영상 브리핑에서 맥락을 확장합니다.',
      data: ['LAST 20', 'STARTER ERA', 'ODDS MOVE']
    },
    {
      copy: '큰 뉴스만 모으지 않습니다. 순위 변화, 부상과 로스터 이슈, 기록 달성, 팀 분위기가 다음 경기와 시즌 흐름에 어떤 영향을 주는지 핵심 숫자와 함께 짚습니다. 단순 속보가 아니라 ‘그래서 다음 경기에 무엇이 달라지는가’까지 연결해 읽을 거리를 남깁니다.',
      data: ['RANK', 'INJURY', 'TREND']
    },
    {
      copy: '선발, 예상 라인업, 불펜 컨디션, 최근 경기력과 상대 전적을 같은 축에서 비교합니다. 경기 시작 전 실제로 봐야 할 승부 포인트를 짧고 선명하게 정리합니다. 향후 라이브와 영상에서는 이 포인트를 실제 경기 장면과 함께 다시 확인할 수 있게 확장합니다.',
      data: ['STARTER', 'LINEUP', 'BULLPEN']
    },
    {
      copy: '결과만 맞고 틀린 것으로 끝내지 않습니다. 선발 구위, 타격 타이밍, 수비와 불펜, 시장 흐름을 다시 연결해 왜 그런 경기가 나왔는지 다음 분석의 기준으로 남깁니다. 텍스트 복기와 영상 리뷰가 같은 기준을 공유하도록 쌓아, 다음 경기에서 다시 확인할 수 있게 만듭니다.',
      data: ['RESULT', 'GAME FLOW', 'REVIEW']
    }
  ];

  const anchors = [...rail.querySelectorAll(':scope > a')];
  anchors.slice(0, cards.length).forEach((anchor, index) => {
    const config = cards[index];
    const type = anchor.querySelector(':scope > span');
    if (type) type.classList.add('content-card-type');

    const copy = document.createElement('p');
    copy.className = 'content-card-copy';
    copy.textContent = config.copy;

    const data = document.createElement('div');
    data.className = 'content-card-data';
    config.data.forEach((label) => {
      const chip = document.createElement('em');
      chip.textContent = label;
      data.appendChild(chip);
    });

    if (type) {
      anchor.insertBefore(copy, type);
      anchor.insertBefore(data, type);
    } else {
      anchor.append(copy, data);
    }
  });

  rail.dataset.editorialEnhanced = '1';
})();
