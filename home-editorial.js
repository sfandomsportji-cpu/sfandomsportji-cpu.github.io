(() => {
  'use strict';

  const rail = document.querySelector('.content-zone .content-rail');
  if (!rail || rail.dataset.editorialEnhanced === '1') return;

  const STYLE_ID = 'sf-home-editorial-css';
  if (!document.getElementById(STYLE_ID)) {
    const link = document.createElement('link');
    link.id = STYLE_ID;
    link.rel = 'stylesheet';
    link.href = 'home-editorial.css?v=20260916-v1';
    document.head.appendChild(link);
  }

  const cards = [
    {
      copy: '최근 20경기의 득실점 흐름과 홈·원정 편차, 선발투수의 ERA와 이닝 소화력, 타선의 최근 컨디션, 배당 변화까지 한 화면에서 함께 봅니다. 단순히 숫자를 늘어놓는 대신 어떤 수치가 실제 경기 방향을 만들고 있는지 설명하고, 홈에서는 핵심 근거를 먼저 공개합니다. 상세 분석에서는 라인업과 현지 이슈까지 더해 결론이 만들어지는 과정을 이어서 보여드립니다.',
      data: ['LAST 20', 'STARTER ERA', 'ODDS MOVE']
    },
    {
      copy: '순위표 한 줄이나 속보 제목만 옮기지 않습니다. 부상과 로스터 변동, 연승·연패, 기록 달성, 감독과 선수의 현지 이슈가 팀 분위기와 다음 경기 준비에 어떤 영향을 주는지 함께 봅니다. 중요한 뉴스는 숫자와 경기 맥락을 붙여 설명하고, 다음 경기에서 무엇이 달라질 수 있는지까지 짧고 분명하게 연결합니다.',
      data: ['RANK', 'INJURY', 'TREND']
    },
    {
      copy: '선발, 예상 라인업, 불펜 컨디션, 최근 경기력과 상대 전적을 같은 축에서 비교합니다. 단순 프리뷰가 아니라 실제 승부를 가를 가능성이 높은 포인트를 먼저 추리고, 경기 전 체크할 숫자와 변수를 함께 보여드립니다. 이후 라이브와 영상에서는 경기 장면을 다시 보며 이 사전 판단이 어디서 맞고 달라졌는지 확인합니다.',
      data: ['STARTER', 'LINEUP', 'BULLPEN']
    },
    {
      copy: '결과만 맞고 틀린 것으로 끝내지 않습니다. 선발 구위와 제구, 타격 타이밍, 수비와 불펜 운영, 시장 흐름까지 다시 연결해 왜 그런 경기 양상이 나왔는지 복기합니다. 한 경기의 결과를 다음 분석의 기준으로 남기고, 텍스트 리뷰와 영상 리뷰가 같은 근거를 공유하도록 기록을 계속 쌓아갑니다.',
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
