---
name: "houyi-workspace-migration"
description: "在共享 /aigc 文件系统仍保留时，将 Houyi 的 VS Code Tunnel、Codex 登录与会话、一个微信和一个飞书机器人、网页及 Cloudflare 隧道迁移到新 Linux 主机，或在容器故障后恢复。沿用原 Tunnel 身份和共享状态，不重新整包搬运 VS Code。不适用于训练任务迁移或重建丢失的共享盘。"
metadata:
  source-snapshot: "2026-11-16"
---

# Houyi 工作环境迁移恢复

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


将 `/aigc/avatar/houyi/vscode_h200/start_all_pretrain_f_224_worker_3.sh` 的恢复范式用于新的兼容主机。用户只要求查看或编写迁移文档时，不启动或停止任何服务；实际迁移请求才执行恢复流程。

本技能配套 [scripts/prepare_target.py](scripts/prepare_target.py)，用于生成新主机的启动入口。默认只输出计划；`--write` 只写启动脚本，不启动服务、不复制状态、不创建 Tunnel。原服务脚本与数据仍从共享盘复用。

## 保持不变的内容

- VS Code Tunnel 名称始终为 `h200-b32-master0`，保留共享 `code_tunnel.json` 中的原注册 ID。旧入口为 `https://vscode.dev/tunnel/h200-b32-master0/aigc/avatar/houyi`；名称不是实际主机名。
- `CODEX_HOME` 使用原共享目录，保留登录、历史会话、数据库、模型及权限配置。先进入 `/aigc/avatar/houyi` 查找历史，不用 `codex resume --all` 扫描其他用户。
- 只保留一个微信机器人和一个飞书机器人。沿用原凭据、所选会话、收发队列；不创建第二个微信实例、不重新扫码覆盖有效绑定。
- 不解压或复制整套 `.vscode` / `.vscode-server` 来迁移 Tunnel 身份，不自动注销旧注册或创建带新机器名的 Tunnel。
- 不因锁文件存在就删除它；不批量杀死 Codex app-server、训练进程或其他用户服务。先识别真实持有者。
- 不把恢复服务扩大成训练迁移、GPU 占用或升级整个 Conda 环境。清理备份也不属于默认恢复动作。

## 适用条件与持久化路径

当前实现在同一路径挂载共享盘的 **Linux x86_64、root、实际 HOME 为 `/root`** 上验证过；现有 CLI 与虚拟环境使用这些路径。不能通过修改 HOME 冒充原用户。ARM、其他 OS、非 root 或不同挂载位置需要适配路径和运行时后再验收。

以下 `/aigc` 数据必须仍在；`/root`、`/home/work` 清空可按流程重建。如果共享身份、账号凭据或会话数据库本身丢失，应报告缺失并按对应组件恢复，不能声称仅凭技能文本能找回内容。

| 内容 | 路径 |
|---|---|
| 工作区 / 控制脚本 | `/aigc/avatar/houyi` / `vscode_h200/` |
| Codex Home | `/aigc/avatar/houyi/restart_commands_h200/migrate_materials/.codex` |
| VS Code Tunnel 身份与 CLI 数据 | `/aigc/avatar/houyi/vscode_h200/.vscode/cli` |
| 原 Tunnel 环境 | `/aigc/avatar/houyi/vscode_h200/tunnel_env.sh` |
| Codex / PATH 环境 | `/aigc/avatar/houyi/migration_backups/b200_to_h200_20261016T091927Z/h200_env.sh` |
| 固定版 Codex / Node 运行时 | 上述迁移目录的 `runtime/` |
| VS Code CLI 程序 | 上述迁移目录的 `target_pretrain_f_256/bin/code` |
| 桥接程序与 Python 环境 | `/aigc/avatar/houyi/codex_wechat_bridge/`，含 `.venv`、`.venv_feishu` |
| 微信唯一实例 | `/aigc/avatar/houyi/.codex-wechat-bridge-state/weixin` |
| 飞书实例 | `/aigc/avatar/houyi/.codex-feishu-bridge-state` |
| Shell / SSH 等恢复材料 | `/aigc/avatar/houyi/restart_commands_h200/migrate_materials/` |
| 默认交互环境 | `/aigc/avatar/houyi/miniforge3/envs/multitalk` |
| 网页清单与历史映射 | `/aigc/avatar/houyi/migration_backups/h200_followup_20261016/` |

