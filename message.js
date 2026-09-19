(() => {
  'use strict';

  const form=document.getElementById('sfMessageForm');
  if(!form)return;

  const message=form.elements.message;
  const length=document.getElementById('messageLength');
  const submit=document.getElementById('messageSubmit');
  const status=document.getElementById('messageStatus');
  const token=document.getElementById('messageClientToken');
  const sink=document.getElementById('sfMessageSink');

  const configured=!form.action.includes('__SFANDOM_MESSAGE_WEB_APP_URL__');
  const tokenKey='sfandom_message_client_token';
  let clientToken='';

  try{
    clientToken=localStorage.getItem(tokenKey)||crypto.randomUUID();
    localStorage.setItem(tokenKey,clientToken);
  }catch{
    clientToken=String(Date.now())+'-'+Math.random().toString(36).slice(2);
  }

  token.value=clientToken;

  const updateLength=()=>{length.textContent=`${message.value.length} / 1500`};
  message.addEventListener('input',updateLength);
  updateLength();

  if(!configured){
    submit.disabled=true;
    status.textContent='접수 기능 연결 전입니다.';
    return;
  }

  status.textContent='메시지는 공개되지 않습니다.';
  let responseTimer=null;

  const finish=(ok,text)=>{
    clearTimeout(responseTimer);
    responseTimer=null;
    submit.disabled=false;
    status.textContent=text;
    if(ok){
      form.reset();
      token.value=clientToken;
      updateLength();
    }
  };

  window.addEventListener('message',event=>{
    if(!sink||event.source!==sink.contentWindow)return;

    let data=event.data;
    if(typeof data==='string'){
      try{data=JSON.parse(data)}catch{return}
    }
    if(!data||data.source!=='sfandom-message')return;

    if(data.ok){
      finish(true,'메시지가 접수되었습니다.');
      return;
    }

    const reason={
      consent:'동의 확인이 필요합니다.',
      category:'분류를 다시 선택해 주세요.',
      message:'메시지 길이를 확인해 주세요.',
      email:'회신 이메일 형식을 확인해 주세요.',
      rate:'잠시 후 다시 보내 주세요.',
      busy:'현재 접수가 많습니다. 잠시 후 다시 시도해 주세요.'
    }[data.error]||'접수에 실패했습니다. 잠시 후 다시 시도해 주세요.';

    finish(false,reason);
  });

  form.addEventListener('submit',event=>{
    if(!form.checkValidity()){
      event.preventDefault();
      form.reportValidity();
      return;
    }

    submit.disabled=true;
    status.textContent='전송 중입니다…';

    clearTimeout(responseTimer);
    responseTimer=window.setTimeout(()=>{
      submit.disabled=false;
      status.textContent='접수 확인이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.';
    },10000);
  });
})();
