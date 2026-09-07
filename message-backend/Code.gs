const CONFIG={sheetName:'메시지함',minLength:10,maxLength:1500,cooldownSeconds:60};

function doGet(){
  return response_({ok:true,service:'sfandom-message-intake'});
}

function doPost(e){
  const p=(e&&e.parameter)||{};
  if(String(p.website||'').trim())return response_({ok:true});

  const category=clean_(p.category,20);
  const nickname=clean_(p.nickname,30);
  const replyEmail=clean_(p.replyEmail,120);
  const message=clean_(p.message,CONFIG.maxLength);
  const source=clean_(p.source,200);
  const token=clean_(p.clientToken,100);

  if(!['의견','문의','제안','오류신고','기타'].includes(category))return response_({ok:false,error:'category'});
  if(message.length<CONFIG.minLength||message.length>CONFIG.maxLength)return response_({ok:false,error:'message'});
  if(replyEmail&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(replyEmail))return response_({ok:false,error:'email'});
  if(!token)return response_({ok:false,error:'token'});

  const spreadsheetId=PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if(!spreadsheetId)throw new Error('SPREADSHEET_ID script property is not configured');

  const cache=CacheService.getScriptCache();
  const key='rate:'+Utilities.base64EncodeWebSafe(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,token)).slice(0,32);
  if(cache.get(key))return response_({ok:false,error:'rate'});

  const lock=LockService.getScriptLock();
  if(!lock.tryLock(5000))return response_({ok:false,error:'busy'});
  try{
    const sheet=SpreadsheetApp.openById(spreadsheetId).getSheetByName(CONFIG.sheetName);
    if(!sheet)throw new Error('sheet not found');
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
  }finally{
    lock.releaseLock();
  }
  return response_({ok:true});
}

function clean_(value,max){
  return String(value||'').replace(/[\u0000-\u001F\u007F]/g,' ').trim().slice(0,max);
}

function safeCell_(value){
  const s=String(value||'');
  return /^[=+\-@]/.test(s)?"'"+s:s;
}

function response_(data){
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}