**`migration_backups` 下的运行时、环境脚本和 CLI 仍在被直接使用。** 目录名中的 B200、旧节点名是历史命名，不代表运行依赖旧机器；不要因换机就改路径、删除该目录或全量覆盖它。

核心环境应来自现有文件，不重新编造：

```bash
source /aigc/avatar/houyi/migration_backups/b200_to_h200_20261016T091927Z/h200_env.sh
source /aigc/avatar/houyi/vscode_h200/tunnel_env.sh
```

其中 `VSCODE_CLI_DATA_DIR=/aigc/avatar/houyi/vscode_h200/.vscode/cli`、`VSCODE_CLI_USE_FILE_KEYCHAIN=1`。不需要改变 HOME，也不要改为新机器本地的空 Codex Home。

## 先判断旧机能否继续运行

读取 `h200_followup_20261016/active-web-host.json` 和目标机上的进程、tmux、共享锁。记录新旧主机、旧服务是否仍运行、原 Tunnel 注册身份；不要把旧日志中的 PID 当成新机进程。

- **故障接管：** Kubernetes 成功查询后旧 Pod 不存在，或其状态为 `Failed` / `Succeeded`，可作为旧机已停止的证据。网页恢复程序会自动核验并记录 `handoff.json`。查询 Forbidden、网络失败、SSH 不通、Pod 正在删除，都不能直接当作服务已停止。未知共享锁仍须审计。
- **计划切换：** 先准备好新机入口和依赖；检查旧桥接任务、待发送回复和待处理入站队列，再从旧机的独立终端停止原服务。使用 `manage_wechat.sh stop`、`manage_feishu.sh stop`，并以 `stop_migrated_web.py --host 旧主机 --stop` 停止网页守护与网页进程；核验退出及锁释放后再接管。
- **VS Code / 当前聊天仍在旧机：** 先明确断连点。只在已获授权的切换中，从独立终端对已核实的旧 Tunnel 执行停止；不要为了“预检”关闭当前聊天。需要关闭 app-server 时逐个确认 executable、CODEX_HOME、PID 启动时间、FD 与锁归属，不能 `pkill -f codex`。
- **非 Kubernetes 场景：** 保留同样的单写者约束。通过旧机进程审计或管理平台确认已停，再将真实证据记录到交接状态；不要把自动 Pod 查询失败改成无条件成功。网页共享标注 API 本身也使用 `.single_writer.lock`。

原 `stop_source_houyi_for_h200.sh`、`stop_h200_for_b200.sh` 带历史主机限制。可以读作参考，不能在新主机上盲跑或仅删除它们的主机检查。

## 在新主机准备并启动

1. 检查 `hostname -s`、`id -u`、`uname -m`、真实 HOME 和共享目录。现有网页程序使用 `socket.gethostname()`，启动器使用短主机名；若系统设置为 FQDN，先统一其命名方式，不能只改启动器绕过检查。
2. 核对表中程序和状态文件存在；只检查凭据是否齐全，不输出 token、私钥、完整环境或认证 JSON。微信目录、飞书私有状态保持原权限。
3. 检查 `python3`、`flock`、`tmux`、`git`、`ffprobe`，共享 Codex / Node、桥接 Python 能运行。主启动脚本会补缺失的 tmux/git；`start_web_services.sh` 可复用共享 cloudflared。其余缺失按实际错误补系统依赖；`restart_commands_h200/install_package.sh` 是现有缺包安装参考，不等于已经在任意新机验证完所有依赖。
4. 生成绑定新主机的启动入口。不要直接在其他机器运行硬编码为 f224 的原入口，也不要修改它以破坏当前可用入口：

```bash
houyi_root=/aigc/avatar/houyi
houyi_skill="$houyi_root/restart_commands_h200/migrate_materials/.codex/skills/houyi-workspace-migration"
houyi_target="$(hostname -s)"

# 只看计划，不写文件、不启动服务。
python3 "$houyi_skill/scripts/prepare_target.py" --host "$houyi_target"

# 写入几 KB 的新主机入口，既不搬运账号数据也不创建新 Tunnel。
python3 "$houyi_skill/scripts/prepare_target.py" --host "$houyi_target" --write

# 在该新主机实际恢复；旧服务接管条件必须已经满足。
bash "$houyi_root/vscode_h200/targets/$houyi_target/start_all.sh"
```

