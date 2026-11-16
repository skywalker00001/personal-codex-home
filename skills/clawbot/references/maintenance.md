# 架构、排障与验证

源码根目录：`/aigc/avatar/houyi/codex_wechat_bridge`。先用 `rg` 定位本次要改的路径；依赖行为以当前源码为准，不因为这是技能维护任务而改运行服务。

## 源码地图

| 文件 | 责任与排查入口 |
| --- | --- |
| `manage_feishu.sh`、`configure_feishu.py` | 飞书 tmux、配置、绑定准备 |
| `feishu_bot.py` | owner/p2p/chat 检查，入站去重，按钮回调，出站卡片与 health |
| `feishu_cards.py` | schema 2.0、等宽布局、token、菜单、过期/跨会话/跨模型保护 |
| `feishu_history.py` | 按角色分色、3 轮分页、700 字预览、全文分段、不可变快照 |
| `feishu_settings.py` | thread 级模型、推理档位、权限、管理员过滤与新建 Full access |
| `manage_wechat.sh`、`wechat_config.py`、`wechat_bot.py` | 单实例、扫码、入站轮询/语音、出站与 health |
| `weixin_transport.py`、`send_image.py` | iLink、context token、媒体、绑定用户发图 |
| `voice_understanding.py`、`voice_model_cpu.py` | 录音临时文件、SILK 解码、CPU 原音理解、转写回退 |
| `mobile_format.py` | 手机排版和完整原文切换 |
| `bridge_state.py` | Store/SQLite、inbox/outbox、会话目录、写锁探测、只读历史 |
| `chat_engine.py` | 口令、线程生命周期、steer、审批、stop_job、每轮关闭自有 RPC |
| `codex_runtime.py`、`codex_rpc.py` | 实际二进制、当前账号模型能力、JSONL RPC 子进程 |
| `session_unlock.py` | 内核锁盘点、持有者身份验证、pidfd TERM、回查与回执 |
| `restart_feishu_when_idle.py`、`restart_when_idle.py` | 等任务/队列空闲后一次性重启对应桥接 |

`Bridge -> Store -> Engine -> CodexRPC` 是两端共用的主链；入口 adapter、展示和配置分别独立。两个 `bridge.sqlite` 都含 `kv`、`inbox`、`outbox`，但 `selected`、别名、收藏、任务记录和菜单不是同一份数据。共享同一个 Codex Home 不代表两边选中了同一个 thread。

入站消息 ID 去重，微信同步游标与入站写入同一事务；出站保序、重试复用 client ID，飞书重试还复用原卡片/token。服务重启时无法确认已执行结果的请求不自动重跑，需要用户核对历史，避免重复执行有副作用的任务。服务端最终去重仍取决于平台，不能承诺网络故障绝不会重复显示。

## 只读诊断

```bash
cd /aigc/avatar/houyi/codex_wechat_bridge
bash manage_feishu.sh status
bash manage_wechat.sh status
```

status 不回显 Secret/token。继续检查 PID 是否真实对应服务、health 更新时间/last_poll、日志中的明确错误；日志可能带用户内容或秘密，摘取必要诊断并脱敏，不把整个日志/配置发到聊天或 Git。

队列只读查询示例，按故障入口选其一，不写数据库：

```python
import sqlite3
from pathlib import Path

state_path = Path('/aigc/avatar/houyi/.codex-feishu-bridge-state')
with sqlite3.connect((state_path / 'bridge.sqlite').as_uri() + '?mode=ro', uri=True) as db:
    print('inbox', db.execute('SELECT state,count(*) FROM inbox GROUP BY state').fetchall())
    print('unsent', db.execute('SELECT count(*) FROM outbox WHERE sent IS NULL').fetchone()[0])
```

微信使用其唯一状态目录。需要看任务时读取 `kv.tasks` 的状态并结合实际工作线程/进程，不仅依赖持久化记录。诊断的目标是区分身份、通道、队列、Codex 提供商/模型、会话写锁和展示层。

| 现象 | 优先核对 |
| --- | --- |
| 文字可收、按钮无效 | card.action.trigger 订阅、长连接、发布版本、owner/chat、token 过期或旧目标 |
| configured 但未 bound | 配对未完成；有效配置不重新生成覆盖 |
| 微信 waiting_binding / login_expired | 原凭据存在与服务端错误；实际失效才扫码，不清空 DB |
| connected 但没有回复 | inbox/outbox、任务/pending 审批、Codex 错误、微信 context token；不先怪网络 |
| 老模型不支持当前 ChatGPT 账号 | config/read、model/list 与提供商；保留原历史，使用兼容模型或明确分支 |
| 只显示空历史/旧片段 | history_mode、thread/turns/list 分页和原生消息索引/前序片段是否完整，不只检查 JSONL 文件存在 |
| 卡片主题不对 | aliases/name/title/preview 优先级，首条消息命名和 thread/name/set；不批量覆盖原历史标题 |
| 原音失败 | .venv_audio、权重、SILK 解码和 CPU 库；确认回退转写并报告真实来源 |
| 切换后按钮改了另一会话 | target/thread/model 校验和持久化 token，不能接收客户端原始命令 |

