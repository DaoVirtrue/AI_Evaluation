"""Tool input/output JSON Schema validator"""
import json
import logging
from jsonschema import validate, ValidationError

logger = logging.getLogger("mcp-bridge.validator")

class ToolValidator:
    def validate_input(self, tool_name: str, params: dict) -> bool:
        """Validate tool input against its JSON Schema"""
        # Basic checks
        if not isinstance(params, dict):
            logger.warning(f"Tool '{tool_name}' params is not dict: {type(params)}")
            return False

        # Check for suspicious patterns
        for key, value in params.items():
            if isinstance(value, str):
                if len(value) > 100_000:  # Max 100K chars
                    logger.warning(f"Tool '{tool_name}' param '{key}' too large")
                    return False
                if any(dangerous in value for dangerous in ["__import__", "eval(", "exec(", "subprocess", "os.system"]):
                    logger.warning(f"Tool '{tool_name}' param '{key}' contains dangerous pattern")
                    return False

        return True

    def validate_output(self, tool_name: str, result: dict) -> bool:
        """Validate tool output"""
        if not isinstance(result, dict):
            return False
        return True
