"""Audit logger - append-only, structured JSON"""
import json
import time
import hashlib
import hmac
import os
import logging

logger = logging.getLogger("mcp-bridge.audit")

AUDIT_SECRET = os.environ.get("AUDIT_SECRET", "dev-audit-secret")

class AuditLogger:
    def __init__(self, log_path: str = "audit.log"):
        self.log_path = log_path

    def log(self, user: str, tool: str, params: dict, result, latency_ms: int, status: str):
        """Record an audit event (append-only)"""
        now = time.time()
        params_str = json.dumps(params, sort_keys=True, default=str)
        result_str = json.dumps(result, sort_keys=True, default=str)

        event = {
            "event": "tool_call",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(now)),
            "user": user,
            "tool": tool,
            "params_hash": hashlib.sha256(params_str.encode()).hexdigest()[:12],
            "result_hash": hashlib.sha256(result_str.encode()).hexdigest()[:12],
            "latency_ms": latency_ms,
            "status": status,
        }

        # HMAC signature for integrity
        signature = hmac.new(
            AUDIT_SECRET.encode(),
            json.dumps(event, sort_keys=True).encode(),
            hashlib.sha256
        ).hexdigest()[:16]
        event["signature"] = signature

        log_line = json.dumps(event)
        logger.info(f"AUDIT: {log_line}")

        try:
            with open(self.log_path, "a") as f:
                f.write(log_line + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def query(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """Query recent audit logs"""
        logs = []
        try:
            with open(self.log_path) as f:
                lines = f.readlines()
                for line in lines[-limit-offset:][offset:offset+limit]:
                    if line.strip():
                        logs.append(json.loads(line))
        except FileNotFoundError:
            pass
        return logs
