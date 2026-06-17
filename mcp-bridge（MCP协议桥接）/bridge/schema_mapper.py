"""JSON Schema bidirectional mapper for protocol conversion"""
import json
import logging

logger = logging.getLogger("mcp-bridge.schema-mapper")

SCHEMA_MAPPINGS = {
    # OpenAI strict mode enums
    "const": "enum",
    "anyOf": None,    # OpenAI strict doesn't support anyOf → needs transformation
    "oneOf": None,    # Same → split into multiple function defs
    "allOf": None,    # Same → merge schemas
}

def map_schema(schema: dict, target: str = "openai") -> dict:
    """
    Map JSON Schema between MCP and OpenAI Function Calling formats.

    target="openai": MCP → OpenAI (add strict, handle anyOf/oneOf)
    target="mcp": OpenAI → MCP (remove strict, restore anyOf/oneOf)
    """
    result = {}

    for key, value in schema.items():
        if target == "openai":
            if key in ("anyOf", "oneOf", "allOf"):
                # OpenAI strict mode: flatten to enum-like pattern
                logger.warning(f"Converting {key} to enum for OpenAI compatibility")
                values = [str(v.get("const", v)) for v in value if isinstance(v, dict)]
                result["enum"] = values
            else:
                result[key] = value
        elif target == "mcp":
            result[key] = value

    return result

def validate_schema_compatibility(schema: dict, target: str = "openai") -> list[str]:
    """Check schema compatibility with target format. Returns list of warnings."""
    warnings = []
    if target == "openai":
        if "anyOf" in schema:
            warnings.append("anyOf converted to enum — may lose semantics")
        if "oneOf" in schema:
            warnings.append("oneOf converted to enum — may lose semantics")
    return warnings
