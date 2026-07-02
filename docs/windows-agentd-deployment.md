# Windows Agentd Deployment

Standard operating procedure for running a MultiNexus agentd as a Windows
service via NSSM. This covers the SSH-based coordination model used in
Phase 7.2+, where the Windows host runs only the agentd and proxies all
coordinator CLI calls to a remote coordinate service over SSH.

---

## Architecture

```
Windows host                       Remote (Tencent Cloud)
─────────────                      ──────────────────────
NSSM service
  └─ python -m multinexus.agentd
       ├─ claude / opencode CLI          coordinate.service
       └─ coord-ssh-win.py ──SSH──►      /usr/local/bin/coord-local
                                           └─ coord.sqlite3
                                       multinexus-discord-bridge.service
                                           (reads jobs, posts to Discord)
```

The agentd does **not** run a Discord bot. It only claims coordinator jobs,
runs the agent adapter, and reports results back. The bridge that owns the
Discord connection lives on the remote host.

---

## Prerequisites on the Windows host

- Python 3.11+ (3.14 verified)
- Git
- OpenSSH client (`ssh.exe`)
- The agent CLI for your adapter:
  - `win-claude` → Claude Code CLI (`claude.cmd` in `%APPDATA%\npm`)
  - `win-opencode` → OpenCode CLI
- NSSM (Non-Sucking Service Manager) — `scoop install nssm` or download from
  `nssm.cc`
- SSH access to the remote coordinate host (key-based, no password prompt)

---

## Step 1: SSH key and alias

Generate a dedicated ed25519 key (do not reuse your personal key):

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\id_ed25519_coord_win -N "" -C "windows-multinexus-coord"
```

Append the public key to the remote `ubuntu` user's `authorized_keys`, then
add an alias in `$env:USERPROFILE\.ssh\config`:

```
Host kook-hermes-admin
    HostName <REMOTE_IP>
    User ubuntu
    IdentityFile ~/.ssh/id_ed25519_coord_win
```

Verify:

```powershell
ssh kook-hermes-admin "echo ok && hostname"
```

You should see `ok` and the remote hostname with no password prompt.

---

## Step 2: Clone and set up the project

```powershell
git clone https://github.com/baisiqi6/multi-agent-nexus C:\Users\<user>\projects\multinexus
cd C:\Users\<user>\projects\multinexus
git switch agents/mac-claude/phase-7.2-multi-host-agent-runtime
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Verify the agentd module imports:

```powershell
.\.venv\Scripts\python.exe -m multinexus.agentd --help
```

---

## Step 3: coord-ssh-win.py wrapper

The wrapper lives at `scripts/coord-ssh-win.py`. It is required because
Windows `subprocess.list2cmdline` corrupts JSON payloads that contain
double quotes when passed through SSH as a command argument.

The wrapper:
1. Quotes each argument with `shlex.quote` (POSIX shell quoting)
2. On Windows, pipes the full remote command through SSH stdin
   (`ssh -T host sh`) to bypass `list2cmdline` entirely
3. On Mac/Linux, passes the command as a single SSH argv element (the
   POSIX shell on the remote handles the quoting correctly)

**Always point `coordinator_cli_path` at the `.py` wrapper, never the
`.cmd` shim.** The `.cmd` shim exists only for manual testing from a
terminal — `cmd.exe`'s `%*` expansion mangles JSON the same way
`list2cmdline` does.

Smoke-test the wrapper before wiring it into config:

```powershell
.\.venv\Scripts\python.exe .\scripts\coord-ssh-win.py --help
.\.venv\Scripts\python.exe .\scripts\coord-ssh-win.py runtime job claim --agent-id win-claude
```

---

## Step 4: agents.toml

`agents.toml` is gitignored — each host keeps its own local copy. Copy
from `agents.toml.example` and edit. For the Windows agent you plan to
run, set `coordinator_cli_path` to the absolute path of the wrapper:

```toml
[[agents]]
id = "win-claude"
adapter = "claude"
token_env = "DISCORD_WIN_CLAUDE_TOKEN"
# ... other fields ...

coordinator_cli_path = 'C:\Users\<user>\projects\multinexus\scripts\coord-ssh-win.py'
```

Use a TOML literal string (single quotes) so the backslashes in the
Windows path are not treated as escape sequences.

Do **not** set `DISCORD_*_TOKEN` environment variables on the Windows host.
The agentd calls `load_config(require_token=False)` and never connects to
Discord directly — the bridge on the remote host owns all Discord tokens.

Verify the config parses:

```powershell
.\.venv\Scripts\python.exe -c "import tomllib; print([a.get('coordinator_cli_path') for a in tomllib.load(open('agents.toml','rb'))['agents'] if a.get('id')=='win-claude'])"
```

---

## Step 5: Register the agent on the remote

The agentd does not self-register on startup. Register once manually:

```powershell
.\.venv\Scripts\python.exe .\scripts\coord-ssh-win.py runtime agent register `
    --agent-id win-claude `
    --host-id win-admin `
    --client-type agentd
```

Use a stable `--host-id` that identifies this Windows machine. The
registration persists in the remote coord DB; you only re-run this if the
agent record was deleted or you want to change the host-id.

---

## Step 6: NSSM service

### 6.1 Install

```powershell
nssm install multinexus-win-claude-agentd "C:\Users\<user>\projects\multinexus\.venv\Scripts\python.exe"
```

### 6.2 Configure

```powershell
$svc = "multinexus-win-claude-agentd"
$proj = "C:\Users\<user>\projects\multinexus"

nssm set $svc AppParameters "-m multinexus.agentd --config $proj\agents.toml --agent win-claude --poll-interval 2"
nssm set $svc AppDirectory $proj
nssm set $svc Start SERVICE_AUTO_START

