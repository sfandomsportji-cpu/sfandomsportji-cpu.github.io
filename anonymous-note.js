(()=>{
  /* Anonymous note trigger intentionally retired. Keep this file as a lightweight
     homepage repair layer because site-base.js still loads it. */
  document.getElementById('sfAnonymousNoteButton')?.remove();
  document.querySelector('.sf-note-modal')?.remove();
  document.querySelectorAll('style[data-sf-transient="anonymous-note"]').forEach(el=>el.remove());

  if(document.getElementById('sfPickRepairStyle'))return;

  const style=document.createElement('style');
  style.id='sfPickRepairStyle';
  style.textContent=`
    /* 2026-08-26 emergency pick-board repair: keep only the main visual board. */
    body.home-v2 section[aria-labelledby="pick-result-title"] > div:nth-of-type(3){
      display:none!important;
    }
    body.home-v2 section[aria-labelledby="pick-result-title"] > div:nth-of-type(2) > img{
      content:url('/assets/picks/sfandom-best2-20260826-fixed.svg?v=20260826-1808')!important;
      display:block!important;
      width:100%!important;
      height:auto!important;
    }
    body.home-v2 section[aria-labelledby="pick-result-title"] > div:last-child{
      margin-top:16px!important;
    }
  `;
  document.head.appendChild(style);

  const repair=()=>{
    document.getElementById('sfAnonymousNoteButton')?.remove();
    const section=document.querySelector('section[aria-labelledby="pick-result-title"]');
    if(!section)return;
    const direct=[...section.children].filter(el=>el.tagName==='DIV');
    const visual=direct.find(el=>el.querySelector('img[src*="sfandom-best2-20260826"]'));
    const img=visual?.querySelector('img');
    if(img){
      img.src='/assets/picks/sfandom-best2-20260826-fixed.svg?v=20260826-1808';
      img.alt='SFANDOM 2026년 8월 26일 베스트 2픽 · LG Twins vs NC Dinos 오버 8.5 · FC Anyang vs Incheon United BTTS YES';
    }
    if(direct.length>=4)direct[2].style.setProperty('display','none','important');
  };

  repair();
  requestAnimationFrame(repair);
  [120,350,700,1100].forEach(ms=>setTimeout(repair,ms));
})();