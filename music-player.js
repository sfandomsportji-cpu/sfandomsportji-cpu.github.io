(()=>{
  const originalQuerySelector=Document.prototype.querySelector;
  let blockNextMatchSwap=true;

  Document.prototype.querySelector=function(selector){
    if(blockNextMatchSwap && selector==='.daily-feature-shell') return null;
    return originalQuerySelector.call(this,selector);
  };

  /* Stop the retired anonymous-note loader from adding a second pick board. */
  if(!document.querySelector('script[data-sf-anonymous-note]')){
    const sentinel=document.createElement('script');
    sentinel.dataset.sfAnonymousNote='disabled';
    sentinel.type='application/json';
    sentinel.textContent='{}';
    document.head.appendChild(sentinel);
  }

  const LOGO={
    LG:'https://6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/emblem/regular/fixed/emblem_LG.png',
    NC:'https://6ptotvmi5753.edge.naverncp.com/KBO_IMAGE/emblem/regular/fixed/emblem_NC.png',
    ANYANG:'https://www.kleague.com/assets/images/emblem/emblem_K27.png',
    INCHEON:'https://www.kleague.com/assets/images/emblem/emblem_K18.png'
  };

  const applyPublicHitRate=()=>{
    const card=document.querySelector('.forecast-card');
    if(!card)return;
    const kicker=card.querySelector('.card-kicker span');
    const badge=card.querySelector('.card-kicker b');
    const label=card.querySelector('.forecast-score span');
    const score=card.querySelector('.forecast-score strong');
    const bar=card.querySelector('.signal i');
    if(kicker)kicker.textContent='SFANDOM PUBLIC PICKS';
    if(badge)badge.textContent='UPDATED';
    if(label)label.textContent='PICK HIT RATE';
    if(score)score.innerHTML='70<small>%</small>';
    if(bar)bar.style.width='70%';
  };

  const ensurePickStyle=()=>{
    if(document.getElementById('sfTodayPickStyle'))return;
    const style=document.createElement('style');
    style.id='sfTodayPickStyle';
    style.textContent=`
      .sf-today-board{display:grid;gap:18px;padding:20px;border:1px solid #2d3239;background:linear-gradient(135deg,#071019 0%,#05070b 58%,#09070d 100%);box-shadow:0 22px 70px rgba(0,0,0,.32)}
      .sf-today-row{position:relative;overflow:hidden;display:grid;grid-template-columns:minmax(470px,1.14fr) minmax(285px,.82fr) 170px;gap:24px;align-items:center;min-height:184px;padding:24px 26px;border:1px solid #303641;border-radius:18px;background:linear-gradient(135deg,#0d151e,#090a0f 74%)}
      .sf-today-row:before{content:'';position:absolute;left:0;top:0;bottom:0;width:9px;background:#ef2d2d}
      .sf-today-row.football{background:linear-gradient(135deg,#12101b,#090a0f 74%);border-color:#393347}
      .sf-today-row.football:before{background:#7e2fd1}
      .sf-matchup{min-width:0;display:grid;grid-template-columns:minmax(0,1fr) 34px minmax(0,1fr);gap:12px;align-items:center;padding-right:22px;border-right:1px solid #303641}
      .sf-team{min-width:0;display:grid;grid-template-columns:82px minmax(0,1fr);gap:12px;align-items:center}
      .sf-team.away{grid-template-columns:minmax(0,1fr) 82px;text-align:right}
      .sf-logo{display:grid;place-items:center;width:82px;height:82px;overflow:hidden}
      .sf-logo img{display:block;max-width:82px;max-height:82px;width:auto;height:auto;object-fit:contain;filter:drop-shadow(0 8px 16px rgba(0,0,0,.32))}
      .sf-team-name{min-width:0}
      .sf-team-name small{display:block;margin-bottom:7px;color:#858c97;font:900 .57rem/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:.1em;white-space:nowrap}
      .sf-team-name strong{display:block;color:#fff;font:900 clamp(1.05rem,1.8vw,1.45rem)/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:-.035em;white-space:normal;word-break:keep-all}
      .sf-versus{color:#666d78;font:900 .72rem/1 Inter,sans-serif;text-align:center}
      .sf-match-meta{grid-column:1/-1;margin-top:2px;padding-left:94px;color:#949aa5;font:800 .72rem/1.3 Inter,'Noto Sans KR',sans-serif;letter-spacing:.03em}
      .sf-today-row.football .sf-match-meta{padding-left:94px}
      .sf-market small{display:block;margin-bottom:12px;color:#ef2d2d;font:900 .68rem/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:.08em}
      .sf-today-row.football .sf-market small{color:#b49cff}
      .sf-market strong{display:block;color:#fff;font:900 clamp(2.15rem,4vw,3.6rem)/.95 Inter,'Noto Sans KR',sans-serif;letter-spacing:-.055em;white-space:nowrap}
      .sf-market strong b{color:#ef2d2d}
      .sf-market p{margin:12px 0 0;color:#9fa5ae;font:700 .72rem/1.45 Inter,'Noto Sans KR',sans-serif}
      .sf-read{align-self:stretch;display:flex;flex-direction:column;justify-content:center;padding:15px 16px;border:1px solid #2c323b;border-radius:14px;background:#07090c}
      .sf-read small{color:#8e95a0;font:900 .58rem/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:.11em}
      .sf-read strong{margin:10px 0;color:#fff;font:900 .88rem/1.12 Inter,'Noto Sans KR',sans-serif}
      .sf-read span{color:#c3c6cc;font:700 .64rem/1.55 Inter,'Noto Sans KR',sans-serif}
      .sf-read b{margin-top:8px;color:#ef2d2d;font:900 .66rem/1 Inter,'Noto Sans KR',sans-serif}
      .sf-pick-footer{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-top:18px;padding-top:16px;border-top:1px solid #222}
      @media(max-width:1080px){.sf-today-row{grid-template-columns:1fr 1fr}.sf-matchup{grid-column:1/-1;border-right:0;border-bottom:1px solid #303641;padding:0 0 20px}.sf-read{min-height:100px}}
      @media(max-width:720px){.sf-today-board{padding:12px}.sf-today-row{grid-template-columns:1fr;gap:18px;padding:20px 16px;min-height:0}.sf-matchup{grid-template-columns:1fr 28px 1fr;gap:8px}.sf-team,.sf-team.away{grid-template-columns:1fr;text-align:center;gap:8px}.sf-team.away .sf-logo{order:0}.sf-team.away .sf-team-name{order:1}.sf-logo{width:68px;height:68px;margin:auto}.sf-logo img{max-width:68px;max-height:68px}.sf-team-name small{font-size:.5rem}.sf-team-name strong{font-size:1rem}.sf-match-meta{padding-left:0!important;text-align:center}.sf-market strong{font-size:2.55rem}.sf-read{min-height:0}}
    `;
    document.head.appendChild(style);
  };

  const team=(name,sub,logo,away=false)=>`
    <div class="sf-team${away?' away':''}">
      ${away?`<div class="sf-team-name"><small>${sub}</small><strong>${name}</strong></div><div class="sf-logo"><img src="${logo}" alt="${name} team logo" loading="eager" decoding="async"></div>`:`<div class="sf-logo"><img src="${logo}" alt="${name} team logo" loading="eager" decoding="async"></div><div class="sf-team-name"><small>${sub}</small><strong>${name}</strong></div>`}
    </div>`;

  const renderCurrentPicks=()=>{
    const section=document.querySelector('section[aria-labelledby="pick-result-title"]');
    if(!section)return;
    ensurePickStyle();
    section.style.paddingTop='58px';
    section.style.paddingBottom='58px';
    section.innerHTML=`
      <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:28px;flex-wrap:wrap;margin-bottom:26px;">
        <div>
          <p class="eyebrow">SFANDOM & KAIRO · TODAY'S BEST 2 · 2026.08.26 KST</p>
          <h2 id="pick-result-title" style="margin:8px 0 0;font-size:clamp(2rem,4vw,4.2rem);line-height:.96;letter-spacing:-.05em;">전체판에서 남긴,<br><span style="color:#ef2d2d;">오늘의 두 경기.</span></h2>
        </div>
        <p style="max-width:470px;margin:0;color:#a7a7a7;line-height:1.75;">전체 경기판을 비교하고 반대 근거까지 다시 확인한 뒤 시장을 골랐습니다. 경기 직전 선발·라인업·시장 급변이 있으면 최종 판단을 변경할 수 있습니다.</p>
      </div>

      <div class="sf-today-board" data-sf-current-picks="1">
        <article class="sf-today-row">
          <div class="sf-matchup">
            ${team('LG TWINS','HOME · LG',LOGO.LG)}
            <div class="sf-versus">—</div>
            ${team('NC DINOS','AWAY · NC',LOGO.NC,true)}
            <div class="sf-match-meta">18:30 · JAMSIL · KST</div>
          </div>
          <div class="sf-market">
            <small>01 · KBO · OVERSEAS TOTAL LINE</small>
            <strong>OVER <b>8.5</b></strong>
            <p>승패보다 총점 흐름에 집중.</p>
          </div>
          <div class="sf-read">
            <small>SFANDOM READ</small>
            <strong>TOTALS MARKET</strong>
            <span>Avoid side risk<br>Focus on scoring flow</span>
            <b>PICK · O8.5</b>
          </div>
        </article>

        <article class="sf-today-row football">
          <div class="sf-matchup">
            ${team('FC ANYANG','HOME · K LEAGUE 1',LOGO.ANYANG)}
            <div class="sf-versus">—</div>
            ${team('INCHEON UTD','AWAY · K LEAGUE 1',LOGO.INCHEON,true)}
            <div class="sf-match-meta">19:30 · KST</div>
          </div>
          <div class="sf-market">
            <small>02 · K LEAGUE 1 · BOTH TEAMS TO SCORE</small>
            <strong>BTTS <b>YES</b></strong>
            <p>승패 변수 대신 양 팀 득점 경로 선택.</p>
          </div>
          <div class="sf-read">
            <small>SFANDOM READ</small>
            <strong>MARKET SWITCH</strong>
            <span>Avoid 1X2<br>Prefer BTTS route</span>
            <b>PICK · YES</b>
          </div>
        </article>
      </div>

      <div class="sf-pick-footer">
        <span style="color:#777;font-size:.64rem;font-weight:800;letter-spacing:.08em;">분석 콘텐츠용 · 결과 보장 아님</span>
        <a href="archive/picks/" aria-label="SFANDOM and KAIRO picks archive" style="display:inline-flex;align-items:center;justify-content:center;min-width:190px;height:40px;padding:0 16px;border:1px solid #393939;background:#0b0b0c;color:#fff;text-decoration:none;font-size:.72rem;font-weight:900;letter-spacing:.08em;">이전 픽 보관함 →</a>
      </div>`;
  };

  const script=document.createElement('script');
  script.src='/site-base.js?v=20260826-pick-singleboard1';
  script.async=false;

  const restore=()=>{
    blockNextMatchSwap=false;
    Document.prototype.querySelector=originalQuerySelector;
  };

  const applyAll=()=>{
    applyPublicHitRate();
    renderCurrentPicks();
  };

  script.addEventListener('load',()=>{
    restore();
    applyAll();
    requestAnimationFrame(applyAll);
    setTimeout(applyAll,180);
  },{once:true});

  script.addEventListener('error',()=>{
    restore();
    applyAll();
    console.warn('[SFANDOM] site enhancer loader failed');
  },{once:true});

  document.head.appendChild(script);
  applyAll();
})();
