"""MCP Tool Definition -> OpenAI Function Calling format"""

def mcp_to_openai_function(mcp_tool: dict) -> dict:
    """
    Convert MCP tool definition to OpenAI Function Calling format.

    MCP format:
      {name, description, inputSchema: {type: "object", properties: {...}, required: [...]}}

    OpenAI format:
      {type: "function", function: {name, description, parameters: {...}, strict: true}}
    """
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.get("name", ""),
            "description": mcp_tool.get("description", ""),
            "parameters": mcp_tool.get("inputSchema", {}),
            "strict": True,
        }
    }

def mcp_tools_to_openai(mcp_tools: list[dict]) -> list[dict]:
    """Convert a list of MCP tools to OpenAI format"""
    return [mcp_to_openai_function(t) for t in mcp_tools]
