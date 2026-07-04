# Platform Setup

Full setup instructions for Windows and Mac/Linux.

---

## Prerequisites

- Python 3.11 or higher
- Node.js 18+ (for Claude Code CLI and/or Codex CLI)
- Git
- A Discord application with a bot token

---

## Step 1: Discord Application

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application** — name it whatever you like
3. Go to **Bot** → click **Add Bot**
4. Under **Privileged Gateway Intents**, enable:
   - **Message Content Intent**
   - **Server Members Intent** (if you use the allowlist feature)
5. Copy the **Token** — you'll put it in `.env`

### Invite URL

In **OAuth2 → URL Generator**, select:
- Scopes: `bot`, `applications.commands`
- Permissions: `Send Messages`, `Manage Webhooks`, `Read Message History`, `Embed Links`, `Add Reactions`

Open the generated URL and add the bot to your server.

### Get IDs

Enable **Developer Mode** in Discord (User Settings → Advanced → Developer Mode).
Right-click any server, channel, or user to copy its ID.

---

## Step 2: Clone and Install

```bash
git clone https://github.com/your-org/multinexus.git
cd multinexus
python -m venv .venv
```

**Windows:**
```cmd
.venv\Scripts\activate
```

**Mac/Linux:**
```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

---

## Step 3: Configure

```bash
cp .env.example .env
cp config.yaml.example config.yaml
```

### .env

```
DISCORD_TOKEN=your_bot_token_here
# LMSTUDIO_API_KEY=       # optional, leave blank for LM Studio / Ollama
# OPENCLAW_GATEWAY_TOKEN= # optional
# PRIVATE_DB_PATH=        # optional, absolute path to private SQLite DB file
```

### config.yaml

Key fields to fill in:

```yaml
bot:
  name: "YourBot"           # Display name in status commands
  allowed_users:
    - YOUR_DISCORD_USER_ID  # Right-click your name → Copy User ID (Dev Mode must be on)

agent_roles:
  claude: YOUR_CLAUDE_ROLE_ID
  codex: YOUR_CODEX_ROLE_ID
  local-agent: YOUR_LOCAL_AGENT_ROLE_ID

discoveries_channel: YOUR_CHANNEL_ID   # Where <!-- DISCOVERY: --> tags are posted
```

Create Discord roles for each agent you want (e.g., "Claude", "Local Agent") and put the role IDs here.
Users mentioning `@Claude` will trigger the Claude agent.

---

## Step 4: Install CLI Agents (Optional)

### Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
claude login
```

### Codex CLI

```bash
npm install -g @openai/codex
# Add OPENAI_API_KEY to .env
```

### Local LLM (LM Studio)

