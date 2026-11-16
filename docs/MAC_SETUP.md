# Mac 安装与验收

## 安装

1. 安装适用于自己 Mac 的 Codex 客户端或 CLI，参考 [官方安装文档](https://learn.chatgpt.com/docs/codex/cli)。Linux 的 Codex 二进制与 Python 虚拟环境不应直接搬到 macOS。
2. 克隆仓库，执行 `bash install.sh --dry-run`，确认将使用的 Codex Home 与 skills 目录。
3. 执行 `bash install.sh`，再用自己的账号完成 `codex login`。
4. 在新的 Codex 会话运行 `/skills`。可先请它“阅读个人 AGENTS 指引，列出与你本次任务有关的技能，不执行服务器操作”。

要求 Python 3.9+。`python3 --version` 可查看版本。安装器本身不依赖 pip、Conda、CUDA、GitHub token 或第三方 Python 包。

## 已有本地配置

- 已有 `config.toml` 不会被覆盖。希望采用本仓库默认模型时，自行合并 `config/config.toml` 的两个配置项；模型必须是当前账号可用的模型。
- 已有 `AGENTS.md` 会保留，只追加或更新 `personal-codex-home` 标记之间的区块。变更前的文件备份到目标 Codex Home 的 `profile-backups/`。
- 如果存在 `AGENTS.override.md`，它会优先于 `AGENTS.md`，安装器会提示；需自己确认是否仍想保留该覆盖层。
- 同名外部 skill 默认保留并报告冲突。确认要替换才用 `bash install.sh --replace-skills`，旧内容先备份。
- 插件内置的 skill 可能与这里的名称重复。不要再把同一套技能同时放进 `~/.codex/skills`；用 `/skills` 核对来源后保留一份。
- 不在这里同步机器信任列表、Full access 设置、MCP 凭据或账号登录。服务器的授权范围不会自动延伸到本地电脑。

## 自定义位置

```bash
bash install.sh \
  --codex-home "$HOME/.codex-personal" \
  --skills-root "$HOME/.agents/skills"

CODEX_HOME="$HOME/.codex-personal" codex
```

安装和运行必须使用同一个 Codex Home。CLI 环境变量不保证自动传入从 Dock 启动的图形客户端；默认 `~/.codex` 最容易统一。需要自定义时按所用客户端的启动机制设置。

## 更新、验证与撤销

```bash
git pull --ff-only
bash install.sh
python3 scripts/doctor.py
```

技能链接会跟随 Git 内容变化。重新安装会更新全局偏好的受管理区块；原有 config 保持不动。

验收分两层：`doctor.py` 证明文件和链接安装正确；新客户端的 `/skills`、实际模型回复与远程 SSH 命令证明运行可用。本仓库没有在你的实体 Mac 上运行过，不能把 Linux 临时目录测试当作 Mac 端验收。

若要撤销，先读目标 Codex Home 中 `personal-profile-install.json`。只移除其中指向本克隆目录的技能软链接；只删 `AGENTS.md` 中本仓库的受管理区块。原有文件可从 `profile-backups/` 恢复，不要整体删除自己的 `~/.codex`。

官方加载位置见 [skills](https://learn.chatgpt.com/docs/build-skills) 和 [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。