# Logging
nssm set $svc AppStdout "$proj\logs\win-claude.agentd.log"
nssm set $svc AppStderr "$proj\logs\win-claude.agentd.err.log"
nssm set $svc AppRotateFiles 1
nssm set $svc AppRotateOnline 1
nssm set $svc AppRotateBytes 10485760

# Restart policy
nssm set $svc AppExit Default Restart
nssm set $svc AppRestartDelay 5000
```

### 6.3 Environment variables (critical)

The service process does **not** inherit your user environment. Without
these, the agentd will start but fail when it tries to invoke the agent
CLI or SSH:

```powershell
nssm set $svc AppEnvironmentExtra `
    "PYTHONUTF8=1" `
    "PYTHONIOENCODING=utf-8" `
    "USERPROFILE=C:\Users\<user>" `
    "HOME=C:\Users\<user>" `
    "APPDATA=C:\Users\<user>\AppData\Roaming" `
    "LOCALAPPDATA=C:\Users\<user>\AppData\Local" `
    "PATH=C:\Users\<user>\AppData\Roaming\npm;C:\Program Files\nodejs;C:\Program Files\Git\usr\bin;C:\Windows\System32\OpenSSH;C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem"
```

Why each one matters:

| Variable | Reason |
|----------|--------|
| `PYTHONUTF8=1` | Forces UTF-8 mode; without it, Chinese Windows uses GBK and crashes decoding coord-local's UTF-8 JSON output |
| `PYTHONIOENCODING=utf-8` | Belt-and-suspenders for stdout/stderr encoding |
| `USERPROFILE`, `HOME` | Claude CLI reads `~/.claude/` for auth/config |
| `APPDATA`, `LOCALAPPDATA` | Node.js and npm-installed CLIs look here for config |
| `PATH` | Must include `npm` global bin (for `claude`), Node.js, Git's `usr\bin`, and `OpenSSH` |

### 6.4 Create logs directory

NSSM will fail to start if the log directory does not exist:

```powershell
mkdir C:\Users\<user>\projects\multinexus\logs -Force
```

### 6.5 Start

```powershell
nssm start multinexus-win-claude-agentd
Get-Service multinexus-win-claude-agentd
```

Python's `logging` module writes to **stderr** by default, so the main
log is `win-claude.agentd.err.log`. The `win-claude.agentd.log` (stdout)
will usually be empty unless the agentd explicitly prints to stdout.

---

## Step 7: Verify end-to-end

1. Check the service is Running and the log shows:
   ```
   agentd worker starting: agent=win-claude
   Agentd worker started: agent=win-claude
   ```
   with no `coordinate CLI failed` errors.

2. `@Win Claude ping` (or equivalent) from Discord. Within a few seconds
   the log should show `Processing job request:<id>` followed by
   `Job request:<id> complete: status=done`.

3. Confirm the remote job is `done`:
   ```powershell
   .\.venv\Scripts\python.exe .\scripts\coord-ssh-win.py job list --workspace-id discord-nexus
   ```
   The newest `win-claude` job should have `"status": "done"` and a
   populated `result.response_text`.

---

## Operations

### View logs

```powershell
Get-Content C:\Users\<user>\projects\multinexus\logs\win-claude.agentd.err.log -Tail 50 -Wait
```

### Restart / stop / start

```powershell
nssm restart multinexus-win-claude-agentd
nssm stop   multinexus-win-claude-agentd
nssm start  multinexus-win-claude-agentd
```

### Update code

```powershell
cd C:\Users\<user>\projects\multinexus
git pull
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
nssm restart multinexus-win-claude-agentd
```

### Uninstall

```powershell
nssm stop   multinexus-win-claude-agentd
nssm remove multinexus-win-claude-agentd confirm
```

---

## Adding another agent (win-opencode)

Copy the win-claude template with these changes:

1. New service name: `multinexus-win-opencode-agentd`
2. `--agent win-opencode` instead of `--agent win-claude`
3. Confirm the opencode CLI is on `PATH` (add its install dir if needed)
4. New log paths: `win-opencode.agentd.log` / `.err.log`
5. Register the new agent on the remote:
   ```powershell
   .\.venv\Scripts\python.exe .\scripts\coord-ssh-win.py runtime agent register `
       --agent-id win-opencode --host-id win-admin --client-type agentd
   ```

---

## Known gotchas

- **`coordinator_cli_path` must point to the `.py` wrapper, not `.cmd`.**
  The `.cmd` shim is for interactive testing only — `cmd.exe` `%*`
  expansion and `list2cmdline` both corrupt JSON arguments.

- **Python signal handlers do not work on Windows.** The agentd's
  `loop.add_signal_handler(SIGINT, ...)` is guarded by
  `sys.platform != "win32"`. Stopping the service via NSSM falls back to
  a forceful process kill, which is fine — the agentd is idempotent and
  will re-claim any in-flight job on next start.

- **Zombie jobs.** If an agentd crashes mid-job (or a report fails), the
  job stays `running` on the remote forever. Periodically check:
  ```powershell
  .\.venv\Scripts\python.exe .\scripts\coord-ssh-win.py job list --workspace-id discord-nexus
  ```
  and mark orphans `failed`:
  ```powershell
  .\.venv\Scripts\python.exe .\scripts\coord-ssh-win.py runtime job report <job-id> `
      --agent-id win-claude --status failed `
      --result-json '{"error":"orphaned, manually cleaned","response_text":"","duration_ms":0}'
  ```

- **First SSH call after service start may be slow** (key agent /
  connection setup). The agentd tolerates this — the claim loop just
  retries on the next poll interval.
