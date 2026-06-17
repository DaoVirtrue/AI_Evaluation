"""stdio transport for local MCP communication"""
import sys
import json
import asyncio

async def run_stdio(handler):
    """Run MCP server over stdio (for local Claude Code integration)"""
    loop = asyncio.get_event_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            request = json.loads(line.strip())
            response = await handler(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps({"error": {"code": -32700, "message": "Parse error"}}) + "\n")
            sys.stdout.flush()
        except Exception:
            break
