#!/usr/bin/env python3
# --------------------------------------------------------------------
# signal_server.py – ultra‑small relay for ONE WebRTC pair
#
# • Keeps at most two WebSocket clients; broadcasts {"type":"peers"} on
#   every join/leave so the GUI knows when both are present.
# • Relays all JSON messages verbatim between the two peers.
# • GET or HEAD  /healthz  → 200 OK   (for uptime monitors).
# • Silences “no close frame received” noise.
#
#   pip install websockets
#   python signal_server.py             # local (port 8080)
#   # Render will provide $PORT env var automatically
# --------------------------------------------------------------------
import asyncio, json, os, websockets
from typing import Set

CLIENTS: Set[websockets.WebSocketServerProtocol] = set()

async def _broadcast_peer_count() -> None:
    msg = json.dumps({"type": "peers", "count": len(CLIENTS)})
    await asyncio.gather(*(c.send(msg) for c in CLIENTS if not c.closed))

async def handler(ws: websockets.WebSocketServerProtocol, _path: str):
    CLIENTS.add(ws)
    await _broadcast_peer_count()
    try:
        async for raw in ws:                          # relay everything
            others = CLIENTS - {ws}
            await asyncio.gather(*(o.send(raw) for o in others),
                                 return_exceptions=True)
    except websockets.ConnectionClosedError:
        pass                                          # ignore noisy close errors
    finally:
        CLIENTS.discard(ws)
        await _broadcast_peer_count()

# ---------- plain HTTP for /healthz (HEAD or GET) -------------------
async def process_request(path, request_headers):
    if path == "/healthz":
        # websockets exposes the first request line in raw_headers[0][0]
        method = request_headers.raw_headers[0][0].decode().split()[0]
        if method in {"GET", "HEAD"}:
            body = b"OK" if method == "GET" else b""
            return 200, [
                ("Content-Type", "text/plain"),
                ("Content-Length", str(len(body))),
            ], body
    return None  # let WebSocket handshake continue

# ---------- main ----------------------------------------------------
async def main():
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
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
