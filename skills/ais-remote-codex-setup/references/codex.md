# 远端 Codex 与个人配置

以下命令在 SSH 的 AIS 上以目标用户执行；先 `id; hostname; echo "$HOME"`，不可在 Mac 上使用 /home/work 路径。

## CLI

先 `bash -lc 'command -v codex; codex --version; codex login status'`。缺失时从官方入口下载脚本，阅读后安装；不要要求 Node/npm 才能安装 standalone CLI。

```bash
curl -fsS https://chatgpt.com/codex/install.sh -o /tmp/codex-install.sh
# 助手检查脚本来源、下载地址、摘要校验与写入范围后执行
CODEX_NON_INTERACTIVE=1 sh /tmp/codex-install.sh
```

需要与本地一致时先查本地实际 `codex --version`，使用安装器当前支持的 `--release VERSION`。不把 2026-11-16 的 0.169.0 当作永远最新版本。新用户目录一般为 ~/.local/bin/codex；验证实际位置。

## 个人配置

默认远端仓库 `/home/work/personal-codex-home`。已有仓库先检查 remote 与未提交修改，不能 reset/覆盖；缺失才 clone。更新已有配置仓库按当前用户意图决定，不盲目拉取覆盖。

```bash
git clone https://github.com/skywalker00001/personal-codex-home.git /home/work/personal-codex-home
cd /home/work/personal-codex-home
python3 scripts/check_repo.py
bash install.sh --dry-run
bash install.sh
python3 scripts/doctor.py
```

installer 通过 ~/.agents/skills 链接技能并合并 AGENTS 受管理区块，保留现有 config.toml。模型和推理强度按当前用户偏好/可用性配置，不能仅凭目录复制声称模型授权可用。本 skill 随仓库安装到 ~/.agents/skills/ais-remote-codex-setup；已有独立 ~/.codex/skills 副本时核实来源并保留一份，不再重复链接。

未认证时 `codex login --device-auth`，显示当次 URL/验证码，由用户在浏览器完成；等待 CLI 成功后再 `codex login status`。不搬运 Mac ~/.codex/auth.json，不在 skill 里记录已用过的 device code。CLI 与远端 IDE 扩展读取同一远端用户的 Codex Home，但要检查实际设置是否自定义。

## VS Code 扩展

本地装 Remote SSH；连接后的远端也需 `openai.chatgpt`。先用远端 VS Code CLI 列出扩展，缺失才安装。若没有 `code` shell 命令，查专用 server 目录内的 `server/bin/code-server`，同时传正确 `--extensions-dir` 和 `--user-data-dir`。不要误向 Mac 安装一次便当作远端已安装。

历史成功布局（实际路径需重新发现）：

```
/home/work/.vscode-server-ais/.vscode-server/cli/servers/Stable-<commit>/server/bin/code-server
/home/work/.vscode-server-ais/.vscode-server/extensions
/home/work/.vscode-server-ais/.vscode-server/data
```

## 验收

运行 scripts/verify_codex.py：登录 shell CLI、login status、app-server 的 skills/list 和 config/read。它报告加载错误及实际模型配置；`--require-skill` 验证目标技能实际被发现并启用。`--model-test` 增加一次临时只读模型回复，验证真实调用。

官方来源：
- https://developers.openai.com/codex/cli
- https://developers.openai.com/codex/auth
- https://developers.openai.com/codex/skills

官方页面/CLI 接口有变化时以现场 help 和官方文档为准。
