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
from collections.abc import Callable
from typing import Any

from ..models import AgentConfig
from .base import AdapterResult, AgentAdapter
from .utils import filtered_env

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
            )
        except FileNotFoundError as e:
            return AdapterResult(text=f"SSH 不可用: {e}", metadata={"error": "no_ssh"})

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(prompt.encode("utf-8")),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            return AdapterResult(text="Jarvis 响应超时（Pad 可能休眠）", metadata={"error": "timeout"})

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
    """Jarvis agentd worker adapter — calls brain() directly (no SSH).

    Runs inside the agentd worker ON the Pad. Imports jarvis_pkg.brain
    directly and calls brain() in a thread (brain is synchronous).
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

    async def call(
        self,
        prompt: str,
        *,
        timeout: int | None = None,
        work_dir: str | None = None,
        on_progress: Callable[[str | dict[str, Any]], None] | None = None,
    ) -> AdapterResult:
        """Call brain() directly in a worker thread."""
        timeout = timeout or self.config.timeout
        brain = self._get_brain()

        if on_progress:
            on_progress({"status": "calling_brain"})

        try:
            text = await asyncio.wait_for(
                asyncio.to_thread(brain, prompt),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return AdapterResult(text="Jarvis brain() 响应超时", metadata={"error": "timeout"})
        except Exception as e:
            return AdapterResult(text=f"Jarvis brain() 调用失败: {e}", metadata={"error": "brain_fail"})

        return AdapterResult(text=text or "", session_id=None, metadata={"engine": "jarvis-local"})

    async def health_check(self) -> dict:
        """Check if jarvis_pkg is importable and wake service is running."""
        import shutil
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
