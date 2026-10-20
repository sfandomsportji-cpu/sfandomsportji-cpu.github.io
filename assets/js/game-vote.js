/* SFANDOM: 경기별 한 줄 투표. 표 집계 테이블이 없거나 실패하면 투표 칸을 조용히 숨깁니다. */
(() => {
  "use strict";
  const cfg = window.SFANDOM?.supabase;
  const boxes = [...document.querySelectorAll("[data-vote]")];
  if (!boxes.length || !cfg?.url || !cfg.key) return;
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  let voter = store.get("sf-voter");
  if (!voter) {
    voter = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2));
    store.set("sf-voter", voter);
  }
  const req = async (path, init = {}) => {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 10000);
    try {
      const r = await fetch(cfg.url + path, { ...init, credentials: "omit", cache: "no-store", signal: ctl.signal,
        headers: { apikey: cfg.key, Accept: "application/json", ...(init.headers || {}) } });
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r;
    } finally { clearTimeout(t); }
  };
  async function counts(id) {
    const r = await req("/rest/v1/game_vote_counts?select=side,votes&game_id=eq." + encodeURIComponent(id));
    const o = { away: 0, home: 0 };
    (await r.json()).forEach(x => { if (x.side in o) o[x.side] = x.votes; });
    return o;
  }
  function paint(box, c, mine) {
    const sum = c.away + c.home;
    ["away", "home"].forEach(side => {
      const b = box.querySelector(`[data-side="${side}"]`);
      const pct = sum ? Math.round(c[side] * 100 / sum) : 0;
      b.style.setProperty("--p", pct + "%");
      b.querySelector("em").textContent = pct + "%";
      b.dataset.mine = mine === side ? "1" : "0";
    });
    box.dataset.state = "done";
    box.querySelector("small").textContent = `${sum}명 참여` + (mine ? " · 내 선택 표시" : "");
  }
  boxes.forEach(async box => {
    const id = box.dataset.vote;
    const key = "sf-vote:" + id;
    const readonly = box.dataset.readonly === "1";
    try {
      const c = await counts(id);
      box.hidden = false;
      const mine = store.get(key);
      if (mine || readonly) { paint(box, c, mine); return; }
      box.dataset.state = "open";
      box.querySelectorAll("[data-side]").forEach(b => b.addEventListener("click", async e => {
        e.preventDefault();
        const side = b.dataset.side;
        box.dataset.state = "busy";
        try {
          await req("/rest/v1/game_votes", { method: "POST", headers: { "Content-Type": "application/json", Prefer: "return=minimal" },
            body: JSON.stringify({ game_id: id, side, voter }) });
        } catch (err) { /* 이미 투표했거나 일시 오류: 집계만 보여 준다 */ }
        store.set(key, side);
        try { paint(box, await counts(id), side); } catch (err) { box.hidden = true; }
      }));
    } catch (e) { box.hidden = true; }
  });
})();
