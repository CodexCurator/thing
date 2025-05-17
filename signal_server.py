#!/usr/bin/env python3
"""
Minimal, room‑less signalling server for aiortc P2P chat.
• Listens on ws://0.0.0.0:$PORT  (Render sets $PORT, default 8080)
• Relays every JSON message to the *other* connected client(s)
• Emits {"type":"peers","count":N} whenever the number of clients changes
• Replies “OK” to GET / and /health  →  works with UptimeRobot
"""
import asyncio, json, os, websockets
from typing import Set

CLIENTS: Set[websockets.WebSocketServerProtocol] = set()

# ── helpers ────────────────────────────────────────────────────────────
async def broadcast(raw: str, *, exclude: Set = frozenset()):
    """Send raw string to all clients except those in *exclude*."""
    if CLIENTS:
        await asyncio.gather(
            *[c.send(raw) for c in CLIENTS - exclude],
            return_exceptions=True,     # ignore broken pipes
        )

async def notify_peers():
    """Tell everyone how many peers are currently connected."""
    await broadcast(json.dumps({"type": "peers", "count": len(CLIENTS)}))

# ── main handler ───────────────────────────────────────────────────────
async def handler(ws, _path):
    CLIENTS.add(ws)
    await notify_peers()
    try:
        async for raw in ws:            # just relay everything
            await broadcast(raw, exclude={ws})
    finally:
        CLIENTS.discard(ws)
        await notify_peers()

# ── HTTP “health check” (Render & UptimeRobot ping this) ───────────────
async def process_request(path, _hdrs):
    if path in ("/", "/health"):
        return 200, [("Content-Type", "text/plain")], b"OK\n"
    return None                         # continue WebSocket handshake

# ── entry‑point ────────────────────────────────────────────────────────
async def main():
    port = int(os.getenv("PORT", "8080"))
    print(f"Signalling server listening on 0.0.0.0:{port}")
    async with websockets.serve(
        handler,
        host="0.0.0.0",
        port=port,
        ping_interval=20,
        ping_timeout=20,
        process_request=process_request,
    ):
        await asyncio.Future()          # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
