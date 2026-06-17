"""MCP Bridge Server - JSON-RPC 2.0 handler with FastAPI"""
import json
import logging
import traceback
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from server.tool_registry import ToolRegistry
from server.auth import AuthManager
from governance.access_control import AccessController
from governance.rate_limiter import RateLimiter
from governance.audit_log import AuditLogger
from governance.tool_validator import ToolValidator

logger = logging.getLogger("mcp-bridge")
logging.basicConfig(level=logging.INFO, format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}')

app = FastAPI(title="mcp-bridge", version="0.1.0")
registry = ToolRegistry()
auth = AuthManager()
access_ctrl = AccessController()
rate_limiter = RateLimiter()
audit = AuditLogger()
validator = ToolValidator()

# --- JSON-RPC Error Codes ---
JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
CUSTOM_TOOL_ERROR = -32000
CUSTOM_FORBIDDEN = -32001
CUSTOM_RATE_LIMITED = -32002

# --- Models ---
class JsonRpcRequest(BaseModel):
    jsonrpc: str = Field(default="2.0", pattern="^2\\.0$")
    method: str = Field(..., min_length=1)
    params: Optional[dict] = None
    id: Optional[int | str] = None

# --- Helpers ---
def make_response(result: dict, req_id: int | str | None = None) -> dict:
    return {"jsonrpc": "2.0", "result": result, "id": req_id}

def make_error(code: int, message: str, req_id: int | str | None = None, data: dict = None) -> dict:
    err = {"code": code, "message": message}
    if data:
        err["data"] = data
    return {"jsonrpc": "2.0", "error": err, "id": req_id}

# --- Error Handler ---
@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled: {traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"code": 500, "msg": "Internal error", "detail": None})

# --- JSON-RPC Endpoint ---
@app.post("/mcp")
async def mcp_handler(request: JsonRpcRequest, raw: Request):
    method = request.method
    params = request.params or {}
    req_id = request.id
    user = auth.get_user_from_request(raw)

    logger.info(f"MCP call: method={method}, user={user}")

    try:
        # --- tools/list ---
        if method == "tools/list":
            tools = registry.list_tools(user=user)
            return JSONResponse(content=make_response({"tools": tools}, req_id))

        # --- tools/call ---
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                return JSONResponse(content=make_error(JSONRPC_INVALID_PARAMS, "Missing tool name", req_id))

            # Access control
            if not access_ctrl.check(user, tool_name, arguments):
                audit.log(user, tool_name, arguments, None, 0, "denied")
                return JSONResponse(content=make_error(CUSTOM_FORBIDDEN, "Forbidden", req_id))

            # Rate limit
            if not rate_limiter.check(user, tool_name):
                audit.log(user, tool_name, arguments, None, 0, "rate_limited")
                return JSONResponse(content=make_error(CUSTOM_RATE_LIMITED, "Rate limit exceeded", req_id))

            # Validate input
            tool = registry.get(tool_name)
            if tool and not validator.validate_input(tool_name, arguments):
                return JSONResponse(content=make_error(JSONRPC_INVALID_PARAMS, "Invalid tool parameters", req_id))

            # Execute tool
            try:
                result = await registry.invoke(tool_name, arguments)
                audit.log(user, tool_name, arguments, result, 0, "success")
                return JSONResponse(content=make_response({"content": [{"type": "text", "text": json.dumps(result)}]}, req_id))
            except Exception as e:
                audit.log(user, tool_name, arguments, str(e), 0, "error")
                return JSONResponse(content=make_error(CUSTOM_TOOL_ERROR, str(e), req_id))

        # --- initialize ---
        elif method == "initialize":
            return JSONResponse(content=make_response({
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mcp-bridge", "version": "0.1.0"}
            }, req_id))

        # --- resources/list ---
        elif method == "resources/list":
            return JSONResponse(content=make_response({"resources": []}, req_id))

        # --- prompts/list ---
        elif method == "prompts/list":
            return JSONResponse(content=make_response({"prompts": []}, req_id))

        else:
            return JSONResponse(content=make_error(JSONRPC_METHOD_NOT_FOUND, f"Method not found: {method}", req_id))

    except Exception as e:
        logger.error(f"Handler error: {traceback.format_exc()}")
        return JSONResponse(content=make_error(JSONRPC_INVALID_REQUEST, str(e), req_id))

# --- REST API (for AgentForge integration) ---
class InvokeInput(BaseModel):
    tool: str = Field(..., min_length=1)
    params: dict = Field(default={})
    user: str = Field(default="agent")

@app.post("/api/v1/tools/invoke")
async def invoke_tool(input: InvokeInput):
    """Invoke a tool (called by AgentForge)"""
    try:
        result = await registry.invoke(input.tool, input.params)
        audit.log(input.user, input.tool, input.params, result, 0, "success")
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail={"code": 400, "msg": str(e)})

@app.get("/api/v1/tools/discover")
async def discover_tools(source: str = "mcp", user: str = "agent"):
    """Discover tools from an MCP source"""
    return {"tools": registry.list_tools(user=user)}

@app.post("/api/v1/tools/register")
async def register_tool(
    name: str, description: str, schema: dict,
    handler_ref: str | None = None
):
    """Register a local tool"""
    registry.register(name, description, schema, handler_ref)
    logger.info(f"Tool registered: {name}")
    return {"status": "ok", "tool": name}

@app.get("/api/v1/audit/logs")
async def get_audit_logs(limit: int = 100, offset: int = 0):
    """Query audit logs"""
    return {"logs": audit.query(limit, offset)}

@app.get("/health")
async def health():
    return {"status": "ok", "tools": registry.count(), "model": "mcp-bridge"}

@app.get("/api/v1/health")
async def health_v1():
    return await health()
