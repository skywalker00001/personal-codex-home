# 初始化映射

2026-11-16 在实际 AIS 只读核验的入口：`/home/work/houyi/restart_commands/restart_all_commands.sh`。本 skill 不修改原脚本。`scripts/init_ais.py` 内有四个已审查文件的 SHA256；任何一个变化都要求重新阅读，不假设旧行为仍成立。

| 原入口操作 | 增量实现与验收 |
| --- | --- |
| install_package.sh | dpkg 只查询缺失包，必要时 apt update/install。原列表 tmux、gawk、net-tools、zip、unzip、ffmpeg、parallel、iputils-ping、aria2、yt-dlp，另补 ripgrep、rclone 和隔离 AIS CLI 所需的 python3-venv。无缺失不更新系统。 |
| configurate_bashrc_and_vscode_debug.sh | 保留当前 .bashrc，加一个有标记且仅交互式 source 持久化 /home/work/houyi/.bashrc 的区块；PATH 在非交互 return 前及 source 后均可用。兼顾已有 .bash_profile/.bash_login 的登录 PATH。修改前备份，检查 bash -n。 |
| 同上 .ssh | authorized_keys 取并集；其他文件仅目标缺失才复制，既有私钥/config/专用 sshd 不覆盖；不跟随符号链接去复制未知树。 |
| 同上调试/工具配置 | .vscode/launch.json、pyrightconfig.json、.cursorignore 仅缺失时补。 .bypy 和 .git-credentials 只服务器本地复制缺失项，权限收紧，不打印内容。 |
| git config --global | 从审查过的入口解析 user.name/user.email；现有值保留。 |
| mount_datasets.sh | 查找已存在的持久化 AIS CLI；缺失才装到独立 venv，避免改变训练环境。只有 --ais-login 才执行源脚本中那条活跃的 ais login，秘密在远端内存读取，捕获所有输出。 |
| 注释中的 dataset/model mount | 不执行。CLI 可运行、登录成功、真实挂载分别报告。用户给出挂载目标时先查 mountpoint/已有进程再定点操作。 |

`--apply --packages --ais-login` 适合明确委托新 AIS 初始化。普通 Codex 修复用 `--apply` 或只运行 Codex 检查即可。来源不完整时报告缺失路径，不下载一份包含私钥/token 的替代初始化包。

实现不会自动用旧 AIS 登录凭据覆盖一个已验证的不同身份；执行 --ais-login 前核实源脚本登录邮箱是否仍是用户预期账号。若旧 token 失效，转用户自己的 AIS 登录，不索取其密码，不打印原 token。

备份位于目标 `~/.local/state/ais-remote-codex-setup/backups/<timestamp>/`。同名配置冲突保留并显示 PRESERVE；这需要按实际用途处理，不能把 PRESERVE 误报为内容已迁移。source 持久化 bashrc 会沿用用户原环境，应先检查它是否包含当前不需要的自动任务。
