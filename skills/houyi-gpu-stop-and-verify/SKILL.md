---
name: "houyi-gpu-stop-and-verify"
description: "Stop a named training, inference, ODE, or service workload on Houyi pods and verify scoped GPU cleanup when the user says “停了吧”, “清空显存”, or “确保没有任何显存程序”."
metadata:
  source-snapshot: "2026-11-16"
  legacy-argument-hint: "[run_name_or_logdir] [pod_scope]"
  legacy-disable-model-invocation: "true"
  legacy-user-invocable: "false"
  legacy-allowed-tools: "[\"Bash\"]"
---

# Houyi GPU stop and verify

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


Use this when the user wants a specific training, inference, ODE producer, or service stopped and cares about verified GPU cleanup, including B200 pod families such as A16/B16/C16/I8/J16/K16.

Do not use this for cluster-wide cleanup, speculative pod hunting, or repo/code-reading questions. Search `MEMORY.md` instead when the task is about stage-1 causal AR, prompt scheduling, or dataset layout.

## Inputs / context to gather

1. Resolve the exact target run:
   - run name
   - logdir
   - config path
   - checkpoint prefix if the user will care what was preserved
   - full command/config/output path, and associated tmux session when present
2. Resolve the exact pods to touch.
   - Prefer the named pod family only, such as `avatar-a16-*` or `avatar-e16-*`.
   - If the user explicitly asks for broader cleanup, list that scope clearly before acting.
3. Read:
   - latest relevant log tail
   - current `nvidia-smi --query-compute-apps=pid,process_name,used_memory`
   - current training-process grep for the exact run/logdir string
   - `/proc/<pid>/cmdline` and `/proc/<pid>/exe` for each candidate; require a Python executable as well as the exact target path
   - zombie count when the user asks to clear zombies; keep it separate from live GPU-process evidence
4. On B16, run remote inspection with `env -u BASH_ENV -u ENV bash --noprofile --norc` so injected shell startup does not create misleading matches.

## Procedure

1. Confirm scope before killing anything.
   - If the user named one run or one pod family, do not touch sibling jobs outside that scope.
2. Capture the pre-stop state.
   - Save the exact run dir or logdir.
   - Note the newest checkpoint already present if it matters.
   - Record the current compute-app PIDs per target pod.
3. Confirm every candidate before signaling.
   - Read `/proc/<pid>/cmdline` for each candidate and require the exact project/config/output identifier across the process tree.
   - Preserve an unrelated CUDA service even when it shares a named pod family.
4. Stop GPU users by validated PID, not by broad pattern.
   - Run `nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader`.
   - Send `kill -TERM` to those PIDs on the target pods.
5. Re-check and escalate only if needed.
   - Re-run the compute-app query.
   - Send `kill -KILL` only to survivors that are still present after a reasonable wait.
6. Close only the matching tmux session after its target processes have been identified, then verify the stop from three angles.
   - `nvidia-smi --query-compute-apps=...` shows no remaining compute apps.
   - `nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader` shows the post-stop state.
   - Process greps show no remaining `train_longcat`, `torchrun`, `accelerate`, or exact-run processes in scope.
7. Check the log tail for expected stop signals.
   - Good markers include `Sending process ... closing signal SIGTERM` and `Signal 15 (SIGTERM) received`.
8. If zombie cleanup is authorized, dry-run the project cleanup script first and confirm the zombies have no live parents. Use its ordinary `--all` reaping path; do not use a parent-kill escalation unless explicitly justified. Recheck zombie count after the cleanup.
9. Report the result in the user’s preferred shape.
   - what was stopped
   - what checkpoint was preserved
   - which pods are clean
   - whether any residual MiB remains with no running compute apps

## Efficiency plan

1. Jump straight to known pod names; do not start with forbidden or noisy namespace-wide listing.
2. Grep the exact run or logdir string before broad `ps` scans.
3. Prefer one compute-app sweep per pod family over repeated ad hoc `pgrep -f` loops.
4. Stop once all three verification signals agree:
   - no compute apps
   - no target training processes
   - expected SIGTERM evidence or equivalent clean-stop markers

## Pitfalls and fixes

- Symptom: the cleanup shell dies with exit `143` before verification completes.
  - Likely cause: a broad `pgrep -f` matched the running cleanup command itself.
  - Fix: use GPU compute-app PID lists from `nvidia-smi --query-compute-apps` instead of self-matching process patterns.

- Symptom: the user asked to stop one run, but sibling jobs disappeared too.
  - Likely cause: the stop pattern was broader than the named run or pod scope.
  - Fix: resolve exact pods and exact run identifiers first; act only inside that boundary unless the user explicitly expands scope.

- Symptom: a generic `python` or `torchrun` match selects unrelated descendants.
  - Likely cause: matching process names rather than the full command/config/output path; an inspection `kubectl exec` can match itself.
  - Fix: inspect `/proc/<pid>/cmdline` and `/proc/<pid>/exe`; require a Python executable and exact target identifiers before sending a signal.

- Symptom: B16 inspection returns confusing launcher/process matches.
  - Likely cause: `BASH_ENV` or `ENV` injected shell startup behavior.
  - Fix: use `env -u BASH_ENV -u ENV bash --noprofile --norc` for the remote command.

- Symptom: a zombie cleanup wrapper rejects `--remote-arg=--all`.
  - Likely cause: the pool wrapper expects separate arguments.
  - Fix: pass `--remote-arg --all`, then verify the post-run zombie count; do not trust malformed or incorrectly quoted remote scan output.

- Symptom: rank-0 exited but distributed workers or CPU-only `torchrun` controllers remain.
  - Likely cause: SIGTERM did not propagate to every node/process tree.
  - Fix: inspect every target pod for the exact config/run path, CUDA compute apps, and residual `torchrun`; after a bounded wait, use KILL only for confirmed survivors.

- Symptom: a `<defunct>` process remains after a validated stop.
  - Likely cause: parent reaping residue, not an active GPU workload.
  - Fix: report it separately; determine cleanup from CUDA apps, `pmon`, GPU memory/utilization, and resource use.

- Symptom: `nvidia-smi` still shows `20 MiB` or `130 MiB` after all processes are gone.
  - Likely cause: H200 driver residue remains even though no compute apps survive.
  - Fix: verify there are no listed compute apps and report the residual MiB explicitly as residue, not a live job.

- Symptom: `nvidia-smi --gpu-reset` does not clear the residue.
  - Likely cause: the node reports `Not Supported`.
  - Fix: treat that as an environment limitation and avoid promising a full hardware reset through `nvidia-smi`.

## Verification checklist

- Exact target run or logdir was identified before sending signals.
- Target pod scope was explicit and did not silently expand.
- Stop actions used compute-app PIDs, not only broad process-pattern killing.
- Every signaled PID was validated against its full command/config/output path.
- Candidate validation also checked `/proc/<pid>/exe` where self-matching is possible.
- Post-stop verification checked:
  - no remaining compute apps
  - no remaining target training processes
  - log evidence of clean signal handling
- Any preserved checkpoint boundary was reported.
- Any residual MiB with no compute apps was labeled as driver residue, not as a live process.
- If zombie cleanup was requested, pre/post zombie counts and deliberately retained workloads were reported.
