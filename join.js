(()=>{
  const panels=[...document.querySelectorAll('[data-panel]')];
  const tabs=[...document.querySelectorAll('[data-tab]')];
  const prev=document.getElementById('prevBtn');
  const next=document.getElementById('nextBtn');
  const email=document.getElementById('email');
  const pw=document.getElementById('password');
  const pw2=document.getElementById('password2');
  const nick=document.getElementById('nickname');
  const nickPreview=document.getElementById('nickPreview');
  const avatarPreview=document.getElementById('avatarPreview');
  const required=[...document.querySelectorAll('[data-required]')];
  const status=document.getElementById('joinStatus');
  let step=0;

  const setError=(key,msg)=>{
    const el=document.querySelector(`[data-error="${key}"]`);
    if(!el)return;
    el.textContent=msg;
    el.classList.add('error');
  };
  const clearError=key=>{
    const el=document.querySelector(`[data-error="${key}"]`);
    if(el)el.classList.remove('error');
  };

  function validate(){
    if(step===0){
      let ok=true;
      if(!/^\S+@\S+\.\S+$/.test(email.value.trim())){setError('email','올바른 이메일 형식을 입력해 주세요.');ok=false}else clearError('email');
      if(pw.value.length<10||!/[A-Za-z]/.test(pw.value)||!/\d/.test(pw.value)){setError('password','영문과 숫자를 포함해 10자 이상 입력해 주세요.');ok=false}else clearError('password');
      if(pw2.value!==pw.value||!pw2.value){setError('password2','비밀번호가 서로 일치하지 않습니다.');ok=false}else clearError('password2');
      return ok;
    }
    if(step===1){
      const v=nick.value.trim();
      if(v.length<2){setError('nickname','닉네임은 2자 이상 입력해 주세요.');return false}
      clearError('nickname');
      return true;
    }
    if(step===3)return required.every(x=>x.checked);
    return true;
  }

  function render(){
    panels.forEach((p,i)=>p.classList.toggle('active',i===step));
    tabs.forEach((t,i)=>{
      t.classList.toggle('active',i===step);
      t.classList.toggle('done',i<step);
    });
    prev.disabled=step===0;
    next.textContent=step===3?'가입 준비 검수 완료':'다음 단계';
    next.disabled=step===3&&!required.every(x=>x.checked);
  }

  nick.addEventListener('input',()=>{
    const v=nick.value.trim();
    nickPreview.textContent=v||'SFANDOM MEMBER';
    avatarPreview.textContent=(v.slice(0,2)||'SF').toUpperCase();
  });
  required.forEach(x=>x.addEventListener('change',render));
  prev.addEventListener('click',()=>{
    if(step>0){step--;status.classList.remove('show');render()}
  });
  next.addEventListener('click',()=>{
    if(!validate())return;
    if(step<3){step++;render();return}
    status.classList.add('show');
  });
  render();
})();
