(()=>{
  function enhanceChrome(){
    const header=document.querySelector('.site-header');
    const nav=header?.querySelector('.nav');
    if(nav&&!nav.querySelector('a[href="/preamble.html"],a[href="preamble.html"],a[href="../preamble.html"]')){
      const link=document.createElement('a');
      link.href='/preamble.html';
      link.textContent='PREAMBLE';
      const about=[...nav.querySelectorAll('a')].find(a=>/about\.html(?:$|[?#])/.test(a.getAttribute('href')||''));
      if(about)nav.insertBefore(link,about);else nav.appendChild(link);
    }
    if(nav){
      [...nav.querySelectorAll('a')].forEach(a=>{
        const href=a.getAttribute('href')||'';
        if(/analysis\.html(?:$|[?#])/.test(href))a.textContent='ANALYSIS';
        else if(/content\.html(?:$|[?#])/.test(href))a.textContent='CONTENT';
        else if(/(?:^|\/)archive\/?(?:$|[?#])/.test(href)||href==='archive/'||href==='./')a.textContent='ARCHIVE';
        else if(/preamble\.html(?:$|[?#])/.test(href))a.textContent='PREAMBLE';
        else if(/about\.html(?:$|[?#])/.test(href))a.textContent='ABOUT';
      });
    }
    if(header){
      let cta=header.querySelector('.header-cta');
      if(!cta){
        cta=document.createElement('a');
        cta.className='header-cta';
        cta.href='/analysis.html';
        header.appendChild(cta);
      }
      cta.textContent='ENTER LAB ↗';
    }

    const footer=document.querySelector('.footer-links');
    if(footer){
      if(!footer.querySelector('a[href="/preamble.html"],a[href="preamble.html"],a[href="../preamble.html"]')){
        const link=document.createElement('a');link.href='/preamble.html';link.textContent='전문';
        const about=[...footer.querySelectorAll('a')].find(a=>/about\.html(?:$|[?#])/.test(a.getAttribute('href')||'')||a.textContent.trim()==='소개');
        if(about)footer.insertBefore(link,about);else footer.appendChild(link);
      }
      if(!footer.querySelector('a[href="/legal.html"],a[href="legal.html"],a[href="../legal.html"]')){
        const legal=document.createElement('a');legal.href='/legal.html';legal.textContent='운영·법률';footer.appendChild(legal);
      }
      if(!footer.querySelector('a[href="/terms.html"],a[href="terms.html"],a[href="../terms.html"]')){
        const terms=document.createElement('a');terms.href='/terms.html';terms.textContent='이용약관';footer.appendChild(terms);
      }
      if(!footer.querySelector('a[href="/privacy.html"],a[href="privacy.html"],a[href="../privacy.html"]')){
        const privacy=document.createElement('a');privacy.href='/privacy.html';privacy.textContent='개인정보 처리방침';footer.appendChild(privacy);
      }
    }
  }

  function enhanceHome(){
    const isHome=location.pathname==='/'||location.pathname.endsWith('/index.html');
    if(!isHome)return;

    const card=document.querySelector('.forecast-card');
    if(card){
      const kicker=card.querySelector('.card-kicker span');
      const badge=card.querySelector('.card-kicker b');
      const label=card.querySelector('.forecast-score span');
      const score=card.querySelector('.forecast-score strong');
      const bar=card.querySelector('.signal i');
      const stats=[...card.querySelectorAll('.mini-stats > div')];
      if(kicker)kicker.textContent='SFANDOM PUBLIC PICKS';
      if(badge)badge.textContent='UPDATED';
      if(label)label.textContent='PICK HIT RATE';
      if(score)score.innerHTML='90<small>%</small>';
      if(bar)bar.style.width='90%';
      const values=[['RECORD','OPEN'],['REVIEW','ALL'],['STATUS','LIVE']];
      stats.forEach((el,i)=>{if(!values[i])return;const s=el.querySelector('span');const b=el.querySelector('b');if(s)s.textContent=values[i][0];if(b)b.textContent=values[i][1]});
    }

    const matrix=document.querySelector('.matrix');
    if(matrix){
      const head=matrix.querySelector('.matrix-head span');
      const code=matrix.querySelector('.matrix-head b');
      if(head)head.textContent='SFANDOM ANALYSIS PROCESS';
      if(code)code.textContent='LIVE';
      const rows=[...matrix.querySelectorAll('.matrix-row')];
      const vals=[['RECENT FORM','CHECK'],['STARTER / LINEUP','CHECK'],['MATCHUP','TRACK'],['SITUATION','TRACK'],['MARKET SIGNAL','REVIEW']];
      rows.forEach((row,i)=>{
        if(!vals[i])return;
        const name=row.querySelector('span');
        const fill=row.querySelector('i b');
        const value=row.querySelector('em');
        if(name)name.textContent=vals[i][0];
        if(fill)fill.style.width='100%';
        if(value)value.textContent=vals[i][1];
      });
      const foot=matrix.querySelector('.matrix-foot');
      if(foot){const s=foot.querySelector('span');const strong=foot.querySelector('strong');if(s)s.textContent='PROCESS STATUS';if(strong)strong.textContent='ACTIVE'}
    }
  }

  function maybeShowPreamble(){
    const isHome=location.pathname==='/'||location.pathname.endsWith('/index.html');
    if(!isHome||document.querySelector('.sf-preamble-modal'))return;
    let seen=false;
    try{seen=localStorage.getItem('sfandomPreambleSeenV1')==='1'}catch{}
    if(seen)return;

    const style=document.createElement('style');
    style.dataset.sfTransient='preamble';
    style.textContent=`
      .sf-preamble-modal{position:fixed;inset:0;z-index:10000;display:grid;place-items:center;padding:20px;background:rgba(0,0,0,.78);backdrop-filter:blur(9px)}
      .sf-preamble-card{position:relative;width:min(720px,100%);max-height:min(82vh,760px);overflow:auto;border:1px solid #34343a;background:linear-gradient(145deg,#111114,#070708 72%);box-shadow:0 30px 100px rgba(0,0,0,.55);padding:34px}
      .sf-preamble-card:before{content:'';position:absolute;right:-80px;top:-100px;width:300px;height:300px;border-radius:50%;background:radial-gradient(circle,rgba(239,45,45,.2),transparent 66%);pointer-events:none}
      .sf-preamble-card small{position:relative;z-index:1;color:#ef2d2d;font-size:.62rem;font-weight:900;letter-spacing:.16em}
      .sf-preamble-card h2{position:relative;z-index:1;margin:12px 0 18px;color:#fff;font-size:clamp(2rem,6vw,4rem);line-height:.94;letter-spacing:-.055em}
      .sf-preamble-card h2 span{color:#ef2d2d}.sf-preamble-card p{position:relative;z-index:1;margin:0;color:#b7b7be;line-height:1.85;font-size:.92rem;word-break:keep-all}
      .sf-preamble-points{position:relative;z-index:1;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:24px 0}.sf-preamble-points div{padding:13px;border:1px solid #29292e;background:#0a0a0c}.sf-preamble-points b{display:block;color:#fff;font-size:.75rem}.sf-preamble-points span{display:block;margin-top:5px;color:#707078;font-size:.6rem;font-weight:800;letter-spacing:.08em}
      .sf-preamble-actions{position:relative;z-index:1;display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}.sf-preamble-actions a,.sf-preamble-actions button{appearance:none;border:1px solid #38383e;background:#0c0c0e;color:#fff;padding:12px 15px;text-decoration:none;font:800 .72rem/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:.06em;cursor:pointer}.sf-preamble-actions a{border-color:#ef2d2d;background:#17090b}.sf-preamble-close{position:absolute;right:15px;top:15px;z-index:2;width:36px;height:36px;border:1px solid #33343a;background:#0a0a0c;color:#aaa;font-size:1.1rem;cursor:pointer}
      @media(max-width:620px){.sf-preamble-modal{padding:12px}.sf-preamble-card{padding:27px 20px}.sf-preamble-points{grid-template-columns:1fr}.sf-preamble-actions a,.sf-preamble-actions button{flex:1;text-align:center}}
    `;
    document.head.appendChild(style);

    const modal=document.createElement('div');
    modal.className='sf-preamble-modal';
    modal.setAttribute('role','dialog');
    modal.setAttribute('aria-modal','true');
    modal.setAttribute('aria-labelledby','sfPreambleTitle');
    modal.innerHTML=`<div class="sf-preamble-card"><button type="button" class="sf-preamble-close" aria-label="닫기">×</button><small>SFANDOM PREAMBLE · 前文</small><h2 id="sfPreambleTitle">결과보다 먼저,<br><span>근거를 남깁니다.</span></h2><p>SFANDOM은 스포츠를 단순한 승패가 아니라 기록과 흐름이 축적되는 데이터로 봅니다. 맞았다는 말보다 왜 그렇게 판단했는지를 먼저 공개하고, 실패한 기록까지 남겨 신뢰를 쌓겠습니다.</p><div class="sf-preamble-points"><div><b>근거 우선</b><span>EVIDENCE FIRST</span></div><div><b>시각 기록</b><span>TIME STAMP</span></div><div><b>결과 보존</b><span>RECORD EVERYTHING</span></div></div><div class="sf-preamble-actions"><a href="/preamble.html">전문 전체보기 →</a><button type="button" data-dismiss>확인했습니다</button></div></div>`;
    document.body.appendChild(modal);

    const close=()=>{try{localStorage.setItem('sfandomPreambleSeenV1','1')}catch{}modal.remove();style.remove()};
    modal.querySelector('.sf-preamble-close').addEventListener('click',close);
    modal.querySelector('[data-dismiss]').addEventListener('click',close);
    modal.addEventListener('click',e=>{if(e.target===modal)close()});
    const esc=e=>{if(e.key==='Escape'&&document.body.contains(modal)){close();document.removeEventListener('keydown',esc)}};
    document.addEventListener('keydown',esc);
  }

  function loadAnonymousNote(){
    if(document.getElementById('sfAnonymousNoteButton')||document.querySelector('script[data-sf-anonymous-note]'))return;
    const script=document.createElement('script');
    script.dataset.sfAnonymousNote='1';
    script.src='/anonymous-note.js?v=20260826-note3';
    script.async=false;
    script.onerror=()=>console.warn('[SFANDOM] anonymous note loader failed');
    document.body.appendChild(script);
  }

  document.documentElement.classList.remove('sf-route-loading');
  enhanceChrome();
  enhanceHome();
  maybeShowPreamble();
  loadAnonymousNote();
})();
