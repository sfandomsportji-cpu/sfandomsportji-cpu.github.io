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

/* 2026-08-26 mobile next-match rescue v2: remove dead space and ID-photo boxes. */
(()=>{
  const old=document.getElementById('sfMobileMatchupRescue');
  if(old) old.remove();

  const style=document.createElement('style');
  style.id='sfMobileMatchupRescue';
  style.textContent=`
@media (max-width:700px){
  body.home-v2 .daily-read{padding-top:30px!important;padding-bottom:40px!important}
  body.home-v2 .daily-feature-head{padding:16px 16px 15px!important;gap:10px!important}
  body.home-v2 .daily-feature-head .eyebrow{margin:0 0 6px!important;font-size:.58rem!important;letter-spacing:.16em!important}

  body.home-v2 .daily-feature-head h2:before{
    font-size:1.78rem!important;
    line-height:1!important;
    letter-spacing:-.05em!important;
    white-space:nowrap!important;
  }
  body.home-v2 .daily-feature-head h2:after{
    font-size:1.38rem!important;
    line-height:1.08!important;
    letter-spacing:-.055em!important;
    white-space:nowrap!important;
    word-break:keep-all!important;
  }
  body.home-v2 .daily-feature-meta{
    margin-top:2px!important;
    font-size:.58rem!important;
    line-height:1.5!important;
    letter-spacing:.075em!important;
  }

  body.home-v2 .daily-matchup-stage{
    height:318px!important;
    min-height:318px!important;
  }
  body.home-v2 .daily-photo{
    inset:0!important;
    align-items:center!important;
    justify-content:center!important;
  }
  body.home-v2 .daily-photo img{
    width:190%!important;
    max-width:none!important;
    height:100%!important;
    object-fit:cover!important;
    object-position:center 38%!important;
    transform:none!important;
    filter:saturate(.88) contrast(1.05) brightness(.88)!important;
    -webkit-mask-image:linear-gradient(90deg,transparent 0%,rgba(0,0,0,.96) 15%,#000 30%,#000 70%,rgba(0,0,0,.96) 85%,transparent 100%)!important;
    mask-image:linear-gradient(90deg,transparent 0%,rgba(0,0,0,.96) 15%,#000 30%,#000 70%,rgba(0,0,0,.96) 85%,transparent 100%)!important;
  }
  body.home-v2 .daily-photo:after{
    background:
      linear-gradient(90deg,rgba(6,6,6,.36) 0%,transparent 18%,transparent 82%,rgba(6,6,6,.36) 100%),
      linear-gradient(180deg,rgba(5,5,5,.03) 0%,rgba(5,5,5,.03) 47%,rgba(5,5,5,.48) 66%,rgba(5,5,5,.9) 84%,#070707 100%)!important;
  }

  body.home-v2 .daily-player-info{
    padding:11px 10px 12px!important;
    background:linear-gradient(180deg,rgba(7,7,7,0),rgba(7,7,7,.56) 18%,#070707 68%)!important;
  }
  body.home-v2 .daily-team-label{
    max-width:130px!important;
    margin-bottom:4px!important;
    font-size:.47rem!important;
    letter-spacing:.08em!important;
  }
  body.home-v2 .daily-player-info h3{
    margin:0 0 7px!important;
    font-size:1.02rem!important;
    line-height:.94!important;
    letter-spacing:-.045em!important;
  }
  body.home-v2 .daily-stat-row{gap:4px!important;flex-wrap:nowrap!important}
  body.home-v2 .daily-stat-row span{
    min-width:0!important;
    flex:1 1 0!important;
    padding:5px 5px!important;
    font-size:.42rem!important;
  }
  body.home-v2 .daily-stat-row strong{font-size:.7rem!important}
  body.home-v2 .daily-stat-row span:nth-child(3){display:none!important}

  body.home-v2 .daily-matchup-center{
    top:50%!important;
    width:54px!important;
    height:54px!important;
    border-color:#3a3a3a!important;
  }
  body.home-v2 .daily-matchup-center strong{font-size:.66rem!important}
  body.home-v2 .daily-matchup-center span{margin:2px 0!important;font-size:.4rem!important}

  body.home-v2 .daily-verdict-wide{padding:15px 16px 16px!important}
  body.home-v2 .daily-verdict-wide small{margin-bottom:5px!important;font-size:.52rem!important}
  body.home-v2 .daily-verdict-wide p:after{font-size:.72rem!important;line-height:1.58!important}
  body.home-v2 .daily-source{padding:9px 16px!important;font-size:.5rem!important}
}
`;
  document.head.appendChild(style);
})();
