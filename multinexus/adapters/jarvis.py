"""Jarvis adapter — SSH 到 vivo Pad 的 Jarvis brain。

MultiNexus 在 Mac 上管理 Discord bot，消息通过 SSH 转发到 Pad 的 jarvis_pkg.brain，
结果返回 Discord。Jarvis 的工具（YOLO/ASR/TTS/shell 等）在端侧执行。

agents.toml 配置：
  [[agents]]
  id = "pad-jarvis"
  adapter = "jarvis"
  token_env = "DISCORD_PAD_JARVIS_TOKEN"
  display_name = "Jarvis"
  work_dir = "~/projects"
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from collections.abc import Callable
from typing import Any

from ..models import AgentConfig
from .base import AdapterResult, AgentAdapter
from .utils import (
    async_subprocess_kwargs,
    filtered_env,
    terminate_owned_process_group,
)

log = logging.getLogger(__name__)

# 在 Pad 上调 brain 的 Python 片段
_BRAIN_CMD = '''python3 -c "
import sys; sys.path.insert(0, '/root')
from jarvis_pkg.brain import brain
prompt = sys.stdin.read()
print(brain(prompt), end='')
"'''

# health check 片段
_HEALTH_CMD = "ps aux | grep 'jarvis_pkg.main' | grep -v grep | wc -l"


class JarvisAdapter(AgentAdapter):
    """Jarvis 端侧 agent adapter（SSH 到 Pad 调 brain）。"""

    def __init__(self, config: AgentConfig):
        super().__init__(name="jarvis", timeout=config.timeout)
        self.config = config
        self.ssh_host = getattr(config, "jarvis_ssh_host", "vivoPad6p-ubuntu")

    def _ssh_cmd(self, remote_cmd: str) -> list[str]:
        """构造 SSH 命令。"""
        return [
            "ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
            self.ssh_host, remote_cmd,
        ]

    async def call(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
        work_dir: str | None = None,
        on_progress: Callable[[str | dict[str, Any]], None] | None = None,
    ) -> AdapterResult:
        """SSH 到 Pad，把 prompt 喂给 brain()，返回回复。"""
        timeout = timeout or self.config.timeout

        # 用 stdin 传 prompt（避免 shell 转义地狱）
        cmd = self._ssh_cmd(_BRAIN_CMD)

        if on_progress:
            on_progress({"status": "ssh_to_pad", "host": self.ssh_host})

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=filtered_env(),
                **async_subprocess_kwargs(),
            )
        except FileNotFoundError as e:
            return AdapterResult(text=f"SSH 不可用: {e}", metadata={"error": "no_ssh"})

        cleanup_attempted = False

        async def cleanup() -> None:
            nonlocal cleanup_attempted
            if cleanup_attempted:
                return
            cleanup_attempted = True
            await terminate_owned_process_group(proc)

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(prompt.encode("utf-8")),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            await cleanup()
            return AdapterResult(text="Jarvis 响应超时（Pad 可能休眠）", metadata={"error": "timeout"})
        except asyncio.CancelledError:
            await cleanup()
            raise
        except Exception:
            await cleanup()
            raise

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()[:500]
            return AdapterResult(text=f"Jarvis 调用失败: {err}", metadata={"error": "ssh_fail", "rc": proc.returncode})

        text = stdout.decode("utf-8", errors="replace").strip()
        return AdapterResult(text=text, session_id=None, metadata={"engine": "jarvis"})

    async def health_check(self) -> dict:
        """检查 Pad 上唤醒服务是否在跑。"""
        cmd = self._ssh_cmd(_HEALTH_CMD)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            count = int(stdout.decode().strip())
            available = count > 0
            return {
                "adapter": "jarvis",
                "bin": "ssh",
                "available": available,
                "path": self.ssh_host,
                "wake_processes": count,
            }
        except Exception as e:
            return {
                "adapter": "jarvis",
                "bin": "ssh",
                "available": False,
                "path": self.ssh_host,
                "error": str(e),
            }


class LocalBrainAdapter(AgentAdapter):
    """Jarvis agentd worker adapter — calls brain() in an owned local process.

    Runs inside the agentd worker ON the Pad.  The child imports
    ``jarvis_pkg.brain`` locally so timeout/cancellation can terminate the
    entire owned process group instead of leaving an in-process thread alive.
    """

    def __init__(self, config: AgentConfig):
        super().__init__(name="jarvis-local", timeout=config.timeout)
        self.config = config
        self._brain_fn = None

    def _get_brain(self):
        """Lazy-import brain() on first call.

        jarvis_pkg lives at /root/jarvis_pkg on the Pad. The agentd worker's
        cwd is /root/multinexus, so /root must be on sys.path for the import
        to resolve. Also honor PYTHONPATH if set.
        """
        if self._brain_fn is None:
            import sys
            for candidate in ("/root", os.path.expanduser("~")):
                if candidate not in sys.path:
                    sys.path.insert(0, candidate)
            from jarvis_pkg.brain import brain
            self._brain_fn = brain
        return self._brain_fn

    def _build_cmd(self) -> list[str]:
        """Return a command that imports jarvis_pkg.brain and reads from stdin."""
        return [
            sys.executable,
            "-c",
            (
                "import os, sys\n"
                "for d in ('/root', os.path.expanduser('~')):\n"
                "    if d not in sys.path:\n"
                "        sys.path.insert(0, d)\n"
                "from jarvis_pkg.brain import brain\n"
                "prompt = sys.stdin.read()\n"
                "print(brain(prompt), end='')\n"
            ),
        ]

    async def call(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
        work_dir: str | None = None,
        on_progress: Callable[[str | dict[str, Any]], None] | None = None,
    ) -> AdapterResult:
        """Call brain() in a spawned subprocess that owns its process group."""
        timeout = timeout or self.config.timeout

        if on_progress:
            on_progress({"status": "calling_brain"})

        cwd = work_dir or self.config.work_dir
        cmd = self._build_cmd()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=filtered_env(cwd=cwd),
                **async_subprocess_kwargs(),
            )
        except FileNotFoundError as e:
            return AdapterResult(
                text=f"Jarvis local brain 不可用: {e}",
                metadata={"error": "no_python"},
            )

        cleanup_attempted = False

        async def cleanup() -> None:
            nonlocal cleanup_attempted
            if cleanup_attempted:
                return
            cleanup_attempted = True
            await terminate_owned_process_group(proc)

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(prompt.encode("utf-8")),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            await cleanup()
            return AdapterResult(text="Jarvis brain() 响应超时", metadata={"error": "timeout"})
        except asyncio.CancelledError:
            await cleanup()
            raise
        except Exception as e:
            await cleanup()
            return AdapterResult(
                text=f"Jarvis brain() 调用失败: {e}",
                metadata={"error": "brain_fail"},
            )

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()[:500]
            return AdapterResult(
                text=f"Jarvis brain() 调用失败: {err}",
                metadata={"error": "brain_fail", "rc": proc.returncode},
            )

        text = stdout.decode("utf-8", errors="replace").strip()
        return AdapterResult(text=text or "", session_id=None, metadata={"engine": "jarvis-local"})

    async def health_check(self) -> dict:
        """Check if jarvis_pkg is importable and wake service is running."""
        try:
            self._get_brain()
        except Exception as e:
            return {
                "adapter": "jarvis-local",
                "bin": "brain()",
                "available": False,
                "path": "jarvis_pkg.brain",
                "error": f"import failed: {e}",
            }
        # Check wake service process count
        try:
            proc = await asyncio.create_subprocess_exec(
                "sh", "-c", "ps aux | grep 'jarvis_pkg.main' | grep -v grep | wc -l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            count = int(stdout.decode().strip())
        except Exception:
            count = 0
        return {
            "adapter": "jarvis-local",
            "bin": "brain()",
            "available": True,
            "path": "jarvis_pkg.brain",
            "wake_processes": count,
        }
