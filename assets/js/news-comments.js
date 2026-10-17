/* SFANDOM: 기사 한 편당 토론 하나. 기사 바로 밑에 댓글·답글을 보여 주고, FAN BOARD 전체 이야기에도 같은 글로 올라갑니다.
   - 뉴스: 기존 서버 동작(news_comment)으로 토론 글이 만들어지고 source_url 로 찾습니다.
   - 분석·매거진: 팬 보드와 같은 글쓰기 기능으로 "[분석 토론] 기사 제목" 글 하나를 만들고 제목으로 찾습니다.
   댓글·답글 화면은 community-thread.js 의 것을 그대로 씁니다. */
(() => {
  "use strict";
  const box = document.querySelector("[data-news-comments]");
  const cfg = window.SFANDOM?.supabase;
  if (!box || !cfg?.url || !cfg.key) return;
  const path = box.dataset.articlePath || "";
  const kind = box.dataset.articleKind || "news";
  const anchorTitle = box.dataset.articleTitle || "";
  const mount = box.querySelector("[data-discussion-mount]");
  const status = box.querySelector("[data-news-comment-status]");
  const el = (tag, cls, txt) => { const n = document.createElement(tag); if (cls) n.className = cls; if (txt !== undefined) n.textContent = txt; return n; };
  const say = t => { if (status) status.textContent = t; };
  const req = async (url, init = {}) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
      const r = await fetch(cfg.url + url, { ...init, headers: { apikey: cfg.key, Accept: "application/json", ...(init.headers || {}) }, credentials: "omit", cache: "no-store", signal: controller.signal });
      if (!r.ok) { const e = Error("HTTP " + r.status); e.status = r.status; throw e; }
      return r;
    } finally { clearTimeout(timer); }
  };
  const post = (fn, data) => req("/functions/v1/" + fn, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

  const findQuery = () => kind === "news"
    ? "source_url=eq." + encodeURIComponent(path)
    : "title=eq." + encodeURIComponent(anchorTitle);
  async function findAnchor() {
    const r = await req("/rest/v1/posts?select=id&status=eq.published&" + findQuery() + "&order=created_at.asc&limit=1");
    const rows = await r.json();
    return Array.isArray(rows) && rows.length ? rows[0].id : null;
  }

  let form = null, busy = false;
  function showThread(id) {
    if (form) { form.remove(); form = null; }
    mount.replaceChildren();
    const card = el("div", "at-card");
    card.dataset.postId = id;
    card.dataset.threadScope = "";
    card.append(el("div", "post-body"));
    mount.append(card);
    if (window.SFANDOM_THREAD?.attach) window.SFANDOM_THREAD.attach(card);
    else mount.append(el("p", "news-comment-empty", "댓글 화면을 불러오지 못했습니다. 새로고침해 주세요."));
    const link = box.querySelector("[data-news-comment-link]");
    if (link) { link.href = "/community/#comments-" + id; link.hidden = false; }
  }

  function showForm() {
    mount.replaceChildren(el("p", "news-comment-empty", "첫 의견을 남겨보세요. 전체 이야기에도 함께 게시됩니다."));
    form = el("form");
    form.noValidate = true;
    form.setAttribute("data-news-comment-form", "");
    const nick = el("input"); nick.name = "nickname"; nick.maxLength = 30; nick.placeholder = "닉네임 (선택)"; nick.setAttribute("aria-label", "닉네임");
    const body = el("textarea"); body.name = "body"; body.maxLength = 2000; body.required = true; body.setAttribute("aria-label", "댓글 내용"); body.placeholder = "이 글에 대한 생각을 남겨 주세요.";
    const hp = el("label", "hp"); hp.setAttribute("aria-hidden", "true"); hp.append("website");
    const hpIn = el("input"); hpIn.name = "website"; hpIn.tabIndex = -1; hpIn.autocomplete = "off"; hp.append(hpIn);
    const act = el("div", "nc-actions");
    const btn = el("button", "pill", "댓글 등록"); btn.type = "submit";
    act.append(btn);
    form.append(nick, body, hp, act);
    form.addEventListener("submit", async e => {
      e.preventDefault();
      if (busy) return;
      if (String(hpIn.value || "").trim()) return;
      const nickname = String(nick.value || "").trim().slice(0, 30) || "ANON";
      const text = String(body.value || "").trim();
      if (text.length < 2 || text.length > 2000) return say("댓글은 2~2000자로 작성해 주세요.");
      busy = true; btn.disabled = true; say("댓글을 등록하고 있어요…");
      try {
        if (kind === "news") {
          const res = await post("community-manage", { action: "news_comment", article_path: path, nickname, body: text });
          const data = await res.json();
          if (!data.ok) throw Error("not_saved");
        } else {
          let id = await findAnchor();
          if (!id) {
            await post("community-post", { nickname, title: anchorTitle, body: "기사 의견 모음 · " + location.origin + path });
            id = await findAnchor();
          }
          if (!id) throw Error("anchor_missing");
          await post("community-interact", { action: "comment", post_id: id, parent_id: null, nickname, body: text });
        }
        say("댓글이 저장되었습니다.");
        const id = await findAnchor();
        if (id) showThread(id);
        else say("댓글은 저장되었습니다. 목록 조회가 지연되고 있습니다. 새로고침으로 확인해 주세요.");
      } catch (err) {
        say(err.status === 429 ? "잠시 후 다시 댓글을 남겨 주세요." : "등록 상태를 확인하지 못했습니다. 중복 작성하지 말고 새로고침해 확인해 주세요.");
      } finally { busy = false; btn.disabled = false; }
    });
    mount.append(form);
  }

  (async () => {
    try {
      const id = await findAnchor();
      if (id) showThread(id); else showForm();
    } catch (_) {
      mount.replaceChildren(el("p", "news-comment-empty", "댓글을 불러오지 못했습니다. 새로고침 후 다시 확인해 주세요."));
    }
  })();
})();
