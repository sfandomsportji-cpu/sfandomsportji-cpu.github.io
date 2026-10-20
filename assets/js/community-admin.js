/* SFANDOM verified moderator tools. The server checks identity and allowlist on every deletion. */
(() => {
  "use strict";
  const root=document.querySelector("[data-admin-mode]");
  const cfg=window.SFANDOM?.supabase;
  if(!root||!cfg?.url||!cfg.key)return;
  const open=root.querySelector("[data-admin-open]");
  const panel=root.querySelector("[data-admin-panel]");
  const form=root.querySelector("[data-admin-form]");
  const note=root.querySelector("[data-admin-status]");
  const logout=root.querySelector("[data-admin-logout]");
  const say=text=>{note.textContent=text};
  const tokenKey="sfandom_admin_access_token";
  let token="";
  try{
    const hash=new URLSearchParams(location.hash.replace(/^#/,""));
    if(hash.has("access_token")){
      token=hash.get("access_token")||"";
      sessionStorage.setItem(tokenKey,token);
      history.replaceState(null,"",location.pathname+location.search);
    } else token=sessionStorage.getItem(tokenKey)||"";
  }catch(_){}
  const api=async(path,opts={})=>{
    const ctrl=new AbortController(),timeout=setTimeout(()=>ctrl.abort(),12000);
    try{
      const r=await fetch(cfg.url+path,{...opts,signal:ctrl.signal,cache:"no-store",headers:{apikey:cfg.key,Accept:"application/json",...(token?{Authorization:"Bearer "+token}:{}),...(opts.headers||{})}});
      if(!r.ok){const e=Error("HTTP "+r.status);e.status=r.status;throw e}
      return r;
    }finally{clearTimeout(timeout)}
  };
  let admin=false;
  const state=()=>{window.SFANDOM_ADMIN={canDelete:admin,deleteComment:async id=>{
    if(!admin)throw Error("not_admin");
    const res=await api("/functions/v1/community-manage",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"moderate",target_type:"comment",target_id:id,operation:"delete"})});
    const data=await res.json();if(!data.ok)throw Error("delete_failed");return data;
  }};
    root.dataset.adminActive=admin?"true":"false";
    open.textContent=admin?"관리자 모드 활성":"관리자 로그인";
    logout.hidden=!admin;
    document.dispatchEvent(new CustomEvent("sfandom-admin-state",{detail:{admin}}));
  };
  async function check(){
    if(!token){admin=false;state();return}
    try{
      const res=await api("/functions/v1/community-manage",{method:"GET"});
      const data=await res.json();
      admin=!!data.admin;
      if(!admin)say("이 계정에는 아직 관리자 권한이 없습니다.");
      else{say("관리자 인증 완료. 댓글에 삭제 버튼이 표시됩니다.");panel.hidden=false;}
    }catch(_){admin=false;say("관리자 인증 확인에 실패했습니다. 다시 시도해 주세요.");}
    state();
  }
  open.addEventListener("click",()=>{panel.hidden=!panel.hidden;});
  logout.addEventListener("click",()=>{
    token="";admin=false;
    try{sessionStorage.removeItem(tokenKey)}catch(_){}
    say("관리자 모드를 종료했습니다.");
    state();
  });
  form.addEventListener("submit",async e=>{
    e.preventDefault();
    const email=String(new FormData(form).get("email")||"").trim().toLowerCase();
    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))return say("이메일 주소를 확인해 주세요.");
    const button=form.querySelector("button[type=submit]");
    button.disabled=true;say("로그인 메일을 요청하고 있어요…");
    try{
      const redirect="https://sfandom.com/community/?admin=1";
      const res=await fetch(cfg.url+"/auth/v1/otp?redirect_to="+encodeURIComponent(redirect),{method:"POST",headers:{apikey:cfg.key,"Content-Type":"application/json"},body:JSON.stringify({email,create_user:true})});
      if(!res.ok)throw Error("mail_failed");
      say("인증 메일을 발송했습니다. 메일의 로그인 링크로 돌아오세요. 허가된 관리자 계정만 삭제할 수 있습니다.");
    }catch(_){say("로그인 메일을 보내지 못했습니다. 관리자 설정을 확인해 주세요.");}
    finally{button.disabled=false;}
  });
  state();
  check();
})();