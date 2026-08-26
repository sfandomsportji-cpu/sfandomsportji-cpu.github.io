(()=>{
  const originalQuerySelector=Document.prototype.querySelector;
  let blockNextMatchSwap=true;

  Document.prototype.querySelector=function(selector){
    if(blockNextMatchSwap && selector==='.daily-feature-shell') return null;
    return originalQuerySelector.call(this,selector);
  };

  /* Hide the retired pick section immediately, before any legacy script can paint it. */
  if(!document.getElementById('sfNoHomePicksStyle')){
    const style=document.createElement('style');
    style.id='sfNoHomePicksStyle';
    style.textContent='section[aria-labelledby="pick-result-title"],.sf-real-pick-board,.sf-today-board,[data-sf-real-board],[data-sf-current-picks]{display:none!important}';
    document.head.appendChild(style);
  }

  /* Prevent site-base.js from loading the old anonymous-note/pick injector. */
  if(!document.querySelector('script[data-sf-anonymous-note]')){
    const sentinel=document.createElement('script');
    sentinel.dataset.sfAnonymousNote='disabled';
    sentinel.type='application/json';
    sentinel.textContent='{}';
    document.head.appendChild(sentinel);
  }

  const removePicks=()=>{
    document.querySelectorAll('section[aria-labelledby="pick-result-title"]').forEach(el=>el.remove());
    document.querySelectorAll('.sf-real-pick-board,.sf-today-board,[data-sf-real-board],[data-sf-current-picks]').forEach(el=>el.remove());
  };

  removePicks();

  const root=document.documentElement;
  const observer=new MutationObserver(removePicks);
  observer.observe(root,{childList:true,subtree:true});

  const script=document.createElement('script');
  script.src='/site-base.js?v=20260826-no-home-picks1';
  script.async=false;

  const restore=()=>{
    blockNextMatchSwap=false;
    Document.prototype.querySelector=originalQuerySelector;
  };

  script.addEventListener('load',()=>{
    restore();
    removePicks();
    requestAnimationFrame(removePicks);
    setTimeout(removePicks,250);
    setTimeout(()=>{removePicks();observer.disconnect();},2000);
  },{once:true});

  script.addEventListener('error',()=>{
    restore();
    removePicks();
    setTimeout(()=>observer.disconnect(),2000);
    console.warn('[SFANDOM] site enhancer loader failed');
  },{once:true});

  document.head.appendChild(script);
})();

/* 2026-08-26: restore the pre-Manchester local hero reel (Tottenham) and remove the extra hero logo. */
(()=>{
  const restoreHeroReel=()=>{
    const wrap=document.querySelector('.hero-reel-wrap');
    if(!wrap) return;

    wrap.querySelectorAll('.hero-reel-safe-logo').forEach(el=>el.remove());

    const current=wrap.querySelector('.hero-reel');
    const isRestored=current && current.tagName==='VIDEO' && (current.currentSrc||current.getAttribute('src')||'').includes('sfandom-hero-reel.mp4');
    if(isRestored){
      current.muted=true;
      current.loop=true;
      current.autoplay=true;
      current.playsInline=true;
      current.play().catch(()=>{});
      return;
    }

    const video=document.createElement('video');
    video.className='hero-reel';
    video.autoplay=true;
    video.muted=true;
    video.loop=true;
    video.playsInline=true;
    video.preload='auto';
    video.setAttribute('aria-hidden','true');
    video.src='assets/sfandom-hero-reel.mp4?v=20260822-0451';

    if(current) current.replaceWith(video);
    else wrap.prepend(video);

    video.play().catch(()=>{});
  };

  restoreHeroReel();
  requestAnimationFrame(restoreHeroReel);
  setTimeout(restoreHeroReel,250);
})();

/* 2026-08-26 mobile rescue: compact headline, full-size portraits, cleaner matchup card. */
(()=>{
  if(document.getElementById('sfMobileMatchupRescue')) return;
  const style=document.createElement('style');
  style.id='sfMobileMatchupRescue';
  style.textContent=`
@media (max-width:520px){
  body.home-v2 .daily-read{padding-top:34px!important;padding-bottom:42px!important}
  body.home-v2 .daily-feature-head{padding:18px 16px 16px!important;gap:12px!important}
  body.home-v2 .daily-feature-head .eyebrow{margin-bottom:6px!important;font-size:.62rem!important}
  body.home-v2 .daily-feature-head h2:before,
  body.home-v2 .daily-feature-head h2:after{
    font-size:1.7rem!important;
    line-height:1.02!important;
    letter-spacing:-.045em!important;
    word-break:keep-all!important;
  }
  body.home-v2 .daily-feature-head h2:after{white-space:nowrap!important}
  body.home-v2 .daily-feature-meta{font-size:.6rem!important;line-height:1.55!important;letter-spacing:.08em!important}

  body.home-v2 .daily-matchup-stage{height:360px!important}
  body.home-v2 .daily-photo{align-items:flex-end!important}
  body.home-v2 .daily-photo img{
    width:auto!important;
    max-width:none!important;
    height:90%!important;
    object-fit:contain!important;
    object-position:center bottom!important;
    transform:none!important;
    -webkit-mask-image:radial-gradient(ellipse 66% 92% at 50% 48%,#000 0%,#000 58%,rgba(0,0,0,.9) 72%,rgba(0,0,0,.45) 86%,transparent 100%)!important;
    mask-image:radial-gradient(ellipse 66% 92% at 50% 48%,#000 0%,#000 58%,rgba(0,0,0,.9) 72%,rgba(0,0,0,.45) 86%,transparent 100%)!important;
  }
  body.home-v2 .daily-photo:after{
    background:linear-gradient(180deg,rgba(5,5,5,.04) 0%,rgba(5,5,5,.02) 42%,rgba(5,5,5,.34) 62%,rgba(5,5,5,.92) 84%,#070707 100%)!important;
  }
  body.home-v2 .daily-player-info{padding:14px 12px 15px!important}
  body.home-v2 .daily-team-label{max-width:135px!important;margin-bottom:5px!important;font-size:.5rem!important;letter-spacing:.1em!important}
  body.home-v2 .daily-player-info h3{margin-bottom:9px!important;font-size:1.13rem!important;line-height:.95!important;letter-spacing:-.04em!important}
  body.home-v2 .daily-stat-row{gap:5px!important}
  body.home-v2 .daily-stat-row span{padding:6px 7px!important;font-size:.45rem!important}
  body.home-v2 .daily-stat-row strong{font-size:.76rem!important}
  body.home-v2 .daily-matchup-center{top:53%!important;width:58px!important;height:58px!important}
  body.home-v2 .daily-matchup-center strong{font-size:.7rem!important}
  body.home-v2 .daily-matchup-center span{margin:3px 0!important;font-size:.42rem!important}

  body.home-v2 .daily-verdict-wide{padding:17px 16px 18px!important}
  body.home-v2 .daily-verdict-wide small{margin-bottom:6px!important;font-size:.55rem!important}
  body.home-v2 .daily-verdict-wide p:after{font-size:.78rem!important;line-height:1.6!important}
  body.home-v2 .daily-source{padding:10px 16px!important;font-size:.53rem!important}
}
`;
  document.head.appendChild(style);
})();
