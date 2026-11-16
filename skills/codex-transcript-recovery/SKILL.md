---
name: "codex-transcript-recovery"
description: "Recover a prior Codex discussion when the VS Code/sidebar history is incomplete, especially for a concrete topic such as VBench Long; search user messages before treating JSONL hits as evidence."
metadata:
  source-snapshot: "2026-11-16"
  legacy-argument-hint: "[topic keywords]"
  legacy-disable-model-invocation: "false"
  legacy-user-invocable: "false"
  legacy-allowed-tools: "[\"Bash\"]"
---

# Codex transcript recovery

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


## When to use

Use for requests like “找回之前我们的对话”, missing Codex/VS Code history, or topic recovery from local backend records. Do not use it to repair the extension UI or to claim a topic was found merely because a command appeared in tool output.

## Inputs / context to gather

1. Record the exact topic words from `$ARGUMENTS`, including spelling variants.
2. Confirm the effective Codex Home from the running client, explicit `CODEX_HOME`, or its default `~/.codex`; the old server path is only a historical locator.
3. Search `sessions/` and `archived_sessions/` only inside the confirmed Home. Expand to another home only when the user names or authorizes that source. This export intentionally includes no historical conversations.

## Procedure

1. Query `state_5.sqlite` by title/metadata if useful; use Python's `sqlite3` module if no sqlite CLI is installed.
2. Extract only user-message text from rollout JSONL, then filter it. For example:
   ```bash
   find <sessions> -type f -name 'rollout-*.jsonl' -exec jq -r 'select(.type == "response_item" and .payload.type == "message" and .payload.role == "user") | [input_filename, .timestamp, ([.payload.content[]? | .text // empty] | join(" "))] | @tsv' {} + | rg -i '<topic-pattern>'
   ```
3. Inspect the dated candidate's surrounding user messages before reporting it as a recovered discussion.
4. Separate confirmed user discussion, supporting tool evidence, and incidental strings in process scans/paper text.
5. Report the transcript path, date, and confidence. If no user-context match exists, say the topic was not conclusively recovered.

## Efficiency plan

1. Confirm the Codex Home before broad searches.
2. Use `jq` user-message extraction first; do not start with raw `rg` over all JSONL.
3. Stop after the relevant original context is confirmed, or after candidate user messages establish that no definitive topic thread was found.

## Pitfalls and fixes

- Symptom: output is huge or truncated.
  - Likely cause: raw JSONL grep includes tool outputs.
  - Fix: filter `payload.role == "user"` with `jq` first.
- Symptom: a matching command is mistaken for a conversation.
  - Likely cause: the match is incidental tool/process output.
  - Fix: require surrounding user-message context before claiming recovery.
- Symptom: expected project paths do not exist.
  - Likely cause: an assumed rather than effective Codex Home.
  - Fix: locate the actual `.codex` root before continuing.

## Verification checklist

- Effective Codex Home and all applicable transcript roots were checked.
- Search results were based on user-message extraction.
- Reported thread/topic has direct user-context evidence.
- Incidental tool-output hits are labeled as non-confirmatory.
