# 创建、绑定与服务部署

以下命令操作 `/aigc/avatar/houyi/codex_wechat_bridge`。已有服务仅做文档或只读诊断时，不执行创建、绑定、安装或启停命令。

## 运行环境

先验证共享 Codex Home、项目目录与 `python3`、`tmux`；Linux 实现还使用 `fcntl`、`/proc`，全局解锁依赖 pidfd。复用现成 `.venv`、`.venv_feishu` 及共享环境；仅缺失时创建。

当前整机恢复环境由以下文件提供；先确认存在，再按所需复用：

```bash
source /aigc/avatar/houyi/migration_backups/b200_to_h200_20261016T091927Z/h200_env.sh
cd /aigc/avatar/houyi/codex_wechat_bridge
```

检查 `CODEX_HOME`、`CODEX_BRIDGE_PROJECT` 和实际 `CODEX_BRIDGE_BIN`。显式指定的二进制优先；默认 `codex` 会由 `codex_runtime.resolve_binary` 查 VS Code 扩展注册表内 `openai.chatgpt` 的匹配平台程序，再回退 PATH。换机/升级后重新核对版本和 `login status`，不要假设 PATH 与当前服务相同。技能不固定任何模型名称。

确需首次安装时：

```bash
cd /aigc/avatar/houyi/codex_wechat_bridge
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements-wechat.txt
.venv/bin/python -m venv --system-site-packages .venv_feishu
.venv_feishu/bin/python -m pip install -r requirements-feishu.txt
```

`requirements-feishu.txt` 复用微信依赖并固定 `lark-oapi==1.7.4`；微信依赖为 requests、qrcode、cryptography。按仓库文件安装，不为普通配置更新整个训练环境或自动升级 SDK。最新 SDK 示例中出现的额外 API 不代表当前固定版本已实现。

## 飞书：自建应用与私聊绑定

当前采用自建应用机器人、Python SDK 长连接和卡片 schema 2.0，无需公网回调或 Cloudflare。只有出站 webhook 的群自定义机器人不满足当前双向卡片交互。

