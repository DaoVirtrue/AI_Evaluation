"""
Network Policy — controls network access for sandbox executions.

Per JD requirements: network isolation for code sandbox.
Each execution can have network: none | restricted | full (dev only).
"""
from __future__ import annotations

from enum import Enum

from ..api.schemas import Language


class NetworkPolicy(str, Enum):
    """Network access policy for sandbox execution."""
    NONE = "none"          # --network=none, no internet access
    RESTRICTED = "restricted"  # Allow only whitelisted domains
    FULL = "full"          # Full network access (development only)


# Whitelist of domains allowed in RESTRICTED mode
# For package managers to work without giving general internet access
ALLOWED_DOMAINS = {
    "pypi.org", "files.pythonhosted.org",       # pip
    "registry.npmjs.org", "registry.yarnpkg.com",  # npm
    "proxy.golang.org", "sum.golang.org",        # Go modules
    "repo1.maven.org", "repo.maven.apache.org",  # Maven
    "crates.io", "static.crates.io",             # Cargo
}


def get_docker_network_args(policy: NetworkPolicy) -> list:
    """Get Docker network arguments for a given policy."""
    if policy == NetworkPolicy.NONE:
        return ["--network=none"]
    elif policy == NetworkPolicy.RESTRICTED:
        # Use a custom Docker network with egress filtering
        return ["--network=sandbox-restricted"]
    else:
        return []  # default bridge network


def is_domain_allowed(domain: str) -> bool:
    """Check if a domain is in the allowed whitelist."""
    return domain in ALLOWED_DOMAINS
