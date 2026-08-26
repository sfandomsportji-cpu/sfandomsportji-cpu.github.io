(()=>{
  /* Anonymous-note UI retired. This file now only stabilizes the homepage pick board. */
  document.getElementById('sfAnonymousNoteButton')?.remove();
  document.querySelector('.sf-note-modal')?.remove();
  document.querySelectorAll('style[data-sf-transient="anonymous-note"]').forEach(el=>el.remove());

  const LG_LOGO='https://upload.wikimedia.org/wikipedia/commons/4/41/LG_Twins_2017.png';
  const NC_LOGO='https://logotyp.us/file/nc-dinos.svg';
  const ANYANG_LOGO='https://assets.football-logos.cc/logos/south-korea/1500x1500/fc-anyang.0d8f9cd2.png';
  const INCHEON_LOGO='https://assets.football-logos.cc/logos/south-korea/1500x1500/incheon-united.f81e13ae.png';

  if(!document.getElementById('sfPickRepairStyle')){
    const style=document.createElement('style');
    style.id='sfPickRepairStyle';
    style.textContent=`
      body.home-v2 section[aria-labelledby="pick-result-title"] > div:nth-of-type(3){display:none!important}
      body.home-v2 .sf-real-pick-board{display:grid;gap:18px;padding:22px;background:linear-gradient(135deg,#071019 0%,#05070b 52%,#09070d 100%)}
      body.home-v2 .sf-real-pick-row{display:grid;grid-template-columns:minmax(390px,1.05fr) minmax(330px,.95fr) 180px;align-items:center;gap:26px;min-height:190px;padding:26px 28px;border:1px solid #303641;border-radius:18px;background:linear-gradient(135deg,#0d151e,#090a0f 74%);position:relative;overflow:hidden}
      body.home-v2 .sf-real-pick-row.kbo:before,body.home-v2 .sf-real-pick-row.kleague:before{content:'';position:absolute;left:0;top:0;bottom:0;width:9px;border-radius:18px 0 0 18px}
      body.home-v2 .sf-real-pick-row.kbo:before{background:#ef2d2d}
      body.home-v2 .sf-real-pick-row.kleague{background:linear-gradient(135deg,#12101b,#090a0f 74%);border-color:#393347}
      body.home-v2 .sf-real-pick-row.kleague:before{background:#7e2fd1}
      body.home-v2 .sf-real-teams{display:grid;grid-template-columns:88px minmax(0,1fr) 88px;align-items:center;gap:18px;padding-right:22px;border-right:1px solid #303641;min-width:0}
      body.home-v2 .sf-real-logo-wrap{display:grid;place-items:center;width:88px;height:88px}
      body.home-v2 .sf-real-logo-wrap img{display:block;max-width:88px;max-height:88px;width:auto;height:auto;object-fit:contain;filter:drop-shadow(0 8px 16px rgba(0,0,0,.32))}
      body.home-v2 .sf-real-match{min-width:0}
      body.home-v2 .sf-real-league{display:inline-flex;align-items:center;min-height:30px;margin-bottom:13px;padding:0 10px;border-radius:999px;background:#ef2d2d;color:#fff;font:900 .67rem/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:.04em;white-space:nowrap}
      body.home-v2 .kleague .sf-real-league{background:#252837;border:1px solid #4b5061}
      body.home-v2 .sf-real-match h3{margin:0;color:#fff;font:900 clamp(1.35rem,2.4vw,2.05rem)/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:-.04em;white-space:nowrap}
      body.home-v2 .sf-real-match h3 span{color:#747b87;font-size:.65em;margin:0 .2em}
      body.home-v2 .sf-real-match p{margin:12px 0 0;color:#949aa5;font:800 .78rem/1.3 Inter,'Noto Sans KR',sans-serif;letter-spacing:.02em}
      body.home-v2 .sf-real-market small{display:block;margin-bottom:13px;color:#ef2d2d;font:900 .72rem/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:.08em}
      body.home-v2 .kleague .sf-real-market small{color:#b49cff}
      body.home-v2 .sf-real-market strong{display:block;color:#fff;font:900 clamp(2.35rem,4.4vw,4rem)/.95 Inter,'Noto Sans KR',sans-serif;letter-spacing:-.055em;white-space:nowrap}
      body.home-v2 .sf-real-market strong b{color:#ef2d2d}
      body.home-v2 .sf-real-market p{margin:14px 0 0;color:#9fa5ae;font:700 .75rem/1.45 Inter,'Noto Sans KR',sans-serif}
      body.home-v2 .sf-real-read{align-self:stretch;display:flex;flex-direction:column;justify-content:center;padding:16px 18px;border:1px solid #2c323b;border-radius:14px;background:#07090c}
      body.home-v2 .sf-real-read small{color:#8e95a0;font:900 .62rem/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:.11em}
      body.home-v2 .sf-real-read strong{margin:11px 0;color:#fff;font:900 .94rem/1.1 Inter,'Noto Sans KR',sans-serif}
      body.home-v2 .sf-real-read span{color:#c3c6cc;font:700 .68rem/1.55 Inter,'Noto Sans KR',sans-serif}
      body.home-v2 .sf-real-read b{margin-top:8px;color:#ef2d2d;font:900 .69rem/1 Inter,'Noto Sans KR',sans-serif}
      @media(max-width:980px){
        body.home-v2 .sf-real-pick-row{grid-template-columns:1fr;gap:18px}
        body.home-v2 .sf-real-teams{border-right:0;border-bottom:1px solid #303641;padding:0 0 20px}
        body.home-v2 .sf-real-read{min-height:92px}
      }
      @media(max-width:620px){
        body.home-v2 .sf-real-pick-board{padding:12px}
        body.home-v2 .sf-real-pick-row{padding:22px 18px;min-height:0}
        body.home-v2 .sf-real-teams{grid-template-columns:64px minmax(0,1fr) 64px;gap:11px}
        body.home-v2 .sf-real-logo-wrap{width:64px;height:64px}
        body.home-v2 .sf-real-logo-wrap img{max-width:64px;max-height:64px}
        body.home-v2 .sf-real-match h3{white-space:normal;font-size:1.15rem}
        body.home-v2 .sf-real-market strong{font-size:2.7rem}
      }
    `;
    document.head.appendChild(style);
  }

  const boardHTML=()=>`
    <div class="sf-real-pick-board" data-sf-real-board="1" aria-label="SFANDOM 오늘의 베스트 2 픽">
      <article class="sf-real-pick-row kbo">
        <div class="sf-real-teams">
          <div class="sf-real-logo-wrap"><img src="${LG_LOGO}" alt="LG Twins logo" referrerpolicy="no-referrer"></div>
          <div class="sf-real-match">
            <span class="sf-real-league">01 · KBO</span>
            <h3>LG <span>vs</span> NC</h3>
            <p>18:30 · JAMSIL · KST</p>
          </div>
          <div class="sf-real-logo-wrap"><img src="${NC_LOGO}" alt="NC Dinos logo" referrerpolicy="no-referrer"></div>
        </div>
        <div class="sf-real-market">
          <small>OVERSEAS TOTAL LINE</small>
          <strong>OVER <b>8.5</b></strong>
          <p>5–4 in extras yesterday · late scoring swing</p>
        </div>
        <div class="sf-real-read">
          <small>SFANDOM READ</small>
          <strong>TOTALS MARKET</strong>
          <span>Avoid side risk<br>Focus on scoring flow</span>
          <b>PICK · O8.5</b>
        </div>
      </article>

      <article class="sf-real-pick-row kleague">
        <div class="sf-real-teams">
          <div class="sf-real-logo-wrap"><img src="${ANYANG_LOGO}" alt="FC Anyang logo" referrerpolicy="no-referrer"></div>
          <div class="sf-real-match">
            <span class="sf-real-league">02 · K LEAGUE 1</span>
            <h3>FC ANYANG <span>vs</span> INCHEON UTD</h3>
            <p>19:30 · KST</p>
          </div>
          <div class="sf-real-logo-wrap"><img src="${INCHEON_LOGO}" alt="Incheon United logo" referrerpolicy="no-referrer"></div>
        </div>
        <div class="sf-real-market">
          <small>MARKET · BOTH TEAMS TO SCORE</small>
          <strong>BTTS <b>YES</b></strong>
          <p>Avoid 1X2 · prefer both-team scoring route</p>
        </div>
        <div class="sf-real-read">
          <small>SFANDOM READ</small>
          <strong>MARKET SWITCH</strong>
          <span>Avoid 1X2<br>Prefer BTTS route</span>
          <b>PICK · YES</b>
        </div>
      </article>
    </div>`;

  let repairing=false;
  const repair=()=>{
    if(repairing)return;
    const section=document.querySelector('section[aria-labelledby="pick-result-title"]');
    if(!section)return;
    repairing=true;
    try{
      const direct=[...section.children].filter(el=>el.tagName==='DIV');
      if(direct.length>=3)direct[2].style.setProperty('display','none','important');
      const visual=direct[1];
      if(visual&&!visual.querySelector('[data-sf-real-board="1"]')){
        visual.style.removeProperty('aspect-ratio');
        visual.style.background='#07090d';
        visual.innerHTML=boardHTML();
      }
    }finally{repairing=false}
  };

  const section=document.querySelector('section[aria-labelledby="pick-result-title"]');
  if(section){
    const observer=new MutationObserver(()=>repair());
    observer.observe(section,{childList:true,subtree:true});
  }

  repair();
  requestAnimationFrame(repair);
  [80,180,350,650,1000,1600].forEach(ms=>setTimeout(repair,ms));
})();