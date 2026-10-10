/* SFANDOM: one actual discussion per news article, shared with the fan board. */
(() => {
  "use strict";
  const box=document.querySelector("[data-news-comments]");
  const cfg=window.SFANDOM?.supabase;
  if(!box||!cfg?.url||!cfg.key)return;
  const path=box.dataset.articlePath||"";
  if(!/^\/news\/\d{4}\/\d{2}\/[a-z0-9-]+\/$/.test(path))return;
  const form=box.querySelector("[data-news-comment-form]");
  const status=box.querySelector("[data-news-comment-status]");
  const list=box.querySelector("[data-news-comment-list]");
  const discussion=box.querySelector("[data-news-comment-link]");
  const el=(tag,cls,txt)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(txt!==undefined)n.textContent=txt;return n};
  const req=async(url,init={})=>{
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),12000);
    try{
      const r=await fetch(cfg.url+url,{...init,headers:{apikey:cfg.key,Accept:"application/json",...(init.headers||{})},credentials:"omit",cache:"no-store",signal:controller.signal});
      if(!r.ok){const e=Error("HTTP "+r.status);e.status=r.status;throw e}
      return r;
    }finally{clearTimeout(timer)}
  };
  const say=t=>{if(status)status.textContent=t};
  let busy=false;
  async function refresh(){
    try{
      const threads=await req("/rest/v1/posts?select=id&status=eq.published&source_url=eq."+encodeURIComponent(path)+"&limit=1");
      const items=await threads.json();
      if(!items.length){
        list.replaceChildren(el("p","news-comment-empty","첫 의견을 남겨보세요. 전체 이야기에도 함께 게시됩니다."));
        discussion.hidden=true;
        return true;
      }
      const id=items[0].id;
      discussion.href="/community/#comments-"+id;
      discussion.hidden=false;
      const res=await req("/rest/v1/comments?select=id,nickname,body,created_at&post_id=eq."+id+"&status=eq.published&order=created_at.desc&limit=10");
      const comments=await res.json();
      list.replaceChildren();
      if(!comments.length)list.append(el("p","news-comment-empty","아직 의견이 없습니다."));
      for(const item of comments){
        const card=el("div","news-comment-item");
        const meta=el("div","news-comment-meta");
        const when=item.created_at?new Date(item.created_at).toLocaleString("ko-KR",{timeZone:"Asia/Seoul",month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"}):"";
        meta.append(el("strong","",item.nickname||"ANON"),el("span","",when));
        const body=el("p","",item.body||"");
        card.append(meta,body);
        list.append(card);
      }
      return true;
    }catch(err){
      if(!list.querySelector(".news-comment-item"))list.replaceChildren(el("p","news-comment-empty","댓글을 불러오지 못했습니다. 새로고침 후 다시 확인해 주세요."));
      return false;
    }
  }
  form?.addEventListener("submit",async e=>{
    e.preventDefault();
    if(busy)return;
    const fd=new FormData(form);
    if(String(fd.get("website")||"").trim())return;
    const nickname=String(fd.get("nickname")||"").trim().slice(0,30)||"ANON";
    const body=String(fd.get("body")||"").trim();
    if(body.length<2||body.length>2000)return say("댓글은 2~2000자로 작성해 주세요.");
    busy=true;
    const submit=form.querySelector("[type=submit]");
    if(submit)submit.disabled=true;
    say("댓글을 등록하고 있어요…");
    try{
      const res=await req("/functions/v1/community-manage",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"news_comment",article_path:path,nickname,body})});
      const data=await res.json();
      if(!data.ok)throw Error("not_saved");
      form.reset();
      say("댓글이 저장되었습니다. 전체 이야기에서도 함께 볼 수 있습니다.");
      const ok=await refresh();
      if(!ok)say("댓글은 저장되었지만 목록 조회가 지연되고 있습니다. 새로고침으로 확인해 주세요.");
    }catch(err){
      say(err.status===429?"잠시 후 다시 댓글을 남겨 주세요.":"등록 상태를 확인하지 못했습니다. 중복 작성하지 말고 새로고침해 확인해 주세요.");
    }finally{busy=false;if(submit)submit.disabled=false}
  });
  refresh();
})();