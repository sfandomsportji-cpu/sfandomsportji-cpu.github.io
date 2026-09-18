const CONFIG = {
  postsSheet: 'POSTS',
  pageSize: 10,
  maxPageSize: 10,
  maxTitle: 120,
  maxBody: 2000,
  maxNickname: 30,
  cooldownSeconds: 8
};

function doGet(e) {
  const p = (e && e.parameter) || {};
  const action = String(p.action || 'list');
  if (action !== 'list') return json_({ok:false,error:'action'});

  const page = Math.max(1, parseInt(p.page || '1', 10) || 1);
  const limit = Math.min(CONFIG.maxPageSize, Math.max(1, parseInt(p.limit || CONFIG.pageSize, 10) || CONFIG.pageSize));
  const sheet = postsSheet_();
  const lastRow = sheet.getLastRow();
  if (lastRow <= 1) return json_({ok:true,page:1,limit,total:0,pages:1,posts:[]});

  const values = sheet.getRange(2, 1, lastRow - 1, 13).getDisplayValues();
  const rows = values
    .filter(r => String(r[7] || '').toLowerCase() === 'published')
    .map(r => ({
      post_id:r[0],
      created_at_kst:r[1],
      channel:r[2],
      nickname:r[3],
      title:r[4],
      body:r[5],
      media_url:r[6],
      status:r[7],
      view_count:Number(r[8] || 0),
      comment_count:Number(r[9] || 0),
      reaction_count:Number(r[10] || 0),
      source:r[11],
      day_key:r[12]
    }))
    .reverse();

  const total = rows.length;
  const pages = Math.max(1, Math.ceil(total / limit));
  const safePage = Math.min(page, pages);
  const start = (safePage - 1) * limit;
  return json_({ok:true,page:safePage,limit,total,pages,posts:rows.slice(start,start+limit)});
}

function doPost(e) {
  const p = (e && e.parameter) || {};
  if (String(p.website || '').trim()) return json_({ok:true});

  const action = clean_(p.action, 20);
  if (action !== 'create') return json_({ok:false,error:'action'});

  const channel = clean_(p.channel || 'HOT TALK', 30);
  const nickname = clean_(p.nickname || 'TESTER', CONFIG.maxNickname);
  const title = clean_(p.title, CONFIG.maxTitle);
  const body = clean_(p.body, CONFIG.maxBody);

  if (!['HOT TALK','MATCH CHAT','FAN PICKS','VIDEO LOUNGE'].includes(channel)) return json_({ok:false,error:'channel'});
  if (title.length < 2 || body.length < 2) return json_({ok:false,error:'content'});

  const fingerprint = Utilities.base64EncodeWebSafe(
    Utilities.computeDigest(
      Utilities.DigestAlgorithm.SHA_256,
      [nickname,title,body].join('|')
    )
  ).slice(0,32);
  const cache = CacheService.getScriptCache();
  if (cache.get('community:'+fingerprint)) return json_({ok:false,error:'rate'});

  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) return json_({ok:false,error:'busy'});
  try {
    const now = new Date();
    const tz = 'Asia/Seoul';
    const created = Utilities.formatDate(now, tz, 'yyyy-MM-dd HH:mm:ss');
    const dayKey = Utilities.formatDate(now, tz, 'yyyy-MM-dd');
    const postId = 'P-' + Utilities.formatDate(now, tz, 'yyyyMMddHHmmss') + '-' + Utilities.getUuid().slice(0,8).toUpperCase();

    postsSheet_().appendRow([
      postId,
      created,
      safeCell_(channel),
      safeCell_(nickname),
      safeCell_(title),
      safeCell_(body),
      '',
      'published',
      0,
      0,
      0,
      'sfandom.com',
      dayKey
    ]);
    cache.put('community:'+fingerprint, '1', CONFIG.cooldownSeconds);
    return json_({ok:true,post_id:postId,created_at_kst:created});
  } finally {
    lock.releaseLock();
  }
}

function postsSheet_() {
  const id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('SPREADSHEET_ID is not configured');
  const sheet = SpreadsheetApp.openById(id).getSheetByName(CONFIG.postsSheet);
  if (!sheet) throw new Error('POSTS sheet not found');
  return sheet;
}

function clean_(value, max) {
  return String(value || '').replace(/[\u0000-\u001F\u007F]/g, ' ').trim().slice(0, max);
}

function safeCell_(value) {
  const s = String(value || '');
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function json_(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