工具复用当前 f224 启动逻辑，只替换目标主机、目标日志/锁目录和入口路径。原模板结构变化或目标文件内容不同会明确停止；先对比并按本次任务范围更新，不无条件覆盖。可用 `--output` 指定另一入口路径。

同一主机反复执行会保留已运行且身份验证通过的服务。生成器的 `--write` 本身不做依赖安装、登录、锁释放或故障切换，不能把生成成功当作迁移成功。

### 总启动流程覆盖的内容

1. 检查微信/飞书共享配置、服务锁和 Codex 会话写锁；允许核实为本机的原持有者，不删除锁文件。
2. 验证桥接导入依赖；`sync_houyi_shell.py` 合并 `.bashrc`，恢复默认 multitalk 和缺失的 SSH / Git / bypy 等辅助配置。已有辅助文件保留；该步骤会保存小型 Shell 变更回执，不会整包复制 VS Code。HF 等导出默认值来自材料，迁移前如有更新应先核对。
3. 检查原 Codex 登录、共享 Tunnel 登录，启动一个微信、一个飞书和同名 VS Code Tunnel。
4. 恢复网页清单中的全部 origin、Cloudflare 隧道和旧 URL 转换代理，更新入口与映射并执行公网验收。
5. 输出组件状态；任何组件失败均保留已启动服务与共享数据，按日志修复后可重跑。

## 登录、会话和 VS Code 扩展

- `"$CODEX_BRIDGE_BIN" login status` 检查原 Codex 登录。有效则复用；确实过期才处理 Codex 登录。原会话仍在共享 Home，不能通过新建 Home 或新账号代替恢复。CLI 续聊应在工作区使用原 session ID，避免与仍活跃的同一会话并发写入；可用只读 `thread/read` 验证历史。
- `manage_houyi_tunnel.sh status` 同时检查 Tunnel 与 GitHub 登录。只有未登录或凭据无法解密时执行 `manage_houyi_tunnel.sh login`，用户可能需完成一次 GitHub 设备授权。文件密钥链凭据在换主机后可能无法复用；不要承诺永久免授权。重新登录不需要创建新 Tunnel，也不应改掉原 ID。
- 微信和飞书凭据沿用共享目录；只有实际失效时才处理对应账号绑定。不要为了恢复而清空凭据、队列或会话选择。
- **Tunnel 身份、Codex 历史和 VS Code 扩展/用户设置是不同的数据。** 共享 CLI 保存原入口及服务器缓存，但当前默认扩展/用户设置可能位于本机 `/root/.vscode-server`，不能声称它们自动全部持久化。新机缺 `openai.chatgpt` 等扩展时按实际需要补装；CLI `code tunnel --help` 中的 `--install-extension` 可用于显式安装。需要该方式时先检查并适配 `manage_houyi_tunnel.sh` 的实际启动命令，不另开一个 Tunnel。不要为了补扩展解压整套旧归档。

## 网页和 Cloudflare 必须一起恢复

使用 `/aigc/avatar/houyi/vscode_h200/start_web_services.sh start|status`，不能只启动静态文件浏览器。总入口已调用它。

- `mirror_web_services.py` 读取 `b200-web-inventory.json` 中当前清单。已验收实例有 13 个服务；以后以实际清单为准，不把数量写死成通过条件。
- 5126 是 T2V DMD 面板服务，含 `/latest-v3p4/`；5125 包含实验文件与共享标注 API；5315 是 Exp1.10.5 媒体。其他登记服务同样恢复，不丢弃页面间依赖。
- 使用原 Flask 文件浏览后端、实验专属服务和 Node 面板，不改动实验结果文件。`migrated_web_proxy.py` 会将历次公网域名及恢复媒体地址转换到新地址，不要用全局替换重写原始 HTML、结果 JSON 或标注数据。
- 目前是无需 Cloudflare 账号登录的临时 Tunnel。`setup_fixed_tunnel.sh` 的历史配置不等于固定域名已经配置好，不把 `UUID.cfargotunnel.com` 当作现成公网网站；固定域名需要单独的域名与账号配置。
- `houyi-web-watch` 每 60 秒复查，恢复已退出的网页服务/隧道；隧道重新创建后更新映射，公网未通过时重试。正常运行的隧道不主动轮换域名。
- 新域名生效与 DNS 负缓存可能需要等待。验收器可在集群 DNS 仍返回 NXDOMAIN 时查询公共 DNS，并继续校验正常 HTTPS 证书；不修改系统 DNS，不关闭 TLS 校验。DNS 仍不存在时不能标记为发布成功。

