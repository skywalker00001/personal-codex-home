---
name: ais-remote-codex-setup
description: 从 Mac 连接 AIS 或 Zenlayer 并维护远端 Codex 开发环境：AIS 经 SMC/PAM 与 Driver 配置 SSH、VS Code 和增量初始化；Zenlayer 默认复用现有 VS Code Tunnel，支持远程文件和命令操作。不用于默认启动训练、清理 GPU 或重建机器人服务。
---

# AIS / Zenlayer 远程开发与 Codex 配置

目标是由 Mac 上的 Codex 按用户指定目标连接 AIS 或 Zenlayer，读写对应项目并执行已授权的远端任务。先辨别 Mac、AIS 和 Zenlayer；`/aigc/avatar/houyi` 属于 Zenlayer，AIS 初始化源在 `/home/work/houyi`，它们都不是 Mac 本地目录。

## 按目标选择入口

- **Zenlayer 默认使用现有 VS Code Tunnel。** 用户已选择该方式；读取 [Zenlayer Tunnel 接入](references/zenlayer-tunnel.md)，使用 `scripts/zenlayer_tunnel.cjs`。现有名称 `h200-b32-master0` 是历史名称，连接后以 `status` 返回的实际 hostname 为准。批量操作用 `session` 复用连接。不要先走 SMC；Tunnel 故障时可用 SMC → 跳板机 → kubectl 做必要的只读诊断，并说明原因。
- **AIS 使用既有 SSH。** 已连通则复用 `ssh ais`；新建或更换 Notebook 时按下文恢复 SSH、增量初始化及 Codex。不要把 AIS 初始化脚本用于 Zenlayer。
- 用户同时提两台机器时，把路径、命令和验收明确归到对应目标。仅检查或接入不自动授权训练、清理或重启已有服务。

用户要求配置新机器即授权本流程内必要的增量修改，不逐步重复索要确认。先检查实际状态，跳过已通过的阶段。仅需查看文件时使用对应入口只读查看，不执行初始化。

## AIS：入口与换机

- 已连通：`ssh -o BatchMode=yes ais 'id; hostname; test -d /home/work/houyi && echo SHARED_HOME_OK'`。核实当前目标后继续远端阶段。
- 新机器：取得真实 Driver IP、Notebook `hostname -I`、`whoami` 输出。历史地址只作诊断线索，不能替代新目标。
- Mac 上查看 `~/.ssh/ais-tools/setup.json`、`~/.ssh/config.d/ais.conf` 与 VS Code settings，先备份再定点修改；保留其他主机、用户设置和注释。
- SSH 不通或首次接入：读取 [SSH 与 VS Code 接入](references/ssh-and-vscode.md)。配套 `scripts/render_notebook_bootstrap.py` 生成**独立 Bash 进程**的 Notebook 粘贴命令，`assets/notebook_sshd.sh` 启动专用高端口服务；`assets/pam_ssh_wrapper.py` 为 PAM Driver 动态注入认证。
- 新主机指纹从 Notebook 可信终端核实后才更新对应 `known_hosts_ais` 条目；不要全局关闭验证或清空 known_hosts。

第一次接入若尚无 SSH，只需用户在 AIS 网页终端粘贴一次公钥/sshd 初始化段。SMC、AIS、Codex 的个人身份验证可能需浏览器交互；不能声称能跳过这些验证。

## AIS：远端增量初始化

入口是 `/home/work/houyi/restart_commands/restart_all_commands.sh`。先读 [初始化映射与边界](references/incremental-init.md)，检查入口与三个子脚本当前内容；不要把原始私密内容输出到聊天或提交到 skill。

先定位目标已加载本 skill 的实际目录。仓库安装器使用 `~/.agents/skills/ais-remote-codex-setup`；独立安装也可能位于 `${CODEX_HOME:-$HOME/.codex}/skills/ais-remote-codex-setup`。已存在时复用该来源，避免重复安装或覆盖不同来源的同名 skill。尚未安装时随个人配置仓库安装，或同步完整 skill 目录。

