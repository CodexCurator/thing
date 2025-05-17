#!/usr/bin/env python3
# --------------------------------------------------------------------
# signal_server.py  –  ultra‑small relay for ONE pair of WebRTC peers
#
# • Keeps a global set of connected WebSocket clients (max 2).
# • Whatever JSON one peer sends is forwarded verbatim to the other.
# • GET /healthz  →  200 OK   (handy for uptime monitors).
#
#   pip install websockets
#   python signal_server.py            # runs on :8080 locally
#   PORT=10000 python signal_server.py # Render will provide $PORT
# --------------------------------------------------------------------
import asyncio, json, os, websockets
from typing import Set

CLIENTS: Set[websockets.WebSocketServerProtocol] = set()

async def handler(ws: websockets.WebSocketServerProtocol, path: str):
    """
    Runs for each WebSocket connection.  Simply relays every message to the
    *other* connected client (if any).
    """
    CLIENTS.add(ws)
    print(f"[+] client connected  (total={len(CLIENTS)})")
    try:
        async for msg in ws:
            # forward to everyone except the sender
            others = CLIENTS - {ws}
            await asyncio.gather(*(peer.send(msg) for peer in others))
    finally:
        CLIENTS.discard(ws)
        print(f"[-] client disconnected (total={len(CLIENTS)})")

# ---- plain HTTP handler ----------------------------------------------------
async def process_request(path, _request_headers):
    """
    Anything hitting GET /healthz gets a fast 200 OK so uptime monitors
    won't see a 400 Bad Request.
    """
    if path == "/healthz":
        body = b"OK"
        return 200, [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(body)))
        ], body
    # For all other paths let the WebSocket handshake continue.
    return None

# ---- main ------------------------------------------------------------------
async def main() -> None:
    port = int(os.environ.get("PORT", 8080))
    print(f"Signalling server listening on :{port}")
    async with websockets.serve(
        handler,
        "0.0.0.0",
        port,
        ping_interval=15,
        ping_timeout=15,
        process_request=process_request,
    ):
        await asyncio.Future()           # run forever

if __name__ == "__main__":
    asyncio.run(main())
