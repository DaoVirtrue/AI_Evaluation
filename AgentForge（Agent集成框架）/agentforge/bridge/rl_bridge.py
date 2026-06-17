"""RL Training Bridge — export agent trajectories to RL training formats"""
from typing import Literal
import json
import structlog

logger = structlog.get_logger()

class RLTrainingBridge:
    """Convert Agent trajectories to RL training data (JSONL / Parquet / Arrow)"""

    @staticmethod
    def export_trajectory(trajectory) -> dict:
        """Single trajectory → RL training sample"""
        return {
            "observation": [{"step": s.index, "type": s.step_type} for s in trajectory.steps],
            "actions": [{"type": s.step_type, "tool": s.tool_name} for s in trajectory.steps if s.step_type == "tool_call"],
            "reward": 0.0,  # Set by evaluator
            "metadata": {
                "model": trajectory.steps[0].model if trajectory.steps else "unknown",
                "total_tokens": trajectory.total_tokens,
                "total_cost": trajectory.total_cost,
                "total_latency_ms": trajectory.total_latency_ms,
            },
        }

    @staticmethod
    def export_batch(trajectories: list, fmt: str = "jsonl") -> str:
        """Batch export to specified format"""
        samples = [RLTrainingBridge.export_trajectory(t) for t in trajectories]
        if fmt == "jsonl":
            return "\n".join(json.dumps(s, default=str) for s in samples)
        elif fmt == "json":
            return json.dumps(samples, default=str, indent=2)
        else:
            raise ValueError(f"Unsupported format: {fmt}. Use 'jsonl' or 'json'.")
