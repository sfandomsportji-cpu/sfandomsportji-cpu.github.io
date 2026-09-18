(() => {
  'use strict';
  const root=document.getElementById('sfCommunityLobby');
  if(!root)return;

  const list=document.getElementById('sfCommunityList');
  const pager=document.getElementById('sfCommunityPagination');
  const form=document.getElementById('sfCommunityTester');
  const status=document.getElementById('sfCommunityTesterStatus');
  const PAGE_SIZE=10;
  const configuredUrl=String(root.dataset.endpoint||'').trim();
  const endpointReady=configuredUrl && !configuredUrl.includes('__SFANDOM_COMMUNITY_WEB_APP_URL__');
  let page=1,total=0,localPosts=[];

  const demo=Array.from({length:23},(_,i)=>({
    post_id:'DEMO-'+String(23-i).padStart(3,'0'),
    created_at_kst:'2026-09-'+String(19-Math.floor(i/8)).padStart(2,'0')+' '+String(2+(i%8)).padStart(2,'0')+':'+String((i*7)%60).padStart(2,'0'),
    channel:['HOT TALK','MATCH CHAT','FAN PICKS','VIDEO LOUNGE'][i%4],
    nickname:['KAIRO','TESTER','SFANDOM'][i%3],
    title:['오늘 경기에서 제일 먼저 볼 포인트','이 장면은 다시 봐도 흐름이 바뀐다','라인업 뜨면 여기서 같이 보자','영상 라운지 테스트 포스트'][i%4]+' · '+(i+1),
    comment_count:(i*3)%19,
    status:'published'
  }));

  const text=(tag,value,className)=>{
    const el=document.createElement(tag);
    if(className)el.className=className;
    el.textContent=value??'';
    return el;
  };

  const formatTime=(raw)=>{
    const s=String(raw||'');
    return s.length>=16?s.slice(5,16):s;
  };

  const renderRows=(rows,startIndex)=>{
    list.replaceChildren();
    if(!rows.length){
      list.append(text('div','아직 표시할 게시글이 없습니다.','community-empty'));
      return;
    }
    rows.forEach((post,index)=>{
      const row=document.createElement('article');
      row.className='community-row';
      row.append(
        text('span',String(startIndex+index+1).padStart(2,'0'),'community-row-num'),
        text('span',post.channel||'LOUNGE','community-row-channel')
      );
      const main=document.createElement('div');
      main.className='community-row-main';
      main.append(
        text('strong',post.title||'(제목 없음)','community-row-title'),
        text('small',(post.nickname||'ANON')+' · '+(post.status||'published'),'community-row-meta')
      );
      row.append(main,text('time',formatTime(post.created_at_kst),'community-row-time'),text('span',String(post.comment_count||0),'community-row-comments'));
      list.append(row);
    });
  };

  const renderPager=()=>{
    pager.replaceChildren();
    const pages=Math.max(1,Math.ceil(total/PAGE_SIZE));
    const make=(label,target,disabled,current=false)=>{
      const b=text('button',label,'community-page-btn');
      b.type='button';
      b.disabled=disabled;
      if(current)b.setAttribute('aria-current','page');
      b.addEventListener('click',()=>{page=target;load();});
      pager.append(b);
    };
    make('‹',Math.max(1,page-1),page===1);
    const start=Math.max(1,Math.min(page-2,pages-4));
    const end=Math.min(pages,start+4);
    for(let p=start;p<=end;p++)make(String(p),p,false,p===page);
    make('›',Math.min(pages,page+1),page===pages);
  };

  const loadRemote=async()=>{
    const url=new URL(configuredUrl);
    url.searchParams.set('action','list');
    url.searchParams.set('page',String(page));
    url.searchParams.set('limit',String(PAGE_SIZE));
    const r=await fetch(url.toString(),{method:'GET',cache:'no-store',credentials:'omit'});
    if(!r.ok)throw new Error('community '+r.status);
    const data=await r.json();
    if(!data?.ok||!Array.isArray(data.posts))throw new Error('invalid community payload');
    total=Number(data.total||0);
    renderRows(data.posts,(page-1)*PAGE_SIZE);
  };

  const loadLocal=()=>{
    const source=localPosts.length?localPosts:demo;
    total=source.length;
    const start=(page-1)*PAGE_SIZE;
    renderRows(source.slice(start,start+PAGE_SIZE),start);
  };

  const load=async()=>{
    list.setAttribute('aria-busy','true');
    try{
      if(endpointReady)await loadRemote();
      else loadLocal();
    }catch(_){
      loadLocal();
      status.textContent='클라우드 연결 실패 — 화면은 로컬 테스트 데이터로 동작 중입니다.';
    }finally{
      list.removeAttribute('aria-busy');
      renderPager();
    }
  };

  form?.addEventListener('submit',async(e)=>{
    e.preventDefault();
    const fd=new FormData(form);
    const payload={
      action:'create',
      channel:'HOT TALK',
      nickname:String(fd.get('nickname')||'').trim().slice(0,30),
      title:String(fd.get('title')||'').trim().slice(0,120),
      body:String(fd.get('body')||'').trim().slice(0,2000),
      website:String(fd.get('website')||'')
    };
    if(payload.title.length<2||payload.body.length<2){
      status.textContent='제목과 내용을 2자 이상 입력해 주세요.';
      return;
    }
    const button=form.querySelector('button');
    button.disabled=true;
    status.textContent='저장 중…';
    try{
      if(endpointReady){
        const body=new URLSearchParams(payload);
        const r=await fetch(configuredUrl,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8'},body,credentials:'omit'});
        if(!r.ok)throw new Error('save '+r.status);
        const data=await r.json();
        if(!data?.ok)throw new Error(data?.error||'save failed');
      }else{
        localPosts.unshift({
          post_id:'LOCAL-'+Date.now(),
          created_at_kst:new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Seoul',dateStyle:'short',timeStyle:'short'}).format(new Date()),
          channel:'HOT TALK',
          nickname:payload.nickname||'TESTER',
          title:payload.title,
          body:payload.body,
          comment_count:0,
          status:'published'
        });
      }
      form.reset();
      page=1;
      await load();
      status.textContent=endpointReady?'클라우드 테스트 저장 완료.':'로컬 테스트 저장 완료. Apps Script 연결 후 클라우드 저장으로 전환됩니다.';
    }catch(_){
      status.textContent='저장에 실패했습니다. 엔드포인트 연결 상태를 확인해 주세요.';
    }finally{
      button.disabled=false;
    }
  });

  load();
})();