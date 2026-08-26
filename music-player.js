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
