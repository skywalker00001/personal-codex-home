# 技能目录

安装位置为 `~/.agents/skills/`。自动匹配由客户端决定；标为“显式调用”的技能使用 `$技能名`。原有选择策略予以保留。

| 技能 | 用途 | 调用 |
| --- | --- | --- |
| [autonomous-training-delivery](../skills/autonomous-training-delivery/SKILL.md) | Use when a user delegates a model training, inference, evaluation, or training-debug task and expects Codex to own the full workflow end to end: infer the goal from context, inspect the repo and environment, choose or build launchers, prepare configs/data, run smoke tests, launch or stage training, monitor/debug, run inference tests, preserve artifacts, self-audit correctness against the user's intent, and deliver evidence without asking for every intermediate step. | 自动匹配 / 显式调用 |
| [clawbot](../skills/clawbot/SKILL.md) | 创建、配置、维护或排查 Houyi 的飞书和微信 Codex 聊天机器人，包括飞书原生卡片布局、会话与历史、模型和权限、微信语音与发图、服务恢复。用于 /aigc/avatar/houyi/codex_wechat_bridge 这套单微信单飞书实现；不用于安装同名第三方 Clawbot/OpenClaw 产品。 | 自动匹配 / 显式调用 |
| [houyi-workspace-migration](../skills/houyi-workspace-migration/SKILL.md) | 在共享 /aigc 文件系统仍保留时，将 Houyi 的 VS Code Tunnel、Codex 登录与会话、一个微信和一个飞书机器人、网页及 Cloudflare 隧道迁移到新 Linux 主机，或在容器故障后恢复。沿用原 Tunnel 身份和共享状态，不重新整包搬运 VS Code。不适用于训练任务迁移或重建丢失的共享盘。 | 自动匹配 / 显式调用 |
| [video-timestep-evaluation](../skills/video-timestep-evaluation/SKILL.md) | Design and run model-agnostic video denoising-timestep evaluations, including candidate schedules, resident multi-GPU inference queues, MMS publication, and comparison dashboards. Use when testing custom timestep lists across video models or inference implementations. | 自动匹配 / 显式调用 |
| [wan-h200-sft-sop](../skills/wan-h200-sft-sop/SKILL.md) | Use when working on the Wan2.1-T2V-14B 25fps/33-frame SFT workflow in DiffSynth-Studio on H200 pods, including training-rule design, data/aspect-bucket checks, smoke tests, 64-GPU kubectl/tmux launch, monitoring, checkpoint validation, inference/AB eval, and Helios DMD teacher export planning. | 自动匹配 / 显式调用 |
| [codex-transcript-recovery](../skills/codex-transcript-recovery/SKILL.md) | Recover a prior Codex discussion when the VS Code/sidebar history is incomplete, especially for a concrete topic such as VBench Long; search user messages before treating JSONL hits as evidence. | 自动匹配 / 显式调用 |
| [codex-vscode-remote-extension-activation](../skills/codex-vscode-remote-extension-activation/SKILL.md) | Safely force-update Codex in VS Code Remote SSH or diagnose a Codex Audio dependency; use when installation succeeds but activation, app-server version, or local UI-host state is unclear. | 显式调用 |
| [codex-writer-lock-audit](../skills/codex-writer-lock-audit/SKILL.md) | Audit or release a named/all Codex writer locks without deleting state; use for requests to unlock Codex sessions or diagnose a stuck writer lock. | 显式调用 |
| [h3-performer-training-delivery](../skills/h3-performer-training-delivery/SKILL.md) | Prepare, launch, validate, and publish a scoped MiniMax-H3 Performer continuation when the user delegates a Performer experiment end to end. | 显式调用 |
| [helios-hy-exp-status-check](../skills/helios-hy-exp-status-check/SKILL.md) | Check a Helios hy_exp run and answer the user's usual questions: how many GPUs, what step it reached, whether it is still training, and whether a slow start is still healthy. | 自动匹配 / 显式调用 |
| [helios-transformer-distill-diff](../skills/helios-transformer-distill-diff/SKILL.md) | Build or verify a Helios transformer A-B distill diff when the user wants a reusable diff artifact, especially if they insist the 6 patch_short/mid/long weight+bias keys must participate. | 自动匹配 / 显式调用 |
| [houyi-gpu-stop-and-verify](../skills/houyi-gpu-stop-and-verify/SKILL.md) | Stop a named training, inference, ODE, or service workload on Houyi pods and verify scoped GPU cleanup when the user says “停了吧”, “清空显存”, or “确保没有任何显存程序”. | 显式调用 |
| [houyi-video-publish-verify](../skills/houyi-video-publish-verify/SKILL.md) | Publish a completed Houyi video directory through an existing file server/Cloudflare path and prove browser-seekable playback with HTTP Range, not only HTTP 200. | 显式调用 |
| [longlive-stage1-export-validation](../skills/longlive-stage1-export-validation/SKILL.md) | Export a LongLive or LongCat stage-1 AR sharded checkpoint to a native generator directory and validate it efficiently, especially when the user wants fast T2V/I2V checkpoint verification without disturbing the active training pod. | 自动匹配 / 显式调用 |
| [clawbot-feishu-deploy](../skills/clawbot-feishu-deploy/SKILL.md) | 新用户在自己的 Linux 上部署手机飞书 Codex，附指南与源码包 | 自动匹配 / 显式调用 |
| [ais-remote-codex-setup](../skills/ais-remote-codex-setup/SKILL.md) | Mac 经 SMC/PAM 连接新 AIS，增量初始化并配置远端 Codex | 自动匹配 / 显式调用 |
| [personal-codex-profile](../skills/personal-codex-profile/SKILL.md) | 安装、迁移和维护本个人配置仓库 | 自动匹配 / 显式调用 |

## 运行依赖

- `ais-remote-codex-setup`：Mac 的 Python、SSH、SMC/PAM 与 VS Code Remote SSH；AIS 的 `work` 用户、sudo 和持久化 `/home/work/houyi` 初始化来源。凭据留在各自机器，按需交互授权。

- `personal-codex-profile` 与安装器：本地 Git、Python 3.9+。
- `clawbot-feishu-deploy`：自己的 Linux、Python 3.10+、tmux、Codex 登录、飞书应用；包内依赖按部署指南安装。
- `clawbot`、`houyi-workspace-migration`：维护原 Houyi 部署，依赖相应服务器代码和共享状态，不是任意机器直接启动的程序。
- GPU 训练、状态、权重导出类：依赖对应服务器项目、Python 环境、模型数据和本次任务授权。
- `codex-transcript-recovery`：只查目标用户实际存在的历史。本仓库没有导出历史，因此新装 Mac 无法靠这个技能找回旧会话。
- 锁审计中的 `/proc`、`lslocks`、pidfd 路径只适用于 Linux；Mac 需采用当前客户端与系统支持的进程检查方式。

技能里的历史绝对路径用于定位，不代表依赖已包含。安装器不会自动拉取项目、占用 GPU、启动服务或发送消息。
