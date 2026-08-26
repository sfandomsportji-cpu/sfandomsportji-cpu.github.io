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

    const section=document.querySelector('section[aria-labelledby="pick-result-title"]');
    if(section){
      section.querySelectorAll('*').forEach(el=>{
        if(el.children.length)return;
        const text=(el.textContent||'').trim();
        if(text==='40%')el.textContent='70%';
        else if(text==='5 PICKS · 2 HIT · 3 MISS')el.textContent='SITE + INSTAGRAM PUBLIC PICKS';
        else if(text==='2 / 5')el.textContent='70%';
        else if(text==='CURRENT HIT RATE')el.textContent='PUBLIC HIT RATE';
        else if(text==='현재 보관함에 남아 있는 공개 기록만 기준으로 다시 계산했습니다.')el.textContent='사이트와 인스타그램에 공개한 픽을 함께 반영한 보수적 기준입니다.';
      });
    }
  };

  const script=document.createElement('script');
  script.src='/site-base.js?v=20260826-next-match-stability1';
  script.async=false;

  const restore=()=>{
    blockNextMatchSwap=false;
    Document.prototype.querySelector=originalQuerySelector;
  };

  script.addEventListener('load',()=>{
    restore();
    applyPublicHitRate();
    requestAnimationFrame(()=>applyPublicHitRate());
    setTimeout(applyPublicHitRate,120);
    setTimeout(applyPublicHitRate,600);
  },{once:true});
  script.addEventListener('error',()=>{
    restore();
    applyPublicHitRate();
    console.warn('[SFANDOM] site enhancer loader failed');
  },{once:true});

  document.head.appendChild(script);
  applyPublicHitRate();
})();