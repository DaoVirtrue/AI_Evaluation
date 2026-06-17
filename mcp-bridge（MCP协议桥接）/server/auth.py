"""Authentication manager for MCP Bridge"""
import logging

logger = logging.getLogger("mcp-bridge.auth")

class AuthManager:
    def __init__(self):
        # In production, use JWT / API Key / mTLS
        self._api_keys = {"dev-key-001": "admin", "dev-key-002": "operator", "dev-key-003": "readonly"}

    def get_user_from_request(self, request) -> str:
        """Extract user identity from request headers"""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return self._api_keys.get(token, "anonymous")
        if auth_header.startswith("ApiKey "):
            token = auth_header[7:]
            return self._api_keys.get(token, "anonymous")
        return "anonymous"

    def get_role(self, user: str) -> str:
        """Get user role"""
        roles = {"dev-key-001": "admin", "dev-key-002": "operator", "dev-key-003": "readonly"}
        return roles.get(user, "anonymous")
