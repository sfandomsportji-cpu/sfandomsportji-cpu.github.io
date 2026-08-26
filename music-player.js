/* SFANDOM recovery guard · 2026-08-27
   Music UI is retired. Keep homepage behavior static and predictable:
   - no prototype monkey-patching
   - no MutationObserver loops
   - no runtime site-base injection
   - restore the approved local hero reel
   - keep the retired current-pick section hidden until the next pick is published
*/
(()=>{
  const init=()=>{
    if(!document.getElementById('sfRecoveryGuard')){
      const style=document.createElement('style');
      style.id='sfRecoveryGuard';
      style.textContent='section[aria-labelledby="pick-result-title"]{display:none!important}.hero-reel-safe-logo{display:none!important}';
      document.head.appendChild(style);
    }

    const wrap=document.querySelector('.hero-reel-wrap');
    if(!wrap) return;

    wrap.querySelectorAll('.hero-reel-safe-logo').forEach(el=>el.remove());

    let video=wrap.querySelector('video.hero-reel');
    if(!video){
      const current=wrap.querySelector('.hero-reel');
      video=document.createElement('video');
      video.className='hero-reel';
      video.src='assets/sfandom-hero-reel.mp4?v=20260822-0451';
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

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',init,{once:true});
  }else{
    init();
  }
})();
