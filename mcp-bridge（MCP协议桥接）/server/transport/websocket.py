"""WebSocket transport for bidirectional MCP communication"""
from fastapi import WebSocket

async def ws_handler(websocket: WebSocket):
    """Handle MCP requests over WebSocket"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # Process MCP request and send response
            response = {"jsonrpc": "2.0", "result": {"echo": data}, "id": data.get("id")}
            await websocket.send_json(response)
    except Exception:
        pass