1. Download [LM Studio](https://lmstudio.ai/)
2. Download a model in the Discover tab
3. Go to **Local Server** → click **Start Server**
4. Default port is 1234

### Local LLM (Ollama)

```bash
# Mac/Linux:
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
ollama serve

# Windows: download installer from ollama.com
```

Update `config.yaml` with your chosen model name.

---

## Step 5: Run

> **⚠️ Legacy** — `python bot.py` and the PM2 config (`ecosystem.config.js`)
> below have been removed. Production now uses `multinexus.py` with systemd
> (Linux) or launchd (Mac). See ["Persistent Operation with launchd"](#persistent-operation-with-launchd-new-multi-bot-multinexuspy)
> below and the deploy scripts in `scripts/`.

```bash
python multinexus.py --platform discord --config agents.toml
```

On first run, the bot will:
- Create the `data/` directory
- Create `nexus.db`
- Sync slash commands with Discord (may take up to an hour to propagate globally)

---

## Persistent Operation (legacy PM2 — removed)

> **⚠️ Removed** — `ecosystem.config.js` and the PM2-based persistence path have
> been deleted. PM2 is no longer used. Production persistence is provided by:
>
> - **Linux**: systemd unit `multinexus-discord-bridge` (see `scripts/deploy-server.sh`)
> - **Mac**: launchd plist (see ["Persistent Operation with launchd"](#persistent-operation-with-launchd-new-multi-bot-multinexuspy) below)
>
> This section is retained for historical reference only.

---

## Persistent Operation with launchd (new multi-bot multinexus.py)

Production uses `multinexus.py --platform discord` with launchd for Mac persistence (or systemd on Linux — see `scripts/deploy-server.sh`). The legacy single-bot `bot.py` and its PM2 config have been removed.

### Prerequisites

1. Create `agents.toml` from `agents.toml.example` (fill in real channel IDs, Discord user IDs, and CLI binary paths using absolute paths).
2. Create `.env` from `.env.example` (fill in real bot tokens).
3. Ensure `.venv` is set up with dependencies installed.

### Start all managed bots

```bash
scripts/start.sh
```

### Start a single bot

```bash
scripts/start.sh mac-claude
```

### Check status

```bash
scripts/status.sh
scripts/status.sh mac-claude
```

### Stop (temporary — will restart on next login)

```bash
scripts/stop.sh
scripts/stop.sh mac-codex
```

### Uninstall (permanent — removes LaunchAgent plist)

```bash
scripts/uninstall.sh
scripts/uninstall.sh mac-codex
```

### Logs

Logs are written to `logs/<agent>.log` (stdout) and `logs/<agent>.err.log` (stderr).

```bash
tail -f logs/mac-claude.log
```

### How it works

- Each managed bot (mac-claude, mac-codex, mac-opencode) gets a user-level LaunchAgent plist installed to `~/Library/LaunchAgents/`.
- `RunAtLoad` and `KeepAlive` ensure bots start on login and restart on crash.
- `ThrottleInterval` prevents rapid crash loops (30-second minimum between restarts).
- The plist sets `HOME`, `PYTHONUNBUFFERED`, and a conservative `PATH`. Use absolute paths for CLI binaries in `agents.toml` rather than relying on PATH.

---

## Slash Command Sync (legacy — removed)

> **⚠️ Legacy** — The new `multinexus/` architecture uses text-based operator
> commands (`agents`, `health`, `session status`, `session reset`), not Discord
> slash commands. The `bot.py` tree-sync code and `config.yaml` `dev_guild_id`
> shown below have been removed. This section is retained for historical
> reference only.

---

## Private Wiki / DB Setup

Private wiki pages are stored in `wiki/private/` inside the repo tree, but gitignored — they
never leave your machine. No setup is required for this; the bot creates the directory on first run.

`PRIVATE_DB_PATH` controls where the *private SQLite database* is stored (metadata, sessions).
This is optional — if unset, the private DB is created alongside the main `nexus.db`.

To store the private DB at a custom location (e.g., outside any synced folder):

```
# .env
PRIVATE_DB_PATH=/absolute/path/to/nexus-private.db
```

On Windows, the bot applies `icacls` to restrict this file to the current user on first run.

---

## Troubleshooting

### Bot is online but not responding

- Check that **Message Content Intent** is enabled in the Discord Developer Portal
- Verify the channel ID is in `agent_channels` in `config.yaml`
- Check that the bot has permission to read messages in that channel

### Slash commands not appearing

- Wait up to 1 hour for global propagation, or use `dev_guild_id` for instant sync
- Make sure `applications.commands` scope was included in the invite URL

### Agent is offline

- Run `health` (text command) in Discord to check agent health
- Check the bot logs: `journalctl -u multinexus-discord-bridge` (Linux/systemd) or the launchd plist log path (Mac)
- For CLI agents: verify `claude --version` or `codex --version` works in the same environment
- For local LLM: verify the server is running and the model is loaded

### Windows: console window appears when agents run

This should not happen in normal operation. If it does, verify the adapter layer (`multinexus/adapters/`) is loading CLI agents
with the `_NO_WINDOW` flag (set in `agents/cli.py`). This flag is only applied on `sys.platform == "win32"`.

### Rate limit fallback not working

The fallback chain requires multiple agents to be configured and online.
Check `agents` (text command) to see which agents are available.
