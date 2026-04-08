"""
即時監控模組
- WebSocket：儀表板頁面訂閱，有新資料時推送
- broadcast()：供其他 router 在收到資料時呼叫
"""
import json
import time
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["監控"])

# 連線中的 WebSocket 客戶端
_clients: List[WebSocket] = []


async def broadcast(event: str, data: dict):
    """向所有儀表板客戶端廣播事件"""
    msg = json.dumps({"event": event, "data": data, "ts": int(time.time() * 1000)},
                     ensure_ascii=False)
    dead = []
    for ws in _clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.remove(ws)


@router.websocket("/ws/monitor")
async def websocket_monitor(ws: WebSocket):
    await ws.accept()
    _clients.append(ws)
    try:
        while True:
            await ws.receive_text()   # 保持連線（心跳）
    except WebSocketDisconnect:
        _clients.remove(ws)
