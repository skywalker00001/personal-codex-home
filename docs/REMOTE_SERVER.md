# Mac 与 Zenlayer 服务器配合

本地安装提供指引和技能，不会让 Mac 自动获得共享盘、GPU、Kubernetes 凭据或服务器的 Codex 会话。

## 两种使用方式

**在服务器运行 Codex。** Mac 通过 SSH、已有 VS Code Remote 或 Tunnel 接入服务器，在远程终端运行 Codex。执行工具和共享盘都在服务器，现有环境通常最容易复用。

**在 Mac 运行 Codex，再通过 SSH 操作服务器。** 本地 Codex 负责代码与分析；需要查 `/aigc`、GPU、训练进程时，明确通过自己的 SSH 别名执行。SSH 连接和集群权限由用户另行配置，不从 Git 仓库下载私钥或 kubeconfig。

例如在自己电脑的 SSH 配置中建立 `zenlayer-dev` 别名后，先做只读检查：

```bash
ssh zenlayer-dev 'hostname; uname -s; test -d /aigc/avatar/houyi && pwd'
```

别名是示例，不是现成可用的主机。先验证目标，再在授权范围内执行任务。

## skills 里的绝对路径

导出的训练、迁移与机器人维护技能保留原部署的 `/aigc/...` 路径，以便在服务器上定位代码。它们不是 Mac 本地目录，也不随本仓库复制项目源码、模型、数据、Python 环境或运行状态。

Linux 专属的 `/proc`、`lslocks`、`pidfd`、`nvidia-smi` 不应在 macOS 照搬。处理 Mac 本地 Codex 锁时，需要读取当前版本提供的状态和 macOS 进程工具；保留“确认真实持有者、不删除数据库、不全局杀进程”的原则。

迁移旧服务器服务与新部署自己的服务是不同任务：前者复用仍存在的共享身份和状态，使用 `houyi-workspace-migration`；后者使用 `clawbot-feishu-deploy` 自己登录、创建应用和绑定。技能文字无法找回已经丢失的私有状态。

## 操作授权

历史文档中的机器名、优先级、停止命令只用于理解当时的做法，不是本次清理机器或发消息的授权。当前任务明确指定范围时，可按该范围执行，无需反复索取相同授权。
