(() => {
  'use strict';
  const form=document.getElementById('sfMessageForm');
  if(!form)return;
  const message=form.elements.message;
  const length=document.getElementById('messageLength');
  const submit=document.getElementById('messageSubmit');
  const status=document.getElementById('messageStatus');
  const token=document.getElementById('messageClientToken');
  const configured=!form.action.includes('__SFANDOM_MESSAGE_WEB_APP_URL__');
  const tokenKey='sfandom_message_client_token';
  let clientToken='';
  try{clientToken=localStorage.getItem(tokenKey)||crypto.randomUUID();localStorage.setItem(tokenKey,clientToken)}catch{clientToken=String(Date.now())+'-'+Math.random().toString(36).slice(2)}
  token.value=clientToken;
  const updateLength=()=>{length.textContent=`${message.value.length} / 1500`};
  message.addEventListener('input',updateLength);updateLength();
  if(!configured){submit.disabled=true;return}
  status.textContent='메시지는 공개되지 않습니다.';
  form.addEventListener('submit',event=>{
    if(!form.checkValidity()){event.preventDefault();form.reportValidity();return}
    submit.disabled=true;status.textContent='전송 중입니다…';
    window.setTimeout(()=>{form.reset();updateLength();submit.disabled=false;status.textContent='메시지가 접수되었습니다.'},1400);
  });
})();