入口和证据都在共享盘，不把本次临时域名写成永久地址：

| 文件 / 会话 | 用途 |
|---|---|
| `vscode_h200/WEB_LINKS.md` | 当前实验页入口与全部新旧地址映射入口 |
| `h200_followup_20261016/web_实际主机名/url-map.json`、`LINKS.md` | 该主机的实际 URL 映射 |
| 同目录 `verification.json` | 公网 HTTP 与视频 Range 验收 |
| 同目录 `verification-local.json` | 本地代理验收；不能代替公网证明 |
| 同目录 `origin-端口.log`、`tunnel-端口.log`、`watch.log` | 网页、隧道、自动恢复日志 |
| `26_q1/self_forcing_plus_infi/.tunnel_url_端口` | 原工作流可读取的最新临时入口 |

## 验收与交付

```bash
# 新主机入口的只读状态查询。
bash "/aigc/avatar/houyi/vscode_h200/targets/$(hostname -s)/start_all.sh" status

# 需要复核或诊断时单独执行；不必无原因重复已通过的全量检查。
python3 /aigc/avatar/houyi/vscode_h200/verify_migrated_web.py --host "$(hostname)"
# --local 仅验证本地代理，明确与公网结果区分。
```

完成条件：

- 实际目标主机正确，Tunnel 名称及注册 ID 保持原值，状态为 `Connected`；用户从原入口重连后能看到原工作区。
- 原 CODEX_HOME 登录有效、历史可读；在用户需要的原会话续聊，不创建无关历史。
- 微信和飞书各一个真实本机服务，凭据仍绑定且新鲜 health 为 `connected`。进程 argv 可是相对路径，应结合 `/proc/PID/cwd` 判断。真实消息往返需用户发消息或本次已授权的消息测试，不能仅凭进程存在声称验证通过。
- 所有登记网页本地服务及隧道就绪，公网页面返回 HTTP 200；代表视频请求 `Range: bytes=0-1023` 返回 HTTP 206、Content-Range、Accept-Ranges: bytes。保留媒体、数据库和标注内容。
- 现有验收可用但不是未来固定指标：2026-10-19，f224 节点曾通过 25/25 公网页面、82/82 视频 Range；以后报告实际总数及失败项。
- 交付新页面链接、映射文件、目标主机、各组件验收状态及真实未完成项。临时域名变化可以接受，但不可把隧道打印 URL 当成公网已成功。

## 常见故障的处理顺序

| 现象 | 处理 |
|---|---|
| 原入口报“请在 f224 上运行” | 为真实主机生成专用入口，不覆盖工作中的 f224 脚本 |
| 共享配置存在却想整包恢复 VS Code | 先检查 VSCODE_CLI_DATA_DIR 和 CODEX_HOME；身份恢复不依赖 6 GB 归档解压 |
| GitHub 未登录 / 无法解密 token | 原名称和 ID 保留，按需完成一次设备授权；不创建新注册 |
| 会话或桥接锁占用 | 用 `/proc/locks`、FD/fdinfo、启动时间及 CODEX_HOME 证明持有者；不删锁，不按过期 PID 误杀 |
| 新机没有 Conda 环境 / 原解释器找不到 | 验证共享解释器及 `.venv` 软链接，再补缺失库或修复真实路径；不重建整个训练环境 |
| Shell 默认环境缺失 | 查 `sync_houyi_shell.py` 及 `/root/.config/houyi/interactive.sh`；打开新交互终端验证 |
| 启动退出 141 | 检查 pipefail 下的早退管道；完整捕获 nvidia-smi 输出再匹配，不用 head/grep -q 截断生产者 |
| 公网 530 / NXDOMAIN | 分别查本地 origin、代理、隧道注册、公共 DNS 和公网验收；保留已启动服务，由后台重试，不能标完成 |
| 页面能打开但视频失效 | 查历史 URL 映射、extra-media-registry.json 和 Range；不只替换页面主域名 |
| 网络 / 权限 / 凭据问题持续失败 | 保留日志和部分成果，说明具体阻碍；不要反复重建账号、注册或无限轮换域名 |
