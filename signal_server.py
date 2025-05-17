#!/usr/bin/env python3
# --------------------------------------------------------------------
# signal_server.py – ultra‑light relay for ONE chat pair
#
# * Broadcasts {"type":"peers","count":N} whenever the number of
#   connected clients changes (0‑2 only).
# * Relays every JSON line *verbatim* between the two peers.
# * GET /healthz → 200 OK  (for uptime monitors).
# * Silences “no close frame received” noise.
# --------------------------------------------------------------------
import asyncio, json, os, websockets
from typing import Set

CLIENTS: Set[websockets.WebSocketServerProtocol] = set()

async def broadcast_peer_count() -> None:
    msg = json.dumps({"type": "peers", "count": len(CLIENTS)})
    await asyncio.gather(*(c.send(msg) for c in CLIENTS if not c.closed))

async def handler(ws: websockets.WebSocketServerProtocol, _path: str):
    CLIENTS.add(ws)
    await broadcast_peer_count()
    try:
        async for raw in ws:
            # fan‑out to the *other* peer(s)
            targets = CLIENTS - {ws}
            await asyncio.gather(*(t.send(raw) for t in targets), return_exceptions=True)
    except websockets.ConnectionClosedError:
        # client vanished without a close‑frame – ignore
        pass
    finally:
        CLIENTS.discard(ws)
        await broadcast_peer_count()

# -------- plain HTTP for /healthz ----------------------------------
async def process_request(path, _headers):
    if path == "/healthz":
        body = b"OK"
        return 200, [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(body))),
        ], body
    return None  # let the WS handshake continue

# -------- main ------------------------------------------------------
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
