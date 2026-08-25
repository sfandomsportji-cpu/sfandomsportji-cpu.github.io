(()=>{
  if(document.getElementById('sfAnonymousNoteButton'))return;

  const ENDPOINT='https://formsubmit.co/ajax/sfandomsportji@gmail.com';
  const COOLDOWN_KEY='sfandomAnonymousNoteLastSentV1';

  const style=document.createElement('style');
  style.dataset.sfTransient='anonymous-note';
  style.textContent=`
    .sf-note-trigger{position:relative;display:grid;place-items:center;flex:0 0 42px;width:42px;height:42px;margin-left:auto;margin-right:10px;border:1px solid #34343a;background:#0a0a0c;color:#f3f3f5;cursor:pointer;transition:border-color .18s ease,background .18s ease,transform .18s ease;z-index:3}
    .sf-note-trigger:hover{border-color:#ef2d2d;background:#17090b;transform:translateY(-1px)}
    .sf-note-trigger svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
    .sf-note-trigger:after{content:'익명 쪽지';position:absolute;right:0;top:calc(100% + 8px);width:max-content;padding:7px 9px;border:1px solid #2d2d31;background:#0a0a0c;color:#aaa;font:800 .58rem/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:.05em;opacity:0;pointer-events:none;transform:translateY(-3px);transition:.16s ease}
    .sf-note-trigger:hover:after,.sf-note-trigger:focus-visible:after{opacity:1;transform:none}
    .sf-note-modal{position:fixed;inset:0;z-index:12000;display:grid;place-items:center;padding:18px;background:rgba(0,0,0,.76);backdrop-filter:blur(8px)}
    .sf-note-card{position:relative;width:min(520px,100%);border:1px solid #34343a;background:linear-gradient(145deg,#111114,#070708 72%);box-shadow:0 28px 90px rgba(0,0,0,.58);padding:28px}
    .sf-note-card:before{content:'';position:absolute;right:-55px;top:-70px;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle,rgba(239,45,45,.16),transparent 68%);pointer-events:none}
    .sf-note-close{position:absolute;right:13px;top:13px;width:34px;height:34px;border:1px solid #303035;background:#09090b;color:#aaa;font-size:1.05rem;cursor:pointer;z-index:2}
    .sf-note-eyebrow{position:relative;z-index:1;margin:0 0 10px;color:#ef2d2d;font:900 .61rem/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:.16em}
    .sf-note-card h2{position:relative;z-index:1;margin:0;color:#fff;font:900 clamp(1.65rem,5vw,2.45rem)/1.03 Inter,'Noto Sans KR',sans-serif;letter-spacing:-.045em}
    .sf-note-card h2 span{color:#ef2d2d}
    .sf-note-desc{position:relative;z-index:1;margin:12px 0 20px;color:#8f8f97;font:600 .78rem/1.7 Inter,'Noto Sans KR',sans-serif;word-break:keep-all}
    .sf-note-field{position:relative;z-index:1}
    .sf-note-field textarea{display:block;box-sizing:border-box;width:100%;min-height:150px;resize:vertical;border:1px solid #303036;background:#08080a;color:#f5f5f6;padding:15px 15px 34px;outline:none;font:600 .88rem/1.65 Inter,'Noto Sans KR',sans-serif;transition:border-color .15s ease}
    .sf-note-field textarea:focus{border-color:#ef2d2d}
    .sf-note-count{position:absolute;right:11px;bottom:9px;color:#66666e;font:800 .58rem/1 Inter,sans-serif;letter-spacing:.04em}
    .sf-note-honey{position:absolute!important;left:-10000px!important;width:1px!important;height:1px!important;opacity:0!important;pointer-events:none!important}
    .sf-note-actions{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:14px}
    .sf-note-privacy{color:#66666e;font:700 .6rem/1.45 Inter,'Noto Sans KR',sans-serif}
    .sf-note-send{appearance:none;border:1px solid #ef2d2d;background:#ef2d2d;color:#fff;min-width:118px;padding:12px 15px;cursor:pointer;font:900 .7rem/1 Inter,'Noto Sans KR',sans-serif;letter-spacing:.06em;transition:filter .15s ease,opacity .15s ease}
    .sf-note-send:hover{filter:brightness(1.08)}.sf-note-send:disabled{opacity:.55;cursor:default}
    .sf-note-status{position:relative;z-index:1;display:none;margin-top:13px;padding:10px 12px;border:1px solid #29292e;background:#0a0a0c;color:#aaa;font:700 .68rem/1.5 Inter,'Noto Sans KR',sans-serif}
    .sf-note-status.is-success{display:block;border-color:#285c39;color:#9ee3b6}.sf-note-status.is-error{display:block;border-color:#713333;color:#ffadad}
    @media(max-width:820px){.sf-note-trigger{margin-left:6px;margin-right:6px;flex-basis:38px;width:38px;height:38px}.sf-note-trigger:after{display:none}}
    @media(max-width:560px){.sf-note-modal{padding:10px}.sf-note-card{padding:25px 18px}.sf-note-actions{align-items:stretch;flex-direction:column}.sf-note-send{width:100%}.sf-note-privacy{text-align:center}}
  `;
  document.head.appendChild(style);

  function installTrigger(){
    const header=document.querySelector('.site-header');
    if(!header||document.getElementById('sfAnonymousNoteButton'))return;
    const button=document.createElement('button');
    button.id='sfAnonymousNoteButton';
    button.className='sf-note-trigger';
    button.type='button';
    button.setAttribute('aria-label','관리자에게 익명 쪽지 보내기');
    button.title='익명 쪽지';
    button.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.5 5.5h15v10.5h-9l-4.2 3v-3H4.5z"></path><path d="M8 9h8M8 12.5h5"></path></svg>';
    const cta=header.querySelector('.header-cta');
    if(cta)header.insertBefore(button,cta);else header.appendChild(button);
    button.addEventListener('click',openModal);
  }

  function openModal(){
    if(document.querySelector('.sf-note-modal'))return;
    const modal=document.createElement('div');
    modal.className='sf-note-modal';
    modal.setAttribute('role','dialog');
    modal.setAttribute('aria-modal','true');
    modal.setAttribute('aria-labelledby','sfNoteTitle');
    modal.innerHTML=`
      <form class="sf-note-card" novalidate>
        <button type="button" class="sf-note-close" aria-label="닫기">×</button>
        <p class="sf-note-eyebrow">PRIVATE NOTE · ADMIN ONLY</p>
        <h2 id="sfNoteTitle">관리자에게<br><span>익명 쪽지.</span></h2>
        <p class="sf-note-desc">회원가입 없이 보낼 수 있습니다. 이름·닉네임·이메일은 입력받지 않으며, 쪽지 내용은 사이트에 공개되지 않습니다.</p>
        <label class="sf-note-field">
          <textarea name="message" maxlength="500" required placeholder="전하고 싶은 내용을 자유롭게 적어주세요."></textarea>
          <span class="sf-note-count">0 / 500</span>
        </label>
        <input class="sf-note-honey" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
        <div class="sf-note-actions">
          <span class="sf-note-privacy">ANONYMOUS · 관리자 전용 수신</span>
          <button class="sf-note-send" type="submit">쪽지 보내기 →</button>
        </div>
        <div class="sf-note-status" role="status" aria-live="polite"></div>
      </form>`;
    document.body.appendChild(modal);

    const form=modal.querySelector('form');
    const textarea=form.querySelector('textarea');
    const count=form.querySelector('.sf-note-count');
    const status=form.querySelector('.sf-note-status');
    const send=form.querySelector('.sf-note-send');
    const honey=form.querySelector('[name="website"]');
    const close=()=>modal.remove();

    textarea.addEventListener('input',()=>{count.textContent=`${textarea.value.length} / 500`});
    modal.querySelector('.sf-note-close').addEventListener('click',close);
    modal.addEventListener('click',e=>{if(e.target===modal)close()});
    const esc=e=>{if(e.key==='Escape'&&document.body.contains(modal)){close();document.removeEventListener('keydown',esc)}};
    document.addEventListener('keydown',esc);

    form.addEventListener('submit',async e=>{
      e.preventDefault();
      const message=textarea.value.trim();
      status.className='sf-note-status';
      status.textContent='';
      if(honey.value){close();return}
      if(message.length<2){
        status.className='sf-note-status is-error';
        status.textContent='쪽지 내용을 입력해 주세요.';
        textarea.focus();
        return;
      }
      let last=0;
      try{last=Number(localStorage.getItem(COOLDOWN_KEY)||0)}catch{}
      if(Date.now()-last<30000){
        status.className='sf-note-status is-error';
        status.textContent='연속 전송을 막기 위해 30초 뒤 다시 보낼 수 있습니다.';
        return;
      }

      send.disabled=true;
      send.textContent='전송 중…';
      try{
        const response=await fetch(ENDPOINT,{
          method:'POST',
          headers:{'Content-Type':'application/json','Accept':'application/json'},
          body:JSON.stringify({
            message,
            page:location.href,
            _subject:'[SFANDOM] 새 익명 쪽지',
            _template:'table',
            _captcha:'false',
            _honey:''
          })
        });
        const data=await response.json().catch(()=>({}));
        if(!response.ok||data.success===false)throw new Error(data.message||'send failed');
        try{localStorage.setItem(COOLDOWN_KEY,String(Date.now()))}catch{}
        textarea.value='';count.textContent='0 / 500';
        status.className='sf-note-status is-success';
        status.textContent='전송 완료. 쪽지는 관리자에게만 전달됩니다.';
        send.textContent='보냄 ✓';
        setTimeout(()=>{if(document.body.contains(modal))close()},1400);
      }catch(err){
        console.warn('[SFANDOM] anonymous note failed',err);
        status.className='sf-note-status is-error';
        status.textContent='지금은 전송하지 못했습니다. 잠시 뒤 다시 시도해 주세요.';
        send.disabled=false;
        send.textContent='쪽지 보내기 →';
      }
    });

    requestAnimationFrame(()=>textarea.focus());
  }

  installTrigger();
})();