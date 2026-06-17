"""RBAC access control for MCP tools"""
import yaml
import os
import logging

logger = logging.getLogger("mcp-bridge.access")

DEFAULT_POLICY = """
tools:
  echo:
    access:
      roles: [admin, operator, readonly]
  web_search:
    access:
      roles: [admin, operator]
  calculator:
    access:
      roles: [admin, operator, readonly]
"""

class AccessController:
    def __init__(self, policy_path: str | None = None):
        self.policy = self._load_policy(policy_path)

    def _load_policy(self, path: str | None) -> dict:
        if path and os.path.exists(path):
            with open(path) as f:
                return yaml.safe_load(f)
        return yaml.safe_load(DEFAULT_POLICY)

    def check(self, user: str, tool_name: str, params: dict | None = None) -> bool:
        """Check if user can access tool. Returns True if allowed."""
        tools_policy = self.policy.get("tools", {})
        tool_policy = tools_policy.get(tool_name, {})

        # If no policy defined for tool, allow by default
        if not tool_policy:
            return True

        allowed_roles = tool_policy.get("access", {}).get("roles", [])
        allowed_users = tool_policy.get("access", {}).get("users", [])

        if user in allowed_users:
            return True

        # Map user to role if using API keys
        role_map = {"admin": "admin", "operator": "operator", "readonly": "readonly"}
        user_role = role_map.get(user, "anonymous")

        if user_role in allowed_roles:
            # Check if readonly user is trying to write
            readonly_tools = tool_policy.get("access", {}).get("readonly_users", [])
            if user in readonly_tools and params and params.get("_action") == "write":
                return False
            return True

        return False
