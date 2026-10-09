/* SFANDOM threaded discussions. Optional enhancement, isolated from the core board. */
(() => {
  "use strict";
  const board = document.querySelector("[data-board][data-size]"); 
  if (!board || !board.querySelector("[data-board-form]")) return;
  const list = board.querySelector("[data-board-list]");
  const cfg = (window.SFANDOM || {}).supabase || {};
  if (!list || !cfg.url || !cfg.key) return;
  const validId = x => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(x || "");
  const el = (tag, cls, value) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (value !== undefined) e.textContent = String(value);
    return e;
  };
  const button = (label, cls) => {
    const b = el("button", cls, label); b.type = "button"; return b;
  };
  const request = async (path, init = {}) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
      const r = await fetch(cfg.url + path, {
        ...init, signal: controller.signal, credentials: "omit", cache: "no-store",
        headers: { apikey: cfg.key, Accept: "application/json", ...(init.headers || {}) }
      });
      if (!r.ok) { const e = Error("http_" + r.status); e.status = r.status; throw e; }
      return r;
    } finally { clearTimeout(timer); }
  };
  const send = async data => {
    await request("/functions/v1/community-interact", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
  };
  const errorText = e => e && e.status === 429 ? "잠시 후 다시 작성해 주세요." :
    e && e.status === 404 ? "해당 글이 더 이상 공개되지 않습니다." :
    "연결이 원활하지 않습니다. 다시 시도해 주세요.";

  const makeReport = (type, id, mount, note) => {
    mount.replaceChildren();
    const box = el("div", "ct-report-picker");
    const select = el("select");
    select.setAttribute("aria-label", "신고 사유");
    [["spam","광고·도배"],["abuse","욕설·비하"],["privacy","개인정보"],["other","기타"]]
      .forEach(pair => { const option = el("option", null, pair[1]); option.value = pair[0]; select.append(option); });
    const sendBtn = button("신고 제출", "ct-small");
    const close = button("취소", "ct-small");
    sendBtn.addEventListener("click", async () => {
      sendBtn.disabled = true;
      try {
        await send({ action:"report", target_type:type, target_id:id, reason:select.value });
        note("신고가 접수되었습니다.");
        mount.replaceChildren();
      } catch (err) { note(errorText(err)); sendBtn.disabled = false; }
    });
    close.addEventListener("click", () => mount.replaceChildren());
    box.append(select, sendBtn, close);
    mount.append(box);
  };
  function attach(card) {
    if (card.dataset.ctReady) return;
    const id = card.dataset.postId;
    if (!validId(id)) return;
    const postBody = card.querySelector(".post-body");
    if (!postBody) return;
    card.dataset.ctReady = "1";
    const BATCH = 40;
    let rows = [], cursor = null, hasMore = true, busy = false, open = false, loadEpoch = 0;
    const actions = el("div", "ct-actions");
    const show = button("댓글 보기 · 답글 쓰기", "ct-open");
    show.setAttribute("aria-expanded", "false");
    const reportPost = button("신고", "ct-small");
    const reportSlot = el("span", "ct-report-slot");
    const panel = el("section", "ct-panel");
    panel.hidden = true; panel.setAttribute("aria-label", "댓글 대화");
    const notice = el("p", "ct-status"); notice.setAttribute("role","status"); 
    const comments = el("div", "ct-comments");
    const composer = el("div", "ct-top-composer");
    const more = button("이전 댓글 더 보기", "ct-more");
    more.hidden = true;
    panel.append(notice, comments, composer, more);
    actions.append(show, reportPost, reportSlot);
    // Keep discussion inside the existing vertical post body; the article is a horizontal flex row.
    postBody.append(actions, panel);
    const say = text => { notice.textContent = text; };

    function writeForm(target, nickname, mount) {
      mount.replaceChildren();
      const form = el("form", "ct-form");
      const title = el("div", "ct-form-title", target ? "↳ " + nickname + "님에게 답글" : "새 댓글 작성");
      const nick = el("input"); nick.name="nickname"; nick.maxLength=30;
      nick.placeholder="닉네임 (선택)"; nick.setAttribute("aria-label","닉네임");
      const body = el("textarea"); body.name="body"; body.maxLength=2000;
      body.rows=2; body.required=true; body.placeholder="서로 존중하며 자유롭게 이야기해 주세요.";
      body.setAttribute("aria-label","댓글 내용");
      const footer = el("div", "ct-form-actions");
      const submit = el("button", "ct-send", "댓글 등록"); submit.type="submit";
      footer.append(submit);
      if(target) {
        const cancel=button("답글 취소","ct-small");
        cancel.addEventListener("click", () => { mount.replaceChildren(); writeForm(null,"",composer); });
        footer.append(cancel);
      }
      form.append(title,nick,body,footer);
      form.addEventListener("submit", async e => {
        e.preventDefault();
        const text=body.value.trim();
        if(text.length<2){say("댓글을 두 글자 이상 적어 주세요.");return;}
        submit.disabled=true; say("댓글을 등록하고 있어요…");
        try {
          await send({ action:"comment", post_id:id, parent_id:target || null,
            nickname:nick.value.trim() || "ANON", body:text });
          say("댓글이 등록되었습니다.");
          rows=[]; cursor=null; hasMore=true;
          await load(true);
          writeForm(null,"",composer);
        } catch(err) {say(errorText(err));}
        finally {submit.disabled=false;}
      });
      mount.append(form);
    }

    function draw() {
      if(!rows.length){comments.replaceChildren(el("p","ct-empty","첫 댓글을 남겨보세요."));return;}
      const fragment = document.createDocumentFragment();
      const byId = new Map(rows.map(x=>[x.id,x]));
      const children = new Map();
      const push=(k,x)=>{if(!children.has(k))children.set(k,[]);children.get(k).push(x);};
      for(const r of rows) push(r.parent_id && byId.has(r.parent_id) ? r.parent_id : "root",r);
      const stack=(children.get("root")||[]).slice().reverse().map(x=>({x,depth:0}));
      const visited=new Set();
      while(stack.length){
        const cur=stack.pop(), r=cur.x;
        if(visited.has(r.id)) continue;
        visited.add(r.id);
        const node=el("div","ct-comment");
        // CSS caps the horizontal indent further on narrow screens, without losing reply depth.
        node.style.setProperty("--ct-indent", (Math.min(cur.depth,5)*14) + "px");
        node.id="comment-"+r.id;
        const meta=el("div","ct-meta");
        const who=el("strong",null,r.nickname || "ANON");
        const when=el("span",null,r.created_at ? new Date(r.created_at).toLocaleString("ko-KR",{timeZone:"Asia/Seoul",month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"}) : "");
        meta.append(who,when);
        if(r.parent_id && !byId.has(r.parent_id)) meta.append(el("span","ct-parent-note","↳ 이전 댓글에 대한 답글"));
        const content=el("p","ct-message",r.body || "");
        const bar=el("div","ct-comment-actions");
        const reply=button("답글","ct-small");
        const report=button("신고","ct-small");
        const reportHere=el("span","ct-report-slot");
        const replyHere=el("div","ct-reply-composer");
        reply.addEventListener("click",()=>{writeForm(r.id,r.nickname || "ANON",replyHere);replyHere.querySelector("textarea")?.focus();});
        report.addEventListener("click",()=>makeReport("comment",r.id,reportHere,say));
        bar.append(reply,report,reportHere);
        node.append(meta,content,bar,replyHere);
        fragment.append(node);
        const kids=children.get(r.id)||[];
        for(let i=kids.length-1;i>=0;i--)stack.push({x:kids[i],depth:cur.depth+1});
      }
      const unmatched=rows.filter(r=>!visited.has(r.id));
      if(unmatched.length) fragment.append(el("p","ct-status","일부 답글의 연결을 확인하지 못했습니다."));
      comments.replaceChildren(fragment);
    }

    async function load(reset=false){
      if(busy) return;
      if(!reset && !hasMore) return;
      busy=true; more.disabled=true;
      say("댓글을 불러오는 중…");
      const epoch=++loadEpoch;
      const before = reset ? null : cursor;
      try {
        const query = new URLSearchParams({
          select:"id,post_id,parent_id,nickname,body,created_at",
          post_id:"eq."+id, status:"eq.published",
          order:"created_at.desc,id.desc", limit:String(BATCH)
        });
        // Keyset pagination is stable if new comments arrive while an older page is requested.
        if(before) query.set("or", "(created_at.lt."+before.created_at+
          ",and(created_at.eq."+before.created_at+",id.lt."+before.id+"))");
        const res=await request("/rest/v1/comments?"+query.toString());
        const batch=await res.json();
        if(epoch!==loadEpoch) return;
        if(reset){rows=[];cursor=null;}
        const known = new Set(rows.map(r=>r.id));
        for(const row of batch) if(!known.has(row.id)){rows.push(row);known.add(row.id);}
        if(batch.length) cursor = { created_at:batch[batch.length-1].created_at, id:batch[batch.length-1].id };
        hasMore=batch.length===BATCH;
        draw();
        say(rows.length + "개 댓글 · 댓글에 다시 답글을 달 수 있어요.");
      }catch(err){say(errorText(err));}
      finally{busy=false;more.disabled=false;more.hidden=!hasMore;}
    }
    show.addEventListener("click",()=>{
      open=!open; panel.hidden=!open;
      show.setAttribute("aria-expanded",String(open));
      show.textContent=open?"대화 접기":"댓글 보기 · 답글 쓰기";
      if(open && rows.length===0){writeForm(null,"",composer);load(true);}
    });
    reportPost.addEventListener("click",()=>makeReport("post",id,reportSlot,say));
    more.addEventListener("click",()=>load(false));
  }

  const decorate=()=>list.querySelectorAll("article.post[data-post-id]").forEach(attach);
  new MutationObserver(decorate).observe(list,{childList:true});
  decorate();
})();