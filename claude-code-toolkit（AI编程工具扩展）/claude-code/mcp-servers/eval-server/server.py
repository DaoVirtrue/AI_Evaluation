"""MCP Server: AgentEval queries"""
from fastapi import FastAPI
import httpx, json

app = FastAPI(); EVAL_API = "http://localhost:8000/api/v1"

@app.post("/mcp")
async def mcp(request: dict):
    method = request.get("method")
    if method == "tools/list":
        return {"tools": [
            {"name": "query_eval", "description": "Query evaluation results"},
            {"name": "list_datasets", "description": "List test datasets"},
            {"name": "get_report", "description": "Get evaluation report"},
        ]}
    if method == "tools/call":
        name = request.get("params", {}).get("name")
        if name == "query_eval":
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{EVAL_API}/evaluations")
                return {"content": [{"type": "text", "text": r.text}]}
    return {"error": {"code": -32601, "message": "Not implemented"}}

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, port=8100)
