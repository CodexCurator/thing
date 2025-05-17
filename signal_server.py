# signal_server.py
# Minimal signaling server for aiortc P2P chat on Render

import asyncio, json, websockets, os
from typing import Dict, Set

# ---------- room store -------------------------------------------------------
ROOMS: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}

async def handler(ws, _path):
    room = None
    try:
        async for raw in ws:
            msg = json.loads(raw)
            if msg["type"] == "join":
                room = msg["room"]
                ROOMS.setdefault(room, set()).add(ws)
                print(f"User joined room: {room}")
            else:  # relay to peers
                for peer in ROOMS.get(room, set()) - {ws}:
                    await peer.send(raw)
    finally:
        if room and ws in ROOMS.get(room, ()):
            ROOMS[room].discard(ws)
            print(f"User left room: {room}")
            if not ROOMS[room]:
                del ROOMS[room]

async def main():
    PORT = int(os.environ.get("PORT", 8080))
    print(f"Signaling server listening on port {PORT} …")
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
