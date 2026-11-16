# Zenlayer 默认通过 Tunnel 接入

用户在 2026-11-16 明确选择：本地 Codex 以后默认用现有 VS Code Tunnel 访问 Zenlayer。SMC/Kubernetes 是必要时的诊断备用路径，不替代日常 Tunnel 入口。

## 当前已验证入口

| 项目 | 已核实值 |
| --- | --- |
| Tunnel 名称 | `h200-b32-master0`（历史名称，不是实际 Pod 名） |
| 最近实际目标 | `avatar-c32-master-0`，root，HOME=/root，初始 cwd=/home/work |
| 共享工作区 | `/aigc/avatar/houyi` |
| VS Code 网页入口 | https://vscode.dev/tunnel/h200-b32-master0/aigc/avatar/houyi |
| 诊断备用入口 | `smc toc 10.220.43.97`，然后 `kubectl exec -it -n training avatar-c32-master-0 -c main -- bash` |

名称、Pod、IP 和账号状态需现场核实。不要把名称里的 h200/b32 推断为当前硬件或主机。保持现有 Tunnel 注册、登录、共享 Codex Home 与项目环境，不运行迁移启动器，不创建第二个 Tunnel。

## Mac 上的可执行客户端

需要本地 Node.js、GitHub 的本机 Git 凭据，以及已安装的官方 `ms-vscode.remote-server` 扩展。本实现已用 1.5.3 实测；脚本动态查找扩展目录，也支持 `--extension-path`。它从已安装扩展在内存加载同源客户端库，不改扩展文件，通过已有 Tunnel 运行 RPC。内部布局改变时会明确失败，先检查适配代码，不去关闭 TLS 校验或盲改模块编号。

先把 `REMOTE_SKILL_DIR` 设为本机实际已加载的 skill 目录；常见为 `~/.codex/skills/ais-remote-codex-setup` 或仓库安装的 `~/.agents/skills/ais-remote-codex-setup`：

```bash
REMOTE_SKILL_DIR="$HOME/.codex/skills/ais-remote-codex-setup"
node "$REMOTE_SKILL_DIR/scripts/zenlayer_tunnel.cjs" status
```

返回真实 hostname、共享目录是否存在、扩展版本和协议版本。核实目标后，以下示例用最近实测 hostname；目标换机时改成刚核实的实际 hostname。

```bash
node "$REMOTE_SKILL_DIR/scripts/zenlayer_tunnel.cjs" read --expect-host avatar-c32-master-0 --path /etc/hostname
node "$REMOTE_SKILL_DIR/scripts/zenlayer_tunnel.cjs" exec --expect-host avatar-c32-master-0 --cwd /aigc/avatar/houyi -- python3 -c 'import os; print(os.getcwd())'
```

`read` 输出原始文件字节，默认最多 1 MiB，可用 `--max-bytes` 调整。`exec` 直接传程序和参数，不额外插入 shell；需要 shell 时显式使用 `bash -lc '...'`。它转发 stdout/stderr 和退出码，stdin 也会传给远端进程；依赖交互式 TTY 的操作用官方 VS Code Tunnel 终端。执行前必须提供核实后的 `--expect-host`，目标不符会停止。

客户端的 GitHub token 仅由 `git credential fill` 读入本地内存。使用系统凭据助手；不要输出 helper 原始结果、SDK 完整错误对象、HTTP 认证头或服务器登录文件。脚本启用 TLS 证书验证。Git 凭据与 VS Code 登录可能属于不同存储；脚本缺凭据时用用户自己的本机 GitHub 授权处理，不从服务器复制登录状态。

## 一次连接处理多项任务

启动 `session` 后用 JSONL 交换请求；关闭 stdin 或发送 close 释放本次客户端连接。它保持同一个 Tunnel 客户端，避免每次操作重新认证和建连。

```bash
node "$REMOTE_SKILL_DIR/scripts/zenlayer_tunnel.cjs" session
```

收到 ready 后可逐行发送：

```json
{"id":1,"op":"status"}
{"id":2,"op":"read","path":"/etc/hostname","expect_host":"avatar-c32-master-0"}
{"id":3,"op":"exec","command":"python3","args":["-c","import os; print(os.getcwd())"],"cwd":"/aigc/avatar/houyi","expect_host":"avatar-c32-master-0"}
{"id":4,"op":"close"}
```

响应回显 id，exec 包含 stdout、stderr、exit_code 和 truncated。`stdin` 字符串可传给单次 exec；捕获输出按 `--max-bytes` 截断并明确标记。只执行本次用户任务，远端 root 权限不代表可以访问其他用户项目或重启服务。长任务按任务需要独立运行，不依赖聊天连接保持进程。

## Zenlayer 的 Codex 与环境

这里已有共享开发环境，连接本身不要求重装 Codex。需要检查 Codex 时先核实当前配置与环境脚本，再复用；历史共享 Home 为 `/aigc/avatar/houyi/restart_commands_h200/migrate_materials/.codex`。PATH、CODEX_HOME 与 Conda 路径以实际运行状态为准，不把 AIS 的 `/home/work/.codex` 覆盖过来。检查凭据只输出登录状态，不输出 auth.json 或历史会话内容。

## 故障诊断与已有实测

认证失败先核实本机 GitHub 账号；客户端适配失败先检查扩展版本；目标错误先重新运行 status，结合用户的新目标判断，不能绕过 expect-host。必要时通过 `smc-pam` 的 SMC 路径只读检查原 Tunnel 状态：

```bash
smc toc 10.220.43.97
kubectl exec -it -n training avatar-c32-master-0 -c main -- bash
bash /aigc/avatar/houyi/vscode_h200/manage_houyi_tunnel.sh status
```

备用 IP/Pod 也要核实；接入或诊断不运行 background/login/restart 等改变服务的动作，除非属于当前明确委托的修复。

2026-11-16 对同一个 Pod，用相同 Python 程序、交替顺序，各做 20 次连接内请求与 5 次新建连接。SMC/Tunnel 小请求中位数为 372/379 ms，读取 20 B 为 330/315 ms，新建连接（已登录）为 7.12/5.86 秒。结果支持复用连接；它是当时网络下的端到端测试，不是稳定性能保证，也不代表 VS Code UI 或大文件吞吐。

官方入口与架构说明：https://code.visualstudio.com/docs/remote/tunnels
