# Mac → SMC/PAM → Driver → AIS

先复用已有可用配置，不覆盖其他主机。2026-11-16 核实的历史实例：Driver 10.168.137.79 / yi.hou，Notebook 10.249.33.8 / work，专用端口 20222。换机时使用新 Notebook 输出，Driver 也要验证；不从 PDF 的同事示例推导用户名。

## Mac 的 PAM 入口

检查 `command -v smc`、`smc token status`、`smc sshconf show`。缺 CLI/插件或认证失效时使用现有 smc / smc-pam skill；浏览器或 SeaTalk 认证由用户完成。不要显示 `smc token export` 原始输出。

先备份 ~/.ssh/config、config.d/ais.conf、ssh_wrapper、scp 和 VS Code settings。有可用 wrapper 时保留。若需要生成：`assets/pam_ssh_wrapper.py` 是本案例实际验证实现的通用版本；复制到 ~/.ssh/ssh_wrapper 后，将首行设为本机已存在 Python 的绝对路径（用 sys.executable 查），chmod 700。Dock 启动 VS Code 的 PATH 可能不含 conda。

该 wrapper 通过 `ssh -G` 判断目标是否使用 SMC PAM identity，只有 Driver 才刷新认证；`target_ip=<解析出的 Driver IP>` 必须传给 `smc deviceauth get-svid-dpop`，否则 DPoP 与目标不匹配。所有 token/SVID 仅留内存与 SSH 子进程环境，不写日志。

在 wrapper **同一目录**生成名为 scp 的可执行脚本：

```bash
#!/bin/bash
exec /usr/bin/scp -S "$HOME/.ssh/ssh_wrapper" "$@"
```

VS Code 会查找旁边的 scp；缺它可能显示 SSH 已登录却始终无法上传 server。

## SSH config

从当前 `smc sshconf show` 提取该平台的 IdentityFile、ProxyCommand 和 SendEnv，限定到 `Host ais-driver`，设置真实 HostName 与 User。PAM 网关地址、端口和 key 路径由当前 SMC 导出，不固定历史网关 IP，不把其 `Host *` 全局复制进主配置。

下方仅是 AIS 段模板。用真实绝对 home、IP、端口和用户替换占位符：

```sshconfig
Host ais
    HostName <NOTEBOOK_IP>
    Port <DEDICATED_PORT>
    User <NOTEBOOK_USER>
    IdentityFile <MAC_HOME>/.ssh/id_ed25519_ais
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
    UserKnownHostsFile <MAC_HOME>/.ssh/known_hosts_ais
    ServerAliveInterval 30
    ServerAliveCountMax 3
    ProxyCommand <MAC_HOME>/.ssh/ssh_wrapper -F <MAC_HOME>/.ssh/config -W %h:%p ais-driver
```

确保 ~/.ssh/config 在可能匹配的 Host 通配段之前包含 `Include ~/.ssh/config.d/ais.conf`，权限 600。路径含空格按 OpenSSH 语法引用。Driver 段的 SendEnv 要覆盖：

```
LANG LC_* TOC_* SMC_USER_EMAIL SMC_TOKEN SMC_DEVICE_AUTH_USER_JWT_SVID SMC_DEVICE_AUTH_USER_DPOP_TOKEN
```

原生 `ssh ais` 通过 ProxyCommand 自动刷新 Driver 认证。单独测试 Driver 用 `~/.ssh/ssh_wrapper ais-driver hostname` 或 `smc toc <DRIVER_IP> hostname`；原生 `ssh ais-driver` 未注入认证环境时可能失败。

## Notebook 第一次启动专用 SSH

若已有 ~/.ssh/id_ed25519_ais 则复用，缺失才生成新的 ed25519 key。**私钥留在 Mac**。端口 22/2222 有 SSH banner 不等于连到了自己的 Notebook；本案例这些端口的服务均不是 Notebook 内所启动的服务。

在 Mac 渲染：

```bash
python3 <SKILL_DIR>/scripts/render_notebook_bootstrap.py --ip <NOTEBOOK_IP> --user work --output /tmp/ais-notebook-bootstrap.sh
pbcopy < /tmp/ais-notebook-bootstrap.sh
```

由助手在 Mac 执行 pbcopy，再让用户切到 AIS 网页终端 Command+V 执行。不要让用户在 Linux 执行 pbcopy。粘贴第一行必须是 `bash -s -- ... <<'CODEX_AIS_NOTEBOOK_BOOTSTRAP'`，避免同一交互 shell 的 readonly 变量导致重复执行失败。

脚本验证用户/IP，按需安装 openssh-server，保留现有 authorized_keys，生成/复用 ~/.ssh/ais-server 的专用 host key，在空闲的 20222/20223/20224/22022 启动独立 daemon，核对 localhost 实际 host key 后输出 AIS_SSH_READY 和指纹。不停止或修改其他 SSH 服务。Notebook 重建后需再次运行；持久化目录存在不代表 daemon 已启动。

用返回的实际端口更新 AIS config；连接时比对指纹。主机同 IP 重建引发指纹变化时，先从 Notebook 核实新指纹，备份 known_hosts 后仅替换该 `[IP]:port` 条目。不要 `StrictHostKeyChecking=no` 绕过 Notebook 验证。

## VS Code

先检查已安装 `ms-vscode-remote.remote-ssh`。备份并合并本地 JSONC settings，保留注释和其他键：

```jsonc
"remote.SSH.path": "<MAC_HOME>/.ssh/ssh_wrapper",
"remote.SSH.configFile": "<MAC_HOME>/.ssh/config",
"remote.SSH.remotePlatform": {"ais-driver": "linux", "ais": "linux"},
"remote.SSH.serverInstallPath": {"ais": "/home/work/.vscode-server-ais"}
```

若旧 ~/.vscode-server 属于 root，不整体 chown；选择当前用户可写的专用目录。先 `ssh ais 'id; hostname'`，再用 VS Code Remote SSH 打开 `ais:/home/work`（`code --remote ssh-remote+ais /home/work`）。安装路径变化或失败任务卡住时需在远端窗口 Developer: Reload Window；单纯反复打开同一 folder 可能仅聚焦旧窗口。Mac 无辅助功能控制权限时让用户按一次命令，不代其修改系统权限。

在 Mac 的 `~/Library/Application Support/Code/logs` 按实际修改时间查找 Remote - SSH.log，不能仅取目录名字最新的一份。只提取连接成功/失败行；连接 token、password、secret 行不展示。验收 management 与 extensionHost 已连接，再检查远端 Codex 扩展。
