"""Utility commands — slash commands, health dashboard, agent status.

Provides:
  /help      — full command list
  /monitor   — agent health and token usage
  /dashboard — auto-updating health embed
  /discover  — post a finding to #discoveries
  /claude, /codex, /mac-openclaw, /research — slash command entry points for agents
  /new-channel — register current channel with agents
  /restart   — restart the bot process
"""

import asyncio
import json
import logging
import os
import sys
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.fake_message import FakeMessage

log = logging.getLogger(__name__)

_bot_start_time: float | None = None
LOCAL_AGENT_NAME = "mac-openclaw"


class Utility(commands.Cog):
    """Slash commands and utility operations."""

    def __init__(self, bot):
        self.bot = bot
        self._dashboard_message: discord.Message | None = None
        self._monitor_last_called: dict[int, float] = {}
        global _bot_start_time
        _bot_start_time = time.monotonic()

    def _agent_label(self, agent_name: str) -> str:
        return self.bot.agent_configs.get(agent_name, {}).get(
            "display_name", agent_name.capitalize()
        )

    async def get_status(self) -> str:
        """Build a status string showing agent health and token usage."""
        bot_name = self.bot.config.get("bot", {}).get("name", "YourBot")
        lines = [f"**{bot_name} 状态**"]

        if _bot_start_time is not None:
            elapsed = time.monotonic() - _bot_start_time
            hours, rem = divmod(int(elapsed), 3600)
            mins, secs = divmod(rem, 60)
            lines.append(f"运行时长：{hours}时 {mins}分 {secs}秒")

        lines.append("")

        for name, agent in self.bot.agents.items():
            health = await agent.health_check()
            if health["status"] == "ok":
                self.bot._agent_status[name] = True
                model_info = health.get("model", "")
                totals = await self.bot.db.get_token_totals_24h(name)
                stats_parts = []
                if totals["tokens_input"] or totals["tokens_output"]:
                    stats_parts.append(
                        f"输入：{totals['tokens_input']:,} 输出：{totals['tokens_output']:,}"
                    )
                if totals["cost_usd"]:
                    stats_parts.append(f"${totals['cost_usd']:.4f}")
                lines.append(f"- {self._agent_label(name)}：在线（`{model_info}`）")
                if stats_parts:
                    lines.append(f"  24h token：{', '.join(stats_parts)}")
            else:
                self.bot._agent_status[name] = False
                lines.append(
                    f"- {self._agent_label(name)}：离线（{health.get('error', 'unknown')}）"
                )

        lines.append("- 数据库：已连接")
        return "\n".join(lines)

    @commands.command(name="help")
    async def help_command(self, ctx):
        bot_name = self.bot.config.get("bot", {}).get("name", "YourBot")
        local_label = self._agent_label(LOCAL_AGENT_NAME)
        await ctx.send(
            f"**{bot_name} 命令（用 `/help` 查看完整 slash 命令列表）：**\n"
            "\n"
            f"**Agent** — 用 `@Claude`、`@{local_label}`、`@Codex` 角色 mention，或 "
            "`/claude`、`/mac-openclaw`、`/codex`、`/research`\n"
            "**Wiki** — `/wiki [action] [page]`\n"
            "**工具** — `/monitor`、`/dashboard`、`/discover`、`/new-channel`、`/restart`"
        )

    @commands.command(name="monitor")
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def monitor(self, ctx):
        status = await self.get_status()
        await ctx.send(status)

    @commands.command(name="discover")
    async def discover(self, ctx, *, finding: str = ""):
        if finding:
            await self.bot._post_discovery(finding, "user")
            await ctx.message.add_reaction("📌")

    @commands.command(name="new-channel")
    async def new_channel(self, ctx, *, args: str = ""):
        await self.bot._handle_new_channel(ctx.message)

    # --- Slash commands for agents ---

    @app_commands.command(name="mac-openclaw", description="向 Mac OpenClaw agent 提问")
    @app_commands.describe(prompt="你的问题或 prompt")
    async def slash_mac_openclaw(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()
        await interaction.followup.send(f"**{interaction.user.display_name}:** {prompt}")
        await self.bot.handle_agent_request(
            agent_name=LOCAL_AGENT_NAME,
            prompt=prompt,
            thread_id=str(interaction.channel_id),
            channel=interaction.channel,
            user_id=interaction.user.id,
        )

    @app_commands.command(name="claude", description="向 Claude 提问")
    @app_commands.describe(prompt="你的问题或 prompt（针对 Claude）")
    async def slash_claude(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()
        await interaction.followup.send(f"**{interaction.user.display_name}:** {prompt}")
        await self.bot.handle_agent_request(
            agent_name="claude",
            prompt=prompt,
            thread_id=str(interaction.channel_id),
            channel=interaction.channel,
            user_id=interaction.user.id,
        )

    @app_commands.command(name="codex", description="向 Codex 提问")
    @app_commands.describe(prompt="你的问题或 prompt（针对 Codex）")
    async def slash_codex(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()
        await interaction.followup.send(f"**{interaction.user.display_name}:** {prompt}")
        await self.bot.handle_agent_request(
            agent_name="codex",
            prompt=prompt,
            thread_id=str(interaction.channel_id),
            channel=interaction.channel,
            user_id=interaction.user.id,
        )

    @app_commands.command(name="research", description="发送网络研究查询（需要 researcher agent）")
    @app_commands.describe(query="要研究的内容")
    async def slash_research(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        await interaction.followup.send(f"**{interaction.user.display_name}:** {query}")
        await self.bot.handle_agent_request(
            agent_name="researcher",
            prompt=query,
            thread_id=str(interaction.channel_id),
            channel=interaction.channel,
            user_id=interaction.user.id,
        )

    # --- Utility slash commands ---

    @app_commands.command(name="monitor", description="查看 bot 与 agent 状态")
    async def slash_monitor(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id or 0
        now = time.monotonic()
        last = self._monitor_last_called.get(guild_id, 0)
        if now - last < 30:
            await interaction.response.send_message(
                f"状态刚刚已发送 —— 请等待 {30 - int(now - last)} 秒。",
                ephemeral=True,
            )
            return
        self._monitor_last_called[guild_id] = now
        await interaction.response.defer()
        status = await self.get_status()
        await interaction.followup.send(status)

    @app_commands.command(name="help", description="显示所有可用命令")
    async def slash_help(self, interaction: discord.Interaction):
        bot_name = self.bot.config.get("bot", {}).get("name", "YourBot")
        local_label = self._agent_label(LOCAL_AGENT_NAME)
        await interaction.response.send_message(
            f"**{bot_name} 命令：**\n"
            "\n"
            "**Agent**\n"
            "`@Claude <消息>` — Claude（角色 mention）\n"
            f"`@{local_label} <消息>` — 本地 OpenClaw agent（角色 mention）\n"
            "`@Codex <消息>` — Codex（角色 mention）\n"
            "`/mac-openclaw <prompt>` — Mac OpenClaw 的 slash 命令\n"
            "`/claude <prompt>` — Claude 的 slash 命令\n"
            "`/codex <prompt>` — Codex 的 slash 命令\n"
            "`/research <query>` — 网络研究（需要 researcher agent）\n"
            "\n"
            "**Wiki**\n"
            "`/wiki [action] [page]` — 管理项目 wiki\n"
            "`/wiki-private [action] [page]` — 私有 wiki（仅 Mac OpenClaw）\n"
            "\n"
            "**工具**\n"
            "`/monitor` — agent 健康与 token 用量\n"
            "`/dashboard` — 自动刷新的健康面板\n"
            "`/discover <发现>` — 发布到 #discoveries\n"
            "`/new-channel [agents]` — 为当前频道注册 agent\n"
            "`/restart` — 重启 bot",
            ephemeral=True,
        )

    @app_commands.command(name="discover", description="发布一条发现到 #discoveries")
    @app_commands.describe(finding="要记录的发现")
    async def slash_discover(self, interaction: discord.Interaction, finding: str):
        await interaction.response.defer(ephemeral=True)
        await self.bot._post_discovery(finding, "user")
        await interaction.followup.send("已记录发现！", ephemeral=True)

    @app_commands.command(
        name="new-channel", description="Register current channel with agents"
    )
    @app_commands.describe(agents="要注册的 agent 名（留空则全部）")
    async def slash_new_channel(
        self, interaction: discord.Interaction, agents: str = ""
    ):
        await interaction.response.defer(ephemeral=True)
        content = f"!new-channel {agents}".strip()
        fake = FakeMessage(
            content, interaction.channel, interaction.user.id, interaction.guild
        )
        await self.bot._handle_new_channel(fake)
        await interaction.followup.send("完成。", ephemeral=True)

    @app_commands.command(name="dashboard", description="发送自动刷新的健康面板")
    async def slash_dashboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = await self._build_dashboard_embed()
        self._dashboard_message = await interaction.followup.send(embed=embed)
        if not self._dashboard_loop.is_running():
            self._dashboard_loop.start()
        await interaction.channel.send(
            "面板已发送，每 60 秒自动刷新。"
        )

    @app_commands.command(name="stop", description="停止当前频道正在运行的 agent")
    async def slash_stop(self, interaction: discord.Interaction):
        if not self.bot.allowlist.is_allowed(interaction.user.id):
            await interaction.response.send_message("未授权。", ephemeral=True)
            return
        agents_cog = self.bot.get_cog("Agents")
        if not agents_cog:
            await interaction.response.send_message("Agents 模块未加载。", ephemeral=True)
            return
        channel_key = str(interaction.channel_id)
        agent = agents_cog._active_agents.get(channel_key)
        if agent is None:
            await interaction.response.send_message("当前频道没有正在运行的 agent。", ephemeral=True)
            return
        await interaction.response.send_message(f"正在停止 {agent.name}…", ephemeral=True)
        agents_cog._active_agents.pop(channel_key, None)
        await agent.kill()

    @app_commands.command(name="restart", description="重启 bot 进程")
    async def slash_restart(self, interaction: discord.Interaction):
        if not self.bot.allowlist.is_allowed(interaction.user.id):
            await interaction.response.send_message("未授权。", ephemeral=True)
            return
        await interaction.response.send_message("Restarting...")
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
        )
        flag_path = os.path.join(data_dir, "restart_flag.json")
        with open(flag_path, "w") as f:
            json.dump({"channel_id": interaction.channel_id}, f)
        await asyncio.sleep(0.5)
        sys.exit(0)

    # --- Health dashboard ---

    async def _build_dashboard_embed(self) -> discord.Embed:
        """Build a rich embed with agent health information."""
        bot_name = self.bot.config.get("bot", {}).get("name", "YourBot")
        embed = discord.Embed(
            title=f"{bot_name} 健康面板",
            color=discord.Color.green(),
        )

        if _bot_start_time is not None:
            elapsed = time.monotonic() - _bot_start_time
            hours, rem = divmod(int(elapsed), 3600)
            mins, _ = divmod(rem, 60)
            embed.add_field(name="运行时长", value=f"{hours}h {mins}m", inline=True)

        all_ok = True
        for name, agent in self.bot.agents.items():
            health = await agent.health_check()
            if health["status"] == "ok":
                self.bot._agent_status[name] = True
                model = health.get("model", "?")
                embed.add_field(
                    name=self._agent_label(name), value=f"在线\n`{model}`", inline=True
                )
            else:
                self.bot._agent_status[name] = False
                all_ok = False
                embed.add_field(
                    name=self._agent_label(name),
                    value=f"离线\n{health.get('error', '?')[:50]}",
                    inline=True,
                )

        if not all_ok:
            embed.color = discord.Color.red()

        embed.set_footer(text=f"更新于：{time.strftime('%H:%M:%S')}")
        return embed

    @commands.command(name="dashboard")
    async def dashboard_cmd(self, ctx):
        """Post the health dashboard embed (auto-updates every 60s)."""
        embed = await self._build_dashboard_embed()
        self._dashboard_message = await ctx.send(embed=embed)
        if not self._dashboard_loop.is_running():
            self._dashboard_loop.start()
        await ctx.send("面板已发送，每 60 秒自动刷新。")

    @tasks.loop(seconds=60)
    async def _dashboard_loop(self):
        """Update the pinned dashboard embed every 60 seconds."""
        if not self._dashboard_message:
            return
        try:
            embed = await self._build_dashboard_embed()
            await self._dashboard_message.edit(embed=embed)
        except discord.NotFound:
            log.info("Dashboard message deleted — stopping loop")
            self._dashboard_message = None
            self._dashboard_loop.stop()
        except Exception as e:
            log.warning("Dashboard update failed: %s", e)

    def cog_unload(self):
        if self._dashboard_loop.is_running():
            self._dashboard_loop.cancel()


async def setup(bot):
    cog = Utility(bot)
    await bot.add_cog(cog)
    bot.get_status = cog.get_status
