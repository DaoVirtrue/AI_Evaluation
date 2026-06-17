"""
Resource Limiter — enforces CPU/Memory/Disk limits per execution.

Translates ExecutionSpec resource limits into Docker arguments.
"""
from __future__ import annotations

from ..api.schemas import ResourceSpec


def get_docker_resource_args(spec: ResourceSpec) -> list:
    """Convert ResourceSpec to Docker resource limit arguments."""
    args = [
        f"--memory={spec.memory_limit_mb}m",
        f"--cpus={spec.cpu_limit}",
        # Disk limit via storage_opt (requires overlay2 driver)
        f"--storage-opt=size={spec.disk_limit_mb}M",
    ]
    return args


def get_ulimit_args() -> list:
    """Get ulimit arguments for process limits."""
    return [
        "--ulimit=nproc=64:64",     # Max 64 processes
        "--ulimit=nofile=256:256",  # Max 256 open files
        "--ulimit=fsize=104857600",  # Max 100MB file size
    ]
