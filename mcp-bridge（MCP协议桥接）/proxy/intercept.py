"""MCP Proxy intercept layer — modify/block requests in transit"""
import logging
logger = logging.getLogger("mcp-bridge.proxy")

class RequestInterceptor:
    def intercept(self, request: dict) -> tuple[bool, dict]:
        """Returns (allowed, modified_request). Block by returning (False, {...})."""
        # Inject audit header, sanitize params, etc.
        return True, request
