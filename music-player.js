/* SFANDOM stable hero fallback · 2026-08-27
   Music UI is retired. This file has one job only: keep the approved local
   hero reel active when the homepage still contains an older embed node. */
(()=>{
  const init=()=>{
    const wrap=document.querySelector('.hero-reel-wrap');
    if(!wrap) return;

    wrap.querySelectorAll('.hero-reel-safe-logo').forEach(el=>el.remove());

    let video=wrap.querySelector('video.hero-reel');
    if(!video){
      const current=wrap.querySelector('.hero-reel');
      video=document.createElement('video');
      video.className='hero-reel';
      video.src='assets/sfandom-hero-reel.mp4?v=20260827-stable1';
      video.autoplay=true;
      video.defaultMuted=true;
      video.muted=true;
      video.loop=true;
      video.playsInline=true;
      video.preload='metadata';
      video.setAttribute('muted','');
      video.setAttribute('playsinline','');
      video.setAttribute('aria-hidden','true');
      if(current) current.replaceWith(video); else wrap.prepend(video);
    }else{
      video.autoplay=true;
      video.defaultMuted=true;
      video.muted=true;
      video.loop=true;
      video.playsInline=true;
      video.setAttribute('muted','');
      video.setAttribute('playsinline','');
    }
    video.play().catch(()=>{});
  };

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
