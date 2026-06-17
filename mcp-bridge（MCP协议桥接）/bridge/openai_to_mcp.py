"""OpenAI Function Calling -> MCP tool definition"""

def openai_to_mcp_function(openai_func: dict) -> dict:
    """
    Convert OpenAI Function Calling format to MCP tool definition.

    OpenAI format:
      {type: "function", function: {name, description, parameters: {...}, strict: true}}

    MCP format:
      {name, description, inputSchema: {...}}
    """
    fn = openai_func.get("function", openai_func)
    return {
        "name": fn.get("name", ""),
        "description": fn.get("description", ""),
        "inputSchema": fn.get("parameters", {}),
    }

def openai_tools_to_mcp(openai_tools: list[dict]) -> list[dict]:
    """Convert a list of OpenAI functions to MCP format"""
    return [openai_to_mcp_function(t) for t in openai_tools]
