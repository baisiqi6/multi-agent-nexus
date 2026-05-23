import os
import subprocess
import sys

IS_WIN = sys.platform == "win32"
NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if IS_WIN else {}


def filtered_env(*, cwd: str | None = None) -> dict[str, str]:
    """Strip message-bus secrets so spawned agents cannot echo bot tokens."""
    strip_prefixes = ("KOOK_", "DISCORD_")
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(key.startswith(prefix) for prefix in strip_prefixes)
    }
    if cwd:
        env["PWD"] = cwd
    return env