在 [飞书应用后台](https://open.feishu.cn/app) 完成：

1. 创建自建应用并启用机器人能力；已有应用则复用。公司组织的创建、权限和发布可能需要管理员操作。
2. 配置本实现所需权限：`im:message:send_as_bot`、`im:message.p2p_msg`。本人私聊不需要扩大到组织所有群消息或通讯录。
3. 在事件/回调配置选择长连接，分别配置消息事件 `im.message.receive_v1` 与卡片回调 `card.action.trigger`。二者都要核对，不把“文字能收到”视为按钮回调已接通。
4. 发布版本，使用范围先包括需要绑定的本人，按组织规则完成发布/审批。若后台要求已有长连接，先配置本机并启动，再保存订阅。

本机创建配置：

```bash
bash manage_feishu.sh configure
bash manage_feishu.sh start
bash manage_feishu.sh status
```

`configure_feishu.py` 在终端询问 App ID，以隐藏输入接收 App Secret，写入私有 `config.json`。已有配置时拒绝覆盖。不要用聊天收集 Secret，不在 shell 参数里传 Secret。

配置器生成一次性配对口令；用户在与机器人的飞书私聊中发送终端显示的 `/绑定 校验码`。配对成功保存 `owner_open_id` 并移除配对码，后续检查绑定用户和私聊 chat ID。直接私聊非文字消息、群聊和其他用户不会进入当前任务引擎。

配置器可将当时的 `CODEX_THREAD_ID` 设为初始目标；未设置时通过“会话”选择。选择占用会话不代表能接管桌面写锁，需按“历史/分支”流程处理。已绑定时不重新跑配对流程，也不清空队列或会话选择。

官方依据与更新入口：[Python SDK](https://github.com/larksuite/oapi-sdk-python)、[飞书卡片按钮](https://open.feishu.cn/document/feishu-cards/card-components/interactive-components/button)。后台名称变化时核对当前平台界面和固定 SDK 的实际实现，不自动换成另一种接入方式。

## 微信：唯一 iLink 实例

```bash
cd /aigc/avatar/houyi/codex_wechat_bridge
bash manage_wechat.sh start
bash manage_wechat.sh login
bash manage_wechat.sh status
```

仅首次绑定或确已失效时执行 `login`；有效的共享凭据直接复用。扫码流程运行在 `houyi-wx-login`，二维码文件为私有状态目录中的 `wechat-login.png`，日志为 `login.log`。由用户用自己的微信扫描、确认；二维码有效期由服务端决定，本地流程最多等待约 5 分钟。若要求验证码，只在本机私有 `verify-code` 文件中提供，程序读取后删除，不要求用户把验证码贴进聊天记录。

`credentials.json` 保存 bot token、绑定用户和 API 地址；不读取后回显。程序拒绝覆盖已有绑定；更换账号需要先处理旧绑定与服务，不能把登录重试当成换号。只接受绑定用户的单聊，不访问其个人微信好友列表。

`CODEX_WECHAT_INSTANCE` 只允许 `1`，`CODEX_WECHAT_STATE` 只能为当前唯一默认路径。管理脚本、配置辅助和 Python 服务都应保持相同约束；不要另起副本规避单实例锁。

协议维护入口：[腾讯微信插件](https://github.com/Tencent/openclaw-weixin)、[协议说明](https://github.com/Tencent/openclaw-weixin/blob/main/docs/protocol_zh_CN.md)。功能以本地 `weixin_transport.py` 已实现接口为准，不把上游未来能力写成当前已支持。

## 可选微信原音理解

已有共享环境和权重优先复用。需要补齐时才执行：

```bash
cd /aigc/avatar/houyi
npm ci --prefix codex_wechat_bridge --no-audit --no-fund
python3 -m venv --system-site-packages codex_wechat_bridge/.venv_audio
codex_wechat_bridge/.venv_audio/bin/python -m pip install -r codex_wechat_bridge/requirements-audio.txt
```

`requirements-audio.txt` 固定 `qwen-omni-utils==0.0.9`，基础环境还需 torch、transformers、音频处理库。`package-lock.json` 提供 SILK 解码器。权重默认 `/aigc/avatar/houyi/models/Qwen2.5-Omni-3B`，可用 `CODEX_VOICE_MODEL` 指定；权重缺失时先确认下载需求与可用空间，不因查看机器人状态就下载模型。

语音在 CPU 上理解，当前线程数为 12，不为了机器人占用训练 GPU。处理完成删除临时录音；失败回退微信自带转写。文本回复是当前输出方式，未接入语音回复或实时通话。

## 状态、持久化与换机

| 项目 | 飞书 | 微信 |
| --- | --- | --- |
| tmux 服务 | `houyi-feishu-codex` | `houyi-wx-codex` |
| 登录/配置 | 本机 `configure` 与飞书私聊配对 | `houyi-wx-login` 扫码 |
| 私有状态 | `.codex-feishu-bridge-state` | `.codex-wechat-bridge-state/weixin` |
| 账号配置 | `config.json` | `credentials.json` |
| 业务数据库 | 各自的 `bridge.sqlite` | 各自的 `bridge.sqlite` |
| 运行证据 | `health.json`、`service.log` | `health.json`、`service.log`、`login-status.json` |

私有目录应为 0700，配置及状态文件为 0600。各自 SQLite 中的绑定、`selected`、别名、设置、入站去重和出站重试状态需要随服务保留；Codex 原始历史在共享 Home，两者都要在才能保留全部体验。不要在 Git 中保存凭据或原始状态/日志。

tmux 独立于当前 SSH 会话，但容器或宿主重启后仍需要 `start`。当前恢复入口 `vscode_h200/start_all_pretrain_f_224_worker_3.sh` 会启动两端机器人；换节点应使用迁移技能生成对应主机入口，不绕过原脚本的主机检查。

换机前确认旧服务已停，或已得到旧 Pod 退出的实际证据，再在新机用原共享 Home 与私有状态启动；同一个微信/飞书不得在两台机器并行消费同一组队列。保留凭据，不重置绑定；本技能不要求复制 VS Code 或更名 Tunnel。
