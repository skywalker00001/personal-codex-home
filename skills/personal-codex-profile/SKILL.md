---
name: personal-codex-profile
description: 安装、迁移或更新本仓库的个人 Codex 配置、skills 与精选项目知识，用于新的 Mac/Linux 开发环境；不搬迁登录凭据、历史会话或整套服务器服务。
---

# 个人 Codex 配置迁移

先定位本 Git 仓库根目录，读取 `README.md` 与 `docs/MAC_SETUP.md`。全局配置是 `~/.codex/config.toml`，用户技能安装到 `~/.agents/skills`；自定义 Codex Home 以目标客户端实际环境为准。

1. 确定用户需要在 Mac 本地工作，还是本地连接服务器。`/aigc` 路径和 Linux/GPU 工具只在对应服务器执行。
2. 用 `bash install.sh --dry-run` 检查目标，再安装。已有配置保留、偏好以受管理区块合并；同名外部技能默认保留，明确要替换才使用带备份的 `--replace-skills`。
3. 在新客户端用自己的账号登录，打开新会话用 `/skills` 检查发现结果。`scripts/doctor.py` 只证明文件安装，不证明模型或平台授权可用。
4. 补充知识时提炼为可追溯的稳定流程，保留版本区别。长指南放 skill 的 `references/`，运行素材放 `assets/`，配套工具放 `scripts/`；不要全量复制原始聊天或自动记忆库。
5. 使用 `python3 scripts/check_repo.py` 检查文件摘要、引用和秘密模式；有意修改后用 `--write-manifest` 刷新清单，再重新检查。运行 `python3 -m unittest discover -s tests` 验证安装器。
6. 用户明确要求上传时才提交并推送到指定 Git；确认远端与可见性，不把发布权限推广到其他仓库。

本仓库只同步指引、配置模板、技能及筛选后的说明。登录 token、SSH 私钥、飞书绑定、数据库和集群凭据应由用户在目标环境单独配置。历史操作授权不会随技能文本自动迁移。