## 停止与写锁

`stop_job` 验证 thread 及预期 started，设置 cancel；有 turn ID 则 `turn/interrupt`，尚在启动阶段则阻止后续 turn/start。结束时关闭该任务自己的 RPC 子进程释放自有锁。不要以关闭整个服务或全局解锁代替这个流程。

安全分支使用 `thread/fork`，保留原线程。查看历史使用只读分页，不触发 resume 抢锁。同一 app-server 可以持有多个线程的锁；TERM 它会影响这些线程，可能包括当前桌面聊天。

锁审计命令默认只读：

```bash
cd /aigc/avatar/houyi/codex_wechat_bridge
.venv_feishu/bin/python session_unlock.py \
  --home /aigc/avatar/houyi/restart_commands_h200/migrate_materials/.codex
```

`--receipt` 会把该 CLI 变成**实际解锁操作**，不能当作普通“输出报告”选项使用。仅在用户要求全局解锁的范围内执行；先说明会断开占用的 Codex 连接。已明确获授权无需反复确认，但不能由普通修复/文档请求推导授权。

实现从 `/proc/locks` 与锁 FD 核实持有者，再确认可执行文件、命令行、同一 CODEX_HOME、PID 启动时间；通过 pidfd 发 TERM，防 PID 复用。未知持有者不发送信号。诊断需要时可用 `lslocks`、`fuser`、`/proc/PID/fdinfo` 补证 `FLOCK ADVISORY WRITE`。

不删除 `.lock`、会话或数据库，不向训练进程发信号；普通占用首先考虑等待或分支。全局解锁完成要看回执 `status=complete`、`all_locks_released=true` 及 after 中所有锁未占用，并确认已发送 TERM 的进程实际退出；`partial/failed/busy` 均不是成功。重新打开线程会重新持锁。

## 修改与重启

修改展示优先限于卡片/历史/格式层；改 Engine、Store、RPC、锁逻辑时同时检查两端。旧 callback 要在新代码后仍能安全拒绝；不以清空队列、数据库、回调 token 或会话锁来让测试“干净”。

已获准部署变更时，先检查活跃任务、pending 审批、inbox pending/processing 和 outbox 未发送记录。需要自动等空闲可复用相应 `restart_*_when_idle.py`；它们会实际启停服务，当前最多等约两小时，超时只记录延期，不强杀任务。运行前核对脚本的 ACTIVE 状态集合与当前任务状态是否覆盖完整，并复核 PID 身份/启动时间，不能把脚本当作绝对保证。

```bash
# 仅在确需部署且已确认对应入口空闲时运行相应一条。
cd /aigc/avatar/houyi/codex_wechat_bridge
.venv_feishu/bin/python restart_feishu_when_idle.py
.venv/bin/python restart_when_idle.py
```

管理脚本 stop 仅请求对应 tmux 服务退出。核实旧 PID 实际退出再 start；共享盘跨主机故障恢复需迁移技能的交接证据和单写者预检。不要 pkill codex、删除锁或重启 VS Code Tunnel 来部署一处卡片修改。

## 按变更选择验证

只编写本技能时运行技能结构校验、链接与源码对应检查即可，不需要启动真实服务或执行全部机器人测试。

后续改机器人时，现有模拟测试入口：

```bash
cd /aigc/avatar/houyi/codex_wechat_bridge
.venv_feishu/bin/python -m pytest -q test_feishu.py test_feishu_history.py
.venv/bin/python -m pytest -q test_wechat.py test_wechat_single_instance.py
.venv_feishu/bin/python -m pytest -q test_session_unlock.py
```

选择与修改相关的文件/用例；共用代码变更才扩大到两端。解锁测试只用临时目录和测试子进程，不能操作真实线程。卡片预览用 tmp Store、隔离/模拟 Engine 和 Cards.render，检查 schema、分组/行列、标签、目标 token、全文入口及旧卡片拒绝；不要用生产 Store 生成一堆测试菜单。

关键验收：绑定和群聊过滤、入站去重/持久化、出站重试保序、稳定会话选择、占用不接管、模型/权限传入、首条消息命名、停止后可接新任务、延迟停止不误伤后续任务、历史角色/顺序/翻页/全文、单微信约束。

真实消息测试只在已获授权的范围内进行，固定发给已绑定用户；若没有授权发送，则交付模拟验证并请用户自行点击/发消息验收。需要模型回合时用简单只读任务和随机校验词，验证原 thread ID 的上下文续接、最终回信、队列投递及自有锁释放。不要启动训练或给第三方联系人发消息作为连通性检查。

交付注明哪层已验证：源码/模拟测试、服务进程、最新连接、原生历史可读、实际模型回合、飞书/微信客户端收信。配置和服务日志留在私有目录，技能和 Git 只保存不含秘密的操作说明。
