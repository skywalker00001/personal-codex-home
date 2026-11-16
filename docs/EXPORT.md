# 导出范围与来源

整理日期：2026-11-16。目标仓库在整理时为公开仓库。

## 已包含

- 原 Codex Home `skills/` 的 5 个自定义技能，保留其引用文件和配套脚本。
- 原 Codex Home `memories/skills/` 的 9 个经验技能，提升为可安装的独立技能。
- 新建 `clawbot-feishu-deploy`：完整飞书部署指南与 2026-11-13 的配套源码包。
- 新建 `personal-codex-profile`：后续迁移、安装和更新这套个人配置的做法。
- 人工筛选的协作偏好、H3/Performer 项目背景、最小配置与安装工具。

技能来源与源文件 SHA256 见 `manifests/sources.json`；仓库受管文件的完整性摘要见 `manifests/files.sha256.json`。来源清单只是溯源，不会自动去服务器读取或更新原文件。

## 兼容性处理

`memories/skills` 中旧前置字段包含其他 agent 格式的 `argument-hint`、`user-invocable`、`disable-model-invocation` 和 `Bash` 工具限制，个别 description 还有未转义冒号，直接当 YAML 加载会失败。

副本统一使用可解析的 `name`、`description`、`metadata`；旧字段以来源元数据保留，不把 `Bash` 当成 Codex 工具名称。原先 `disable-model-invocation: true` 的选择映射成 `agents/openai.yaml` 的 `allow_implicit_invocation: false`，需要时用 `$技能名` 显式调用。其余技能保留自动匹配。详见技能目录。

技能中的历史服务器路径与数值例子保留，但增加跨机器使用说明。原服务器上的 skill、Codex 配置、机器人和实验程序均不修改。

## 刻意不导出

- 登录 token、`auth.json`、SSH 私钥、GitHub 凭据、飞书绑定与 App Secret、kubeconfig。
- 原始聊天、归档、会话与日志数据库、模型缓存、临时文件、锁、插件缓存。
- 整个 `memories/`、其 Git 历史和自动注入索引。只保留筛选后的知识；不能从本仓库恢复未导出的对话。
- 服务器的项目信任记录、通知 Hook、既有 GPU 清理授权和任意其他账户的状态。
- 模型权重、数据集、虚拟环境、VS Code Tunnel 身份以及正在运行的服务。

不承诺搬迁后逐字复现旧回复；同样的技能仍会受到所选模型、工具和可访问材料影响。新机器需自行安装客户端并登录。

## 后续增加文档

先把有价值的操作步骤提炼成有明确适用范围的 `SKILL.md`；长指南放 `references/`，可分发的模板或源码包放 `assets/`，实际工具放 `scripts/`。补齐资源后运行技能校验与仓库检查，再提交。不要把整个工作目录递归复制进来。
