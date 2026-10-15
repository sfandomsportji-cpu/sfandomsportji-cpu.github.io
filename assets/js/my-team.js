/* SFANDOM: 내 팀 고르기. 고른 팀은 이 브라우저에만 저장되고, 오늘 분석 줄에서 맨 위로 올라와 강조됩니다. */
(() => {
  "use strict";
  const bar = document.querySelector("[data-my]");
  const board = document.querySelector(".an-board");
  if (!bar || !board) return;
  const items = [...board.querySelectorAll(".an-item[data-teams]")];
  const names = [...new Set(items.flatMap(i => i.dataset.teams.split("|")))];
  if (!names.length) return;
  const K = "sf-my-team";
  const get = () => { try { return localStorage.getItem(K) || ""; } catch (e) { return ""; } };
  const put = v => { try { v ? localStorage.setItem(K, v) : localStorage.removeItem(K); } catch (e) {} };
  const order = items.slice();
  const chips = bar.querySelector("[data-my-chips]");
  function apply(team) {
    const mine = it => !!team && it.dataset.teams.split("|").includes(team);
    order.forEach(it => { it.dataset.mine = mine(it) ? "1" : "0"; });
    [...order].sort((a, b) => (b.dataset.mine - a.dataset.mine) || (order.indexOf(a) - order.indexOf(b)))
      .forEach(it => board.appendChild(it));
    chips.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.team === team)));
  }
  names.forEach(n => {
    const b = document.createElement("button");
    b.type = "button"; b.dataset.team = n; b.textContent = n;
    b.addEventListener("click", () => { const next = get() === n ? "" : n; put(next); apply(next); });
    chips.append(b);
  });
  bar.hidden = false;
  const saved = get();
  apply(names.includes(saved) ? saved : "");
})();
