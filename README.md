# Personal Codex Home

Houyi 的精简 Codex 配置、可复用 skills 和项目经验。面向本地 Mac，也可安装到新的 Linux 开发机。

这是工作流程与知识的迁移，不包含模型权重或原始聊天记录。使用同样的模型和这些指引，可以尽量延续服务器上的协作习惯；实际能力仍取决于模型、工具、权限和可访问的项目。

## Mac 快速开始

先按 [官方说明安装 Codex](https://learn.chatgpt.com/docs/codex/cli)，再执行：

```bash
git clone https://github.com/skywalker00001/personal-codex-home.git
cd personal-codex-home
bash install.sh --dry-run
bash install.sh
codex login
codex
```

需要 Git 和 Python 3.9+。安装器只使用 Python 标准库，不安装 Python 包，不登录账号、不启动任何机器人或服务器。

打开一个新的 Codex 会话后，用 `/skills` 检查技能目录；例如输入：

```text
使用 $h3-performer-training-delivery 帮我规划一个实验，先不要启动。
```

安装器会：

- 将 `skills/` 中的技能链接到 `~/.agents/skills/`，保留完整的脚本、参考资料和部署附件。
- 将本仓库的协作偏好作为可更新区块加入 `~/.codex/AGENTS.md`，保留已有内容。
- 仅当配置不存在时创建 `~/.codex/config.toml`，默认模型 `gpt-6.1-sol`、推理强度 `xhigh`；已有配置保持不变。
- 不覆盖同名的外部 skill；冲突会明确列出，确需替换时使用 `--replace-skills`，原文件先备份。

如果设置了 `CODEX_HOME`，安装器会跟随它；也可使用 `--codex-home` 明确指定。用户级 skills 默认位置仍是 `~/.agents/skills`，可用 `--skills-root` 自定义。

## 内容

| 目录 | 用途 |
| --- | --- |
| [skills/](skills/) | 17 个技能，涵盖训练、飞书部署、个人配置迁移与 AIS 远程接入 |
| [AGENTS.md](AGENTS.md) | 中文协作偏好、实验证据与通知习惯 |
| [config/config.toml](config/config.toml) | 最少的可迁移默认配置 |
| [knowledge/](knowledge/) | 精选项目背景，区分不同实验协议 |
| [docs/MAC_SETUP.md](docs/MAC_SETUP.md) | Mac 安装、更新、冲突处理与验收 |
| [docs/REMOTE_SERVER.md](docs/REMOTE_SERVER.md) | Mac 与 Zenlayer 服务器如何配合 |
| [docs/SKILLS.md](docs/SKILLS.md) | 全部技能与运行依赖 |
| [docs/EXPORT.md](docs/EXPORT.md) | 本次导出范围、兼容性处理及遗漏说明 |
| [docs/VERIFICATION.md](docs/VERIFICATION.md) | 已通过的检查，以及仍需在目标 Mac 验证的内容 |
| [manifests/](manifests/) | 来源、版本与可校验的文件摘要 |

## AIS 远程开发环境

使用 [ais-remote-codex-setup](skills/ais-remote-codex-setup/SKILL.md)，从 Mac 经 SMC/PAM 与 Driver 连接 AIS，配置 VS Code Remote SSH，按原初始化入口增量恢复环境，并安装、登录和验证远端 Codex。附 Notebook SSH 启动模板、增量初始化与运行验证脚本。

换机时告诉 Codex：`用 $ais-remote-codex-setup 接入新 AIS，Driver IP 是……，Notebook IP 是……，用户是 work。` 首次 Notebook 公钥授权和个人账号验证可能需要交互；安装本仓库本身不会连接服务器或执行初始化。

## 手机飞书控制自己的 Codex

使用 [clawbot-feishu-deploy](skills/clawbot-feishu-deploy/SKILL.md)。里面包含：

- [完整部署指南](skills/clawbot-feishu-deploy/references/FEISHU_CODEX_DEPLOY.md)
- [配套源码包](skills/clawbot-feishu-deploy/assets/clawbot-feishu-deploy-20261113.tar.gz)

新部署使用自己的飞书应用、Codex 登录和私有状态目录。该部署包针对 Linux；Mac 上可以阅读和准备，常驻机器人建议部署在持续在线的 Linux 服务器。克隆及安装个人配置不会启动机器人或发送消息。

## 更新与检查

```bash
git pull --ff-only
bash install.sh
python3 scripts/doctor.py
python3 scripts/check_repo.py
```

技能通过软链接跟随仓库更新；个人配置不会被 `git pull` 覆盖。不要移动或删除克隆目录；如已移动，重新执行 `bash install.sh --replace-skills` 修复链接。

仓库不包含 `auth.json`、飞书 App Secret、SSH 私钥、Kubeconfig、历史会话、SQLite、缓存、机器信任名单或正在运行的任务。插件与第三方连接需要在目标客户端重新安装、授权。
