# 项目来源与维护说明

本项目基于 GitHub 上的 `baisiqi6/discord-nexus` 继续维护。

原始仓库：
https://github.com/baisiqi6/discord-nexus

分叉基线：
`97dc071f83f67c1a38b91f4d468ff014e1bbdf76`（`v0.2.0`，`Update CHANGELOG and README for v0.2.0`）

## 为什么单独维护

原项目已经较长时间没有继续更新。当前需求已经从单一 Discord bot 扩展到：

- OpenClaw CLI agent，而不是旧的 OpenClaw HTTP relay。
- Claude、Codex、小龙虾在同一频道里的 multi-agent 协作。
- 更好的 managed context：TTL、compaction、summary + recent raw history。
- KOOK 接入，用 KOOK bot 间可见消息和 WebSocket 机制尝试更自然的 agent 群聊。
- 后续接入 Windows 主机和云服务器上的 remote agent runner。

这些改动会逐步偏离原项目，所以使用独立仓库维护更清晰。

## 授权与署名

原项目 README 中标注 License 为 MIT。本仓库保留原始 Git 历史，并新增 `LICENSE` 文件记录授权声明。

约定：

- 原始代码归原作者与 contributors 所有。
- 本仓库新增和修改的代码归当前维护者所有。
- 后续发布、分享或二次分发时保留 MIT License 与本来源说明。

## Remote 约定

建议保留两个 remote：

- `upstream`：原始仓库，用于必要时查看或合并原作者更新。
- `origin`：当前维护仓库，用于日常开发、issue、PR 和 release。

```bash
git remote -v
```

## 本地配置不要入库

以下文件只用于本机运行，不应提交：

- `.env`
- `.env.*`
- `config.yaml`
- `data/`
- `*.db`
- `wiki/private/`

可提交的是 `config.yaml.example`，用于记录可公开的配置模板。
