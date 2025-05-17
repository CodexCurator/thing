#!/usr/bin/env python3
# --------------------------------------------------------------------
# signal_server.py – relay for ONE WebRTC pair
# * max_size=None  → never reject large SDPs
# * broadcasts {"type":"peers","count":N}
# * /healthz returns 200 to GET or HEAD
# --------------------------------------------------------------------
import asyncio, json, os, websockets
from typing import Set

CLIENTS: Set[websockets.WebSocketServerProtocol] = set()

async def _broadcast_peer_count():
    msg = json.dumps({"type": "peers", "count": len(CLIENTS)})
    await asyncio.gather(*(c.send(msg) for c in CLIENTS if not c.closed))

async def handler(ws, _):
    CLIENTS.add(ws)
    await _broadcast_peer_count()
    try:
        async for raw in ws:
            print(f"[server] relay {len(raw)} bytes")
            await asyncio.gather(*(o.send(raw) for o in CLIENTS - {ws}),
                                 return_exceptions=True)
    except websockets.ConnectionClosedError:
        pass
    finally:
        CLIENTS.discard(ws)
        await _broadcast_peer_count()

async def process_request(path, headers):
    if path == "/healthz":
        if headers.raw_headers[0][0].decode().split()[0] in {"GET", "HEAD"}:
            body = b"OK" if headers.raw_headers[0][0].startswith(b"GET") else b""
            return 200, [("Content-Type", "text/plain"),
                         ("Content-Length", str(len(body)))], body
    return None

async def main():
    port = int(os.environ.get("PORT", 8080))
    print(f"signalling server on :{port}")
    async with websockets.serve(handler, "0.0.0.0", port,
                                max_size=None,                 # ← unlimited
                                ping_interval=15,
                                ping_timeout=15,
                                process_request=process_request):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
