import { DurableObject } from "cloudflare:workers";

const ALLOWED_TOPICS = new Set(["GENERAL", "MLB", "KBO", "NBA", "FOOTBALL"]);
const ALLOWED_ORIGINS = new Set([
  "https://sfandom.com",
  "https://www.sfandom.com",
  "https://sfandomsportji-cpu.github.io"
]);

function isAllowedOrigin(request) {
  const origin = request.headers.get("Origin");
  if (!origin) return false;
  if (ALLOWED_ORIGINS.has(origin)) return true;
  try {
    const url = new URL(origin);
    return url.hostname === "localhost" || url.hostname === "127.0.0.1";
  } catch {
    return false;
  }
}

function sanitizeNickname(value) {
  return String(value || "")
    .replace(/[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ ._-]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 18);
}

function cleanText(value) {
  return String(value || "").replace(/\r/g, "").trim().slice(0, 300);
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "https://sfandom.com",
      "access-control-allow-methods": "GET, OPTIONS",
      "access-control-allow-headers": "content-type"
    }
  });
}

export class ChatRoom extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.ctx.blockConcurrencyWhile(async () => {
      this.ctx.storage.sql.exec(`
        CREATE TABLE IF NOT EXISTS messages (
          id TEXT PRIMARY KEY,
          nickname TEXT NOT NULL,
          client_id TEXT NOT NULL,
          topic TEXT NOT NULL,
          text TEXT NOT NULL,
          created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_created_at
          ON messages(created_at DESC);
      `);
    });
  }

  async fetch(request) {
    if (request.headers.get("Upgrade")?.toLowerCase() !== "websocket") {
      return new Response("WebSocket upgrade required", { status: 426 });
    }

    const url = new URL(request.url);
    const nickname = sanitizeNickname(url.searchParams.get("nickname"));
    const clientId = String(url.searchParams.get("client") || "").slice(0, 80);

    if (nickname.length < 2 || !clientId) {
      return new Response("Invalid guest identity", { status: 400 });
    }

    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);

    this.ctx.acceptWebSocket(server);
    server.serializeAttachment({
      nickname,
      clientId,
      lastSentAt: 0,
      lastText: ""
    });

    const rows = this.ctx.storage.sql.exec(`
      SELECT id, nickname, client_id, topic, text, created_at
      FROM messages
      ORDER BY created_at DESC
      LIMIT 100
    `).toArray().reverse();

    const history = rows.map((row) => ({
      id: row.id,
      nickname: row.nickname,
      clientId: row.client_id,
      topic: row.topic,
      text: row.text,
      createdAt: row.created_at
    }));

    server.send(JSON.stringify({ type: "history", messages: history }));

    return new Response(null, { status: 101, webSocket: client });
  }

  async webSocketMessage(ws, rawMessage) {
    if (typeof rawMessage !== "string") return;

    let payload;
    try {
      payload = JSON.parse(rawMessage);
    } catch {
      ws.send(JSON.stringify({ type: "error", message: "잘못된 메시지 형식입니다." }));
      return;
    }

    if (payload?.type !== "message") return;

    const state = ws.deserializeAttachment() || {};
    const nickname = sanitizeNickname(state.nickname);
    const clientId = String(state.clientId || "").slice(0, 80);
    const text = cleanText(payload.text);
    const topic = ALLOWED_TOPICS.has(String(payload.topic || "").toUpperCase())
      ? String(payload.topic).toUpperCase()
      : "GENERAL";
    const now = Date.now();

    if (nickname.length < 2 || !clientId || !text) return;

    if (now - Number(state.lastSentAt || 0) < 2500) {
      ws.send(JSON.stringify({ type: "error", message: "조금만 천천히 보내 주세요." }));
      return;
    }

    if (text === state.lastText && now - Number(state.lastSentAt || 0) < 15000) {
      ws.send(JSON.stringify({ type: "error", message: "같은 메시지를 연속으로 보낼 수 없습니다." }));
      return;
    }

    const linkCount = (text.match(/https?:\/\//gi) || []).length;
    if (linkCount > 1) {
      ws.send(JSON.stringify({ type: "error", message: "링크는 한 메시지에 한 개까지만 허용합니다." }));
      return;
    }

    const message = {
      id: crypto.randomUUID(),
      nickname,
      clientId,
      topic,
      text,
      createdAt: now
    };

    this.ctx.storage.sql.exec(
      `INSERT INTO messages (id, nickname, client_id, topic, text, created_at)
       VALUES (?, ?, ?, ?, ?, ?)`,
      message.id,
      message.nickname,
      message.clientId,
      message.topic,
      message.text,
      message.createdAt
    );

    this.ctx.storage.sql.exec(`
      DELETE FROM messages
      WHERE id NOT IN (
        SELECT id FROM messages ORDER BY created_at DESC LIMIT 500
      )
    `);

    ws.serializeAttachment({
      nickname,
      clientId,
      lastSentAt: now,
      lastText: text
    });

    const frame = JSON.stringify({ type: "message", message });
    for (const peer of this.ctx.getWebSockets()) {
      try {
        peer.send(frame);
      } catch {
        try { peer.close(1011, "send failed"); } catch {}
      }
    }
  }

  async webSocketClose(ws, code, reason) {
    try { ws.close(code, reason); } catch {}
  }

  async webSocketError(ws) {
    try { ws.close(1011, "websocket error"); } catch {}
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      if (!isAllowedOrigin(request)) return new Response(null, { status: 403 });
      return new Response(null, {
        status: 204,
        headers: {
          "access-control-allow-origin": request.headers.get("Origin"),
          "access-control-allow-methods": "GET, OPTIONS",
          "access-control-allow-headers": "content-type",
          "access-control-max-age": "86400"
        }
      });
    }

    if (url.pathname === "/health") {
      return json({ ok: true, service: "sfandom-live-chat", version: "0.1.0" });
    }

    const match = url.pathname.match(/^\/room\/([a-z0-9_-]{1,40})$/i);
    if (!match) return new Response("Not found", { status: 404 });
    if (!isAllowedOrigin(request)) return new Response("Origin not allowed", { status: 403 });

    const room = match[1].toLowerCase();
    const stub = env.CHAT_ROOM.getByName(room);
    return stub.fetch(request);
  }
};
