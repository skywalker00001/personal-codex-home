---
name: "codex-vscode-remote-extension-activation"
description: "Safely force-update Codex in VS Code Remote SSH or diagnose a Codex Audio dependency; use when installation succeeds but activation, app-server version, or local UI-host state is unclear."
metadata:
  source-snapshot: "2026-11-16"
  legacy-argument-hint: "[extension version or activation error]"
  legacy-disable-model-invocation: "true"
  legacy-user-invocable: "false"
  legacy-allowed-tools: "[\"Bash\"]"
---

# Codex VS Code Remote extension activation

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


## When to use

Use for remote `openai.chatgpt` updates, an `openai.codex-audio` dependency error, or when VS Code Remote SSH reports an extension installed but Codex still does not activate. Do not use for writer-lock recovery or ordinary CLI upgrades.

## Inputs / context to gather

1. Confirm the target is Remote SSH and identify the local UI machine separately from the remote VS Code Server.
2. Capture registered extensions, installed extension directories, and the running app-server path before changing anything.
3. Record whether the current app-server hosts the active Codex session; warn before any action that would terminate it.
4. For Audio errors, inspect both manifests: the main extension's `extensionDependencies` and Audio's `extensionKind`.

## Procedure

1. Use the remote CLI when present:
   ```bash
   /root/.vscode/cli/servers/Stable-10c8e557c8b9f9ed0a87f61f1c9a44bde731c409/server/bin/remote-cli/code --list-extensions --show-versions
   ps -eo pid=,ppid=,args= | rg '/openai\.chatgpt-.*/codex app-server'
   ```
2. Before a force update, back up the current `/root/.vscode-server/extensions/openai.chatgpt-<version>-linux-x64` directory to the established `codex-extension-backups` location.
3. Update the remote main extension with `code --install-extension openai.chatgpt --force`; verify the registered version and `<new-extension-dir>/bin/linux-x86_64/codex --version`.
4. For a declared `openai.codex-audio` dependency, install the exact dependency version remotely. If local macOS `code` is unavailable, use:
   ```bash
   /Applications/Visual\ Studio\ Code.app/Contents/Resources/app/bin/code --install-extension openai.codex-audio@<version> --force
   ```
5. Do not treat package installation as activation. Ask the user to run `Developer: Reload Window`; after reload, recheck the remote app-server path and inspect remote `exthost*/remoteexthost.log` plus the local Extension Host/Codex activation state.
   - For Tunnel/sidebar failures, also inspect fresh `/root/.vscode-server/data/logs/<timestamp>/exthost*/openai.chatgpt/Codex.log` and require `app_start outcome=success` plus `home_visible`; require `thread_hydration outcome=success` when restoring a conversation matters. If the sidebar icon is absent, use `Codex: Open Codex Sidebar`.

## Efficiency plan

1. Read manifests first; this distinguishes a missing dependency from a UI-host placement issue.
2. Reuse one pre/post inventory for registration and app-server path instead of restarting processes speculatively.
3. Stop and report partial when reload/log/activation evidence is unavailable; do not infer success from Marketplace output.

## Pitfalls and fixes

- Symptom: `--force` reports success but app-server remains under an old `openai.chatgpt-<version>` directory.
  - Cause: installed/registered extension is not the active remote window runtime.
  - Fix: `Developer: Reload Window`, then recheck the process path; do not kill the active app-server without warning.
- Symptom: Audio is "already installed" but Codex says the dependency is disabled.
  - Cause: `openai.codex-audio` is a UI extension; remote installation does not establish local UI-host activation.
  - Fix: verify the local package and Extension Host after reload, alongside the remote package/logs.
- Symptom: the expected `Enable (Globally)` control is absent.
  - Cause: UI varies by host/profile/version.
  - Fix: do not assume that control; inspect actual extension locations, manifests, and logs.
- Symptom: Extension Host fails with `spawn .../server/node ENOENT`.
  - Cause: the remote VS Code Server's node binary is missing, not necessarily an extension-version or Webview problem.
  - Fix: verify the server path and let/trigger the Server recovery before diagnosing renderer activation; distinguish this from `renderer_ready_timeout` with files present.
- Symptom: `Webview renderer did not become ready ... renderer_ready_timeout` while server and extension files exist.
  - Cause: a Webview readiness failure, not proof that package installation failed.
  - Fix: run `Developer: Reload Window`, then inspect a new Codex.log for the successful startup markers rather than relying on an old app-server process.

## Verification checklist

- Backup exists before the remote main-extension update.
- Registered version and bundled CLI version match the intended package.
- The post-reload app-server path uses the intended extension version.
- For Audio, both local UI host and remote server were checked.
- Extension Host logs and Codex activation were checked after reload.
- For sidebar recovery, fresh Codex.log shows `app_start outcome=success` and `home_visible` (plus `thread_hydration outcome=success` when relevant).
- If any post-reload evidence is missing, result is explicitly partial.
