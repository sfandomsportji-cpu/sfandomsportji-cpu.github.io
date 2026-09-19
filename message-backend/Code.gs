const CONFIG={
  sheetName:'메시지함',
  minLength:10,
  maxLength:1500,
  cooldownSeconds:60,
  targetOrigin:'https://sfandom.com'
};

function doGet(){
  return frameResponse_({ok:true,service:'sfandom-message-intake'});
}

function doPost(e){
  const p=(e&&e.parameter)||{};
  if(String(p.website||'').trim())return frameResponse_({ok:true});

  const category=clean_(p.category,20);
  const nickname=clean_(p.nickname,30);
  const replyEmail=clean_(p.replyEmail,120);
  const message=clean_(p.message,CONFIG.maxLength);
  const source=clean_(p.source,200);
  const token=clean_(p.clientToken,100);
  const consent=String(p.consent||'').trim();

  if(consent!=='yes')return frameResponse_({ok:false,error:'consent'});
  if(!['의견','문의','제안','오류신고','기타'].includes(category))return frameResponse_({ok:false,error:'category'});
  if(message.length<CONFIG.minLength||message.length>CONFIG.maxLength)return frameResponse_({ok:false,error:'message'});
  if(replyEmail&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(replyEmail))return frameResponse_({ok:false,error:'email'});
  if(!token)return frameResponse_({ok:false,error:'token'});

  const spreadsheetId=PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if(!spreadsheetId)return frameResponse_({ok:false,error:'config'});

  const cache=CacheService.getScriptCache();
  const key='rate:'+Utilities.base64EncodeWebSafe(
    Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,token)
  ).slice(0,32);
  if(cache.get(key))return frameResponse_({ok:false,error:'rate'});

  const lock=LockService.getScriptLock();
  if(!lock.tryLock(5000))return frameResponse_({ok:false,error:'busy'});

  try{
    const sheet=SpreadsheetApp.openById(spreadsheetId).getSheetByName(CONFIG.sheetName);
    if(!sheet)return frameResponse_({ok:false,error:'sheet'});

    sheet.appendRow([
      new Date(),
      '신규',
      safeCell_(category),
      safeCell_(nickname),
      safeCell_(replyEmail),
      safeCell_(message),
      safeCell_(source),
      ''
    ]);

    cache.put(key,'1',CONFIG.cooldownSeconds);
    return frameResponse_({ok:true});
  }catch(err){
    return frameResponse_({ok:false,error:'server'});
  }finally{
    lock.releaseLock();
  }
}

function clean_(value,max){
  return String(value||'').replace(/[\u0000-\u001F\u007F]/g,' ').trim().slice(0,max);
}

function safeCell_(value){
  const s=String(value||'');
  return /^[=+\-@]/.test(s)?"'"+s:s;
}

function frameResponse_(data){
  const payload=JSON.stringify(Object.assign({source:'sfandom-message'},data));
  const html='<!doctype html><meta charset="utf-8"><script>try{parent.postMessage('+JSON.stringify(payload)+','+JSON.stringify(CONFIG.targetOrigin)+')}catch(e){}<\/script>';
  return HtmlService.createHtmlOutput(html)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
