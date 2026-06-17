"""Tool execution sandbox"""
import logging

logger = logging.getLogger("mcp-bridge.sandbox")

class SandboxConfig:
    def __init__(self, sandbox_type: str = "none", timeout: int = 30, network: str = "none", read_only: bool = True):
        self.type = sandbox_type
        self.timeout = timeout
        self.network = network
        self.read_only = read_only

class Sandbox:
    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()

    def is_safe(self, params: dict) -> bool:
        """Check if parameters are safe for execution"""
        dangerous = ["__import__", "eval(", "exec(", "subprocess", "os.system", "rm -rf", "DROP", "DELETE"]
        for key, value in params.items():
            if isinstance(value, str) and any(d in value for d in dangerous):
                logger.warning(f"Blocked dangerous call: {value}")
                return False
        return True
