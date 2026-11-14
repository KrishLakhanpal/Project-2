"""
Testing Agent execution backend — restricted environment for testing
generated code.

IMPORTANT / HONEST LIMITATION:
True OS-level sandboxing (no filesystem, no network, no process spawning)
requires containers (Docker/gVisor/firejail) or OS primitives (seccomp,
namespaces). This module gives you a *best-effort* sandbox suitable for a
personal dev tool, NOT a production-grade untrusted-code sandbox:
  - static AST scan blocks obviously dangerous calls/imports before running
  - runs in a subprocess with a hard timeout
  - runs in a fresh temp directory with a stripped environment
  - resource limits (CPU time, memory, no new processes) via `resource` on
    Linux/Mac (no-op on Windows)
For real isolation, run this app's sandbox subprocess inside a Docker
container with --network=none --read-only --pids-limit=64, etc.
Never disable the confirmation step before executing user/AI-generated code.
"""
import ast
import os
import subprocess
import sys
import tempfile
import textwrap

import config

BLOCKED_NAMES = {
    "os", "subprocess", "socket", "shutil", "sys", "ctypes", "multiprocessing",
    "requests", "urllib", "http", "ftplib", "telnetlib", "paramiko",
}
BLOCKED_CALLS = {"eval", "exec", "__import__", "open", "compile"}


class UnsafeCodeError(Exception):
    pass


def static_scan(code: str):
    """Raises UnsafeCodeError if the code imports/calls something blocked."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return  # let the interpreter report the syntax error instead
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) \
                else [node.module.split(".")[0]] if node.module else []
            for n in names:
                if n in BLOCKED_NAMES:
                    raise UnsafeCodeError(f"Import of '{n}' is not allowed in the sandbox.")
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
            if name in BLOCKED_CALLS:
                raise UnsafeCodeError(f"Call to '{name}()' is not allowed in the sandbox.")


def _limit_resources():
    if os.name != "posix":
        return
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (config.SANDBOX_TIMEOUT, config.SANDBOX_TIMEOUT))
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))  # 256MB
        resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
    except Exception:
        pass


def run_python(code: str, stdin_input: str = "") -> dict:
    """
    Runs `code` as Python in a subprocess with restrictions.
    Returns {"status": "PASSED"|"FAILED"|"BLOCKED", "stdout": ..., "stderr": ...}
    Caller is responsible for getting explicit user confirmation before calling this.
    """
    try:
        static_scan(code)
    except UnsafeCodeError as e:
        return {"status": "BLOCKED", "stdout": "", "stderr": str(e)}

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "candidate.py")
        with open(script_path, "w") as f:
            f.write(code)

        env = {"PATH": os.environ.get("PATH", "")}  # stripped env, no secrets
        try:
            proc = subprocess.run(
                [sys.executable, script_path],
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=config.SANDBOX_TIMEOUT,
                cwd=tmpdir,
                env=env,
                preexec_fn=_limit_resources if os.name == "posix" else None,
            )
            status = "PASSED" if proc.returncode == 0 else "FAILED"
            return {"status": status, "stdout": proc.stdout, "stderr": proc.stderr}
        except subprocess.TimeoutExpired:
            return {"status": "FAILED", "stdout": "", "stderr": "Timed out (possible infinite loop)."}
        except Exception as e:
            return {"status": "FAILED", "stdout": "", "stderr": str(e)}


def format_result(result: dict) -> str:
    lines = [f"Test Status: {result['status']}"]
    if result.get("stdout"):
        lines.append(f"Output:\n{textwrap.indent(result['stdout'].strip(), '  ')}")
    if result.get("stderr"):
        lines.append(f"Error:\n{textwrap.indent(result['stderr'].strip(), '  ')}")
    return "\n".join(lines)
