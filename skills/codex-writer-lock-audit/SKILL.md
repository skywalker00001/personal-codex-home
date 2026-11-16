---
name: "codex-writer-lock-audit"
description: "Audit or release a named/all Codex writer locks without deleting state; use for requests to unlock Codex sessions or diagnose a stuck writer lock."
metadata:
  source-snapshot: "2026-11-16"
  legacy-argument-hint: "[named session or all locks]"
  legacy-disable-model-invocation: "true"
  legacy-user-invocable: "false"
  legacy-allowed-tools: "[\"Bash\"]"
---

# Codex writer-lock audit

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


## When to use

Use for a concrete request to release a Codex writer lock or audit all current writer locks. Do not use for unrelated training processes, `.coordination.lock` without a holder, or as a reason to delete lock/session/SQLite files.

## Inputs / context to gather

1. Confirm the effective Codex Home and lock directory. In this workspace it has been `/aigc/avatar/houyi/restart_commands_h200/migrate_materials/.codex/thread-writer-locks/`; do not assume `/root/.codex` is active.
2. Identify the requested session scope and explicitly ask/announce before any current app-server would be terminated, because it disconnects the current session.
3. Read only enough goal state to determine whether a candidate old session has pending work; keep training process scope separate.

## Procedure

1. Inventory every lock with `lslocks` and `fuser <lock>`; record unheld files as `holder=none`, and do not treat `.coordination.lock` as a writer session merely because it exists.
   - If a lock vanishes between directory enumeration and inspection, treat it as a normal concurrent-release race. Skip/re-enumerate it; do not report it as an unexplained failure or recreate/delete state.
2. For each actual holder, map PID to target lock FD through `/proc/<pid>/fd` and confirm `FLOCK ADVISORY WRITE` in `fdinfo`; verify PID start time, `/proc/<pid>/exe`, exact command line, and target inode before any signal. One app-server can hold multiple locks.
3. For an old, approved holder only, send `TERM`, wait for the PID to exit, then repeat the complete `lslocks`/`fuser` inventory. A concurrent Codex session can create a new lock while the audit runs.
   - If Python lacks `os.pidfd_open`, a Linux `pidfd_open`/`pidfd_send_signal` syscall fallback via `ctypes` is acceptable only after the same immediate PID start-time, executable, command-line, target-inode, and target-FD checks.
   - For one named thread, a target-scoped `thread/unsubscribe` RPC may be preferable to terminating a shared app-server, but it is not completion evidence: it has returned `unsubscribed` while the lock remained held. Do not make archive/unarchive a default release action; re-audit first and treat it as potentially disruptive.
4. If the current app-server must be released, warn that it will disconnect. A delayed helper must revalidate PID start time, executable, command line, and target FD immediately before TERM.
5. After any TERM/helper, perform the final audit: PID exited, target FD gone, and every intended lock is `holder=none`. Report partial if that final observation cannot be captured.

## Efficiency plan

1. Find the effective lock directory first; avoid searching inactive Codex homes.
2. Use `fuser` to narrow PIDs, then inspect only those PIDs' FD links rather than broad process greps.
3. Stop once all intended locks have final `holder=none` evidence, or label the result partial rather than inferring completion from a sent signal.

## Pitfalls and fixes

- Symptom: a lock file remains after a process exits.
  - Likely cause: file existence was confused with active ownership.
  - Fix: judge ownership with `fuser` and the holder's target FD; never delete the file directly.
- Symptom: `FileNotFoundError` / `ENOENT` while opening a lock selected by a prior directory scan.
  - Likely cause: Codex released the lock between enumeration and `os.open`.
  - Fix: handle the vanished path as a race, re-enumerate if needed, and base the final answer on current `lslocks`/FD evidence.
- Symptom: an all-lock release looks successful after a delayed TERM.
  - Likely cause: no post-helper recheck was captured, or a concurrent session created a new lock during the audit.
  - Fix: re-audit PID, `lslocks`, `fuser`, and all target FDs after every termination; otherwise report partial.
- Symptom: an app-server appears to own more than one session lock.
  - Likely cause: shared app-server ownership.
  - Fix: enumerate its full lock range before TERM and state the collateral session impact.
- Symptom: `thread/unsubscribe` returns success but the named lock remains.
  - Likely cause: the server retained the loaded thread during its grace period or release lifecycle.
  - Fix: recheck `lslocks`, `fuser`, `/proc/locks`, target FD, and `fdinfo`; abort a lifecycle action if the pre-action snapshot changed.
- Symptom: `AttributeError: module 'os' has no attribute 'pidfd_open'`.
  - Likely cause: the Python build does not expose the pidfd wrapper.
  - Fix: use a validated `ctypes` syscall fallback or another identity-safe method; never fall back to deleting the lock file or broad process matching.

## Verification checklist

- Effective Codex Home and writer-lock directory were confirmed.
- Every actual holder was verified by PID identity and target lock FD.
- No session, SQLite database, or lock file was deleted directly.
- Current-session disconnection risk was warned before its app-server was targeted.
- Post-TERM `fuser` evidence shows each intended lock as `holder=none`; otherwise result is partial.