远端设定实际目录后运行；下面覆盖两种默认布局，自定义位置按实际来源调整：

```bash
AIS_SKILL_DIR="$HOME/.agents/skills/ais-remote-codex-setup"
if [ ! -f "$AIS_SKILL_DIR/SKILL.md" ]; then
  AIS_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ais-remote-codex-setup"
fi
python3 "$AIS_SKILL_DIR/scripts/init_ais.py"
python3 "$AIS_SKILL_DIR/scripts/init_ais.py" --apply --packages --ais-login
```

第一个 Python 命令仅显示计划；第二个用于用户委托首次/恢复初始化的情况。助手检查计划后自主执行。`--apply` 本身只做增量文件与 Git 设置，额外两项分别补软件和恢复 AIS CLI 登录。若只需修 Codex，不必重做 AIS 登录。

- 脚本仅支持已审查的源脚本摘要；源内容有变时停止自动应用，检查实际差异后更新映射。不可绕过摘要检查直接整段重跑。
- 保留 `.bashrc`、现有 SSH 私钥、公钥授权和 `ais-server`；只增加缺失配置。服务器已有的 `.ssh/.bypy/.git-credentials` 仅在服务器本地补齐，文件内容和 token 不进入 skill 或 Mac。
- AIS CLI 登录与数据集已挂载分别验收。原脚本内数据集 mount 示例全部被注释；没有新的明确目标时不恢复这些历史挂载。
- 不运行 `restart_at_ais*.sh`，不启动 Cursor tunnel、GPU watchdog、训练或 `sleep infinity`。

## AIS：Codex、个人配置与远端扩展

连接后读取 [远端 Codex 安装与验收](references/codex.md)。沿用现有版本与账号，缺失时用官方 standalone 安装器。个人配置仓库为 `https://github.com/skywalker00001/personal-codex-home.git`；使用 `personal-codex-profile` 的 dry-run/install 流程，保留现有配置、凭据及其他技能。

初始化完成后检查新登录 shell 的 PATH。不能把 `~/.local/bin` 只写在 `.bashrc` 的非交互提前 return 后面。不要复制 Mac 的 `auth.json`；远端未登录才启动 `codex login --device-auth`，由用户完成当次授权。

验证文件、CLI、认证和实际运行时：

```bash
bash -lc 'command -v codex; codex --version; codex login status'
python3 "$AIS_SKILL_DIR/scripts/verify_codex.py" --require-skill personal-codex-profile --require-skill ais-remote-codex-setup
```

首次完整配置可加 `--model-test` 做一次只读、临时的真实模型调用。普通健康检查不必重复付费调用。最后在 VS Code 日志核实成功连接和远端扩展，不能仅用进程存在代替验收。

## 交付与日后调用

交付本次目标（AIS 或 Zenlayer）、实际主机、所用连接方式、IP/端口或 Tunnel 名称、SSH/VS Code 结果、初始化各项状态、Codex 登录/skills 加载结果及未完成的实际挂载或用户验证。配置路径和备份位置写入机器自己的 `~/.ssh/ais-tools/setup.json` 或本地状态目录，技能本身不记录会变化的凭据。

日后用户可说：`用 $ais-remote-codex-setup 接入新 AIS，Driver 是 …，Notebook IP 是 …，用户是 work，按我的初始化流程补配置并验证 Codex。` 未给新 IP 时先查用户提供的当前 Notebook 信息。若仅查看现有 AIS 内容，直接复用已连通的 SSH。日后用户说“查看 Zenlayer 的某个文件”或“在 Zenlayer 执行任务”，默认使用 Tunnel；可显式调用 `用 $ais-remote-codex-setup 通过 Tunnel 连接 Zenlayer 并查看 /aigc/avatar/houyi/...`。
