"""Anthropic Tool Use <-> MCP bidirectional conversion"""

def anthropic_to_mcp(anthropic_tool: dict) -> dict:
    """
    Convert Anthropic Tool Use definition to MCP format.

    Anthropic format:
      {name, description, input_schema: {type: "object", properties: {...}, required: [...]}}

    MCP format:
      {name, description, inputSchema: {...}}
    """
    return {
        "name": anthropic_tool.get("name", ""),
        "description": anthropic_tool.get("description", ""),
        "inputSchema": anthropic_tool.get("input_schema", {}),
    }

def mcp_to_anthropic(mcp_tool: dict) -> dict:
    """Convert MCP tool to Anthropic Tool Use format"""
    return {
        "name": mcp_tool.get("name", ""),
        "description": mcp_tool.get("description", ""),
        "input_schema": mcp_tool.get("inputSchema", {}),
    }
