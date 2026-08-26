(()=>{
  const originalQuerySelector=Document.prototype.querySelector;
  let blockNextMatchSwap=true;

  Document.prototype.querySelector=function(selector){
    if(blockNextMatchSwap && selector==='.daily-feature-shell') return null;
    return originalQuerySelector.call(this,selector);
  };

  const applyPublicHitRate=()=>{
    const card=document.querySelector('.forecast-card');
    if(card){
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
    }
  };

  const renderCurrentPicks=()=>{
    const section=document.querySelector('section[aria-labelledby="pick-result-title"]');
    if(!section)return;

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

      <div style="overflow:hidden;border:1px solid #2d3239;background:#07090d;box-shadow:0 22px 70px rgba(0,0,0,.32);">
        <img src="/assets/picks/sfandom-best2-20260826.svg?v=20260826-1608" alt="SFANDOM 2026년 8월 26일 베스트 2픽 LG NC 오버 8.5, 안양 인천 양득 YES" loading="eager" decoding="async" style="display:block;width:100%;height:auto;">
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;margin-top:20px;">
        <article style="padding:24px;border:1px solid #343a43;background:linear-gradient(145deg,#10151d,#08090c 72%);">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;"><span style="padding:7px 9px;border:1px solid #66323a;background:#18090c;color:#ff747a;font-size:.62rem;font-weight:900;letter-spacing:.12em;">01 · KBO · 18:30 KST</span><b style="color:#ef2d2d;font-size:.78rem;letter-spacing:.08em;">OVERSEAS LINE</b></div>
          <h3 style="margin:22px 0 5px;font-size:clamp(1.8rem,3vw,2.8rem);letter-spacing:-.045em;">LG · NC</h3>
          <strong style="display:block;margin:8px 0 18px;color:#fff;font-size:clamp(2.2rem,4.5vw,4rem);line-height:.95;letter-spacing:-.055em;">OVER <span style="color:#ef2d2d;">8.5</span></strong>
          <p style="margin:0;color:#b6bac2;line-height:1.75;">25일 맞대결은 연장 끝 <b style="color:#fff;">LG 5–4 NC</b>. 8회 이후 득점 흐름이 크게 열렸고, 승패보다 해외 기준 <b style="color:#fff;">8.5 총점 시장</b>을 선택했습니다.</p>
          <a href="https://www.koreabaseball.com/Schedule/ScoreBoard.aspx" target="_blank" rel="noopener noreferrer" style="display:inline-block;margin-top:16px;color:#8ebcf0;text-decoration:none;font-size:.68rem;font-weight:900;letter-spacing:.08em;">KBO OFFICIAL ↗</a>
        </article>

        <article style="padding:24px;border:1px solid #393345;background:linear-gradient(145deg,#12101a,#08090c 72%);">
          <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;"><span style="padding:7px 9px;border:1px solid #50466e;background:#100d1a;color:#b9a5ff;font-size:.62rem;font-weight:900;letter-spacing:.12em;">02 · K LEAGUE 1 · 19:30 KST</span><b style="color:#b9a5ff;font-size:.78rem;letter-spacing:.08em;">BTTS MARKET</b></div>
          <h3 style="margin:22px 0 5px;font-size:clamp(1.8rem,3vw,2.8rem);letter-spacing:-.045em;">FC안양 · 인천UTD</h3>
          <strong style="display:block;margin:8px 0 18px;color:#fff;font-size:clamp(2.2rem,4.5vw,4rem);line-height:.95;letter-spacing:-.055em;">양득 <span style="color:#ef2d2d;">YES</span></strong>
          <p style="margin:0;color:#b6bac2;line-height:1.75;">현재 K리그1 누적 기준 안양과 인천은 각각 <b style="color:#fff;">30득점</b>. 승패 방향의 변수를 피하고, 두 팀의 득점 경로가 동시에 살아나는 <b style="color:#fff;">BTTS YES</b>로 시장을 바꿨습니다.</p>
          <a href="https://www.kleague.com/schedule.do" target="_blank" rel="noopener noreferrer" style="display:inline-block;margin-top:16px;color:#b9a5ff;text-decoration:none;font-size:.68rem;font-weight:900;letter-spacing:.08em;">K LEAGUE OFFICIAL ↗</a>
        </article>
      </div>

      <div style="display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-top:18px;padding-top:16px;border-top:1px solid #222;">
        <span style="color:#777;font-size:.64rem;font-weight:800;letter-spacing:.08em;">분석 콘텐츠용 · 결과 보장 아님</span>
        <a href="archive/picks/" aria-label="SFANDOM and KAIRO picks archive" style="display:inline-flex;align-items:center;justify-content:center;min-width:190px;height:40px;padding:0 16px;border:1px solid #393939;background:#0b0b0c;color:#fff;text-decoration:none;font-size:.72rem;font-weight:900;letter-spacing:.08em;">이전 픽 보관함 →</a>
      </div>`;
  };

  const script=document.createElement('script');
  script.src='/site-base.js?v=20260826-next-match-stability1';
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
    requestAnimationFrame(()=>applyAll());
    setTimeout(applyAll,120);
    setTimeout(applyAll,600);
  },{once:true});
  script.addEventListener('error',()=>{
    restore();
    applyAll();
    console.warn('[SFANDOM] site enhancer loader failed');
  },{once:true});

  document.head.appendChild(script);
  applyAll();
})();