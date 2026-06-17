"""
Code Scanner — static analysis of submitted code for dangerous patterns.

Scans code before execution to block:
- System command execution (os.system, subprocess, exec, eval)
- File system manipulation (open, shutil, pathlib write)
- Network access (socket, requests, urllib, httpx)
- Process manipulation (fork, kill, signal)
- Import of dangerous modules
- Code that attempts to escape the sandbox
"""
from __future__ import annotations

import re
from typing import Tuple

from ..api.schemas import Language


# ── Language-specific dangerous patterns ───────────────────────────────

PYTHON_DANGEROUS_PATTERNS = [
    # System command execution
    (r'\bos\.system\s*\(', "os.system() call detected"),
    (r'\bos\.popen\s*\(', "os.popen() call detected"),
    (r'\bsubprocess\.', "subprocess module usage detected"),
    (r'\beval\s*\(', "eval() call detected"),
    (r'\bexec\s*\(', "exec() call detected"),
    (r'\bcompile\s*\(', "compile() call detected"),
    (r'\b__import__\s*\(', "__import__() call detected"),

    # File system — write operations
    (r'\bopen\s*\([^)]*["\']w', "File write via open() detected"),
    (r'\bshutil\.(copy|move|rmtree|make_archive)', "shutil file operation detected"),
    (r'\bpathlib\.Path\([^)]*\)\.write_text', "pathlib write_text detected"),

    # Network access
    (r'\bsocket\.', "socket module usage detected"),
    (r'\brequests\.(get|post|put|delete|patch|head)', "HTTP request via requests detected"),
    (r'\burllib\.', "urllib usage detected"),
    (r'\bhttpx\.', "httpx usage detected"),
    (r'\bhttp\.client', "http.client usage detected"),
    (r'\bftplib\.', "FTP access detected"),

    # Process manipulation
    (r'\bos\.kill\s*\(', "Process kill detected"),
    (r'\bos\.fork\s*\(', "Process fork detected"),
    (r'\bsignal\.', "Signal manipulation detected"),
    (r'\bmultiprocessing\.', "Multiprocessing usage detected"),

    # Sandbox escape attempts
    (r'\bdocker\b', "Docker command reference detected"),
    (r'\bkubectl\b', "kubectl command reference detected"),
    (r'\bsudo\b', "sudo command reference detected"),
    (r'\bchmod\b', "chmod command reference detected"),
    (r'\bchown\b', "chown command reference detected"),
    (r'\brm\s+-rf\b', "rm -rf command detected"),

    # Dangerous imports
    (r'\bimport\s+ctypes\b', "ctypes import detected"),
    (r'\bimport\s+sys\b.*sys\.exit', "sys.exit() detected"),
]

JAVASCRIPT_DANGEROUS_PATTERNS = [
    (r'\bchild_process\b', "child_process module detected"),
    (r'\beval\s*\(', "eval() call detected"),
    (r'\bFunction\s*\(', "Function constructor detected"),
    (r'\bfs\.(writeFile|unlink|rmdir|mkdir)', "File system write detected"),
    (r'\brequire\s*\(\s*["\']net["\']', "net module import detected"),
    (r'\brequire\s*\(\s*["\']dgram["\']', "dgram module import detected"),
    (r'\bprocess\.exit\b', "process.exit() detected"),
    (r'\bprocess\.kill\b', "process.kill() detected"),
    (r'\bXMLHttpRequest\b', "XMLHttpRequest detected"),
    (r'\bfetch\s*\(', "fetch() call detected"),
]

# Safe modules/patterns that are explicitly allowed
PYTHON_ALLOWED_MODULES = {
    "math", "statistics", "fractions", "decimal",
    "itertools", "functools", "collections", "heapq", "bisect",
    "re", "string", "textwrap",
    "json", "csv", "base64", "hashlib",
    "datetime", "calendar", "time",
    "random", "copy", "typing", "dataclasses", "enum",
    "unittest", "doctest",
    "os.path", "pathlib.Path.read_text", "pathlib.Path.read_bytes",
}


class CodeScanner:
    """
    Scans submitted code for dangerous patterns before execution.

    This is a defense-in-depth measure — even though Docker provides
    isolation, we block obviously malicious code at the application layer
    for defense in depth and faster rejection (no need to spin up a container).
    """

    def scan(self, code: str, language: Language) -> Tuple[bool, str]:
        """
        Scan code for dangerous patterns.
        Returns (is_safe: bool, reason: str).
        """
        # Check code size
        if len(code) > 500_000:
            return False, "Code exceeds maximum size of 500KB"

        # Check for null bytes (potential binary/exploit)
        if "\x00" in code:
            return False, "Code contains null bytes"

        # Language-specific pattern matching
        if language in (Language.PYTHON,):
            return self._scan_patterns(code, PYTHON_DANGEROUS_PATTERNS)
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            return self._scan_patterns(code, JAVASCRIPT_DANGEROUS_PATTERNS)
        else:
            # Generic scan for extremely dangerous patterns
            generic_patterns = [
                (r'\brm\s+-rf\b', "Dangerous shell command"),
                (r'\bsudo\b', "Privilege escalation attempt"),
                (r'\b/dev/null\b', "Device file access"),
                (r'\b/proc/\b', "Proc filesystem access"),
            ]
            return self._scan_patterns(code, generic_patterns)

    def _scan_patterns(self, code: str, patterns: list) -> Tuple[bool, str]:
        """Run regex patterns against code, return first match."""
        for pattern, message in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False, message
        return True, ""

    def is_safe(self, code: str, language: Language) -> bool:
        """Quick check: is the code safe to execute?"""
        safe, _ = self.scan(code, language)
        return safe
