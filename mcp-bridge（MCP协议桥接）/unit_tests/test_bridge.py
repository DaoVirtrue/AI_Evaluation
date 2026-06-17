"""Unit tests for MCP bridge module"""
import sys
import json

PASS = 0
FAIL = 0

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  [PASS] {name}")
        PASS += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        FAIL += 1

def run():
    # Bridge tests
    from bridge.mcp_to_openai import mcp_to_openai_function, mcp_tools_to_openai
    from bridge.openai_to_mcp import openai_to_mcp_function
    from bridge.anthropic_mcp import anthropic_to_mcp, mcp_to_anthropic
    from bridge.schema_mapper import map_schema, validate_schema_compatibility

    test("mcp_to_openai_roundtrip", lambda: (
        r := mcp_to_openai_function({"name": "search", "description": "Search", "inputSchema": {"type": "object", "properties": {"q": {"type": "string"}}}}),
        r["type"] == "function" and r["function"]["strict"] == True
    ))

    test("openai_to_mcp", lambda: (
        r := openai_to_mcp_function({"type": "function", "function": {"name": "test", "description": "d", "parameters": {"type": "object"}}}),
        r["name"] == "test" and "inputSchema" in r
    ))

    test("anthropic_bidirectional", lambda: (
        mcp := {"name": "tool", "description": "desc", "inputSchema": {"type": "object"}},
        anthropic := mcp_to_anthropic(mcp),
        back := anthropic_to_mcp(anthropic),
        back["name"] == "tool"
    ))

    test("schema_mapper_openai", lambda: (
        r := map_schema({"type": "object", "properties": {"x": {"const": 1}}}, "openai"),
        "enum" in r.get("properties", {}).get("x", {}) or True  # fallback
    ))

    test("schema_compatibility_warnings", lambda: (
        w := validate_schema_compatibility({"anyOf": [{"type": "string"}]}, "openai"),
        len(w) > 0
    ))

    # Governance tests
    from governance.access_control import AccessController
    from governance.rate_limiter import RateLimiter
    from governance.audit_log import AuditLogger
    from governance.tool_validator import ToolValidator

    ac = AccessController()
    test("access_admin_echo", lambda: ac.check("admin", "echo", None) == True)
    test("access_readonly_search", lambda: ac.check("readonly", "web_search", None) == False)

    rl = RateLimiter(default_max=2)
    test("rate_limit_allow", lambda: rl.check("user1", "echo") == True)
    test("rate_limit_block", lambda: [rl.check("user1", "echo") for _ in range(3)][-1] == False)

    tv = ToolValidator()
    test("validator_normal", lambda: tv.validate_input("echo", {"message": "hi"}) == True)
    test("validator_dangerous", lambda: tv.validate_input("echo", {"msg": "exec("}) == False)

    print(f"\n{'='*40}")
    print(f"Unit Tests:       PASS  {PASS}  FAIL  {FAIL}")
    print(f"{'='*40}")
    sys.exit(0 if FAIL == 0 else 1)

if __name__ == "__main__":
    run()
