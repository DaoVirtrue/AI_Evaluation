"""mcp-convert: Convert between MCP, OpenAI FC, and Anthropic formats"""
import json
import sys
from bridge.mcp_to_openai import mcp_tools_to_openai
from bridge.openai_to_mcp import openai_tools_to_mcp
from bridge.anthropic_mcp import anthropic_to_mcp, mcp_to_anthropic

def main():
    if len(sys.argv) < 3:
        print("Usage: mcp-convert --from <format> --to <format> --file <path>")
        print("Formats: mcp, openai, anthropic")
        return

    # Simple conversion demo
    sample_mcp = [{"name": "search", "description": "Search web", "inputSchema": {"type": "object", "properties": {"q": {"type": "string"}}}}]
    print("MCP → OpenAI:", json.dumps(mcp_tools_to_openai(sample_mcp), indent=2))
    print("MCP → Anthropic:", json.dumps([mcp_to_anthropic(t) for t in sample_mcp], indent=2))

if __name__ == "__main__":
    main()
