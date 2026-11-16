---
name: "helios-hy-exp-status-check"
description: "Check a Helios hy_exp run and answer the user's usual questions: how many GPUs, what step it reached, whether it is still training, and whether a slow start is still healthy."
metadata:
  source-snapshot: "2026-11-16"
  legacy-argument-hint: "[exp_dir_or_name]"
  legacy-disable-model-invocation: "false"
  legacy-user-invocable: "false"
  legacy-allowed-tools: "[\"Bash\"]"
---

# Helios hy_exp status check

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


Use this when the task is “多少卡/多少步/还在训练吗”, “看下当前的进度如何了”, or when a Helios run is still initializing and you need concrete status evidence instead of a vague “still running”.

Do not use this for merge/math questions about LoRA or `transformer_partial.pth`; search `MEMORY.md` for those instead.

## Inputs / context to gather

1. Resolve `$ARGUMENTS` to the experiment directory under `scripts/training/hy_exp/` if the user gave only a short name like `exp_6_5_3_2`.
2. Read:
   - `run_master.sh`
   - `run.sh`
   - latest `logs/node0_stderr_*.log`
   - latest `logs/node0_stdout_*.log` if stderr is inconclusive
3. Search process lists for the exact config path, not just `python` or `accelerate`.

## Procedure

1. Confirm intended world size from `run_master.sh` / `run.sh`.
   - Look for pod count, `NNODES`, `GPUS/NODE`, `TOTAL GPUS`, or equivalent launch args.
2. Find the latest progress marker.
   - Search the latest stderr log for `Steps:` first.
   - If no `Steps:` exists, search for startup markers like `DistributedType.DEEPSPEED`, `Num processes:`, `Pretrained LoRA`, `Pretrained Partial`, and `Loading weights:`.
3. Confirm liveness with exact process matching.
   - Search for `train_helios.py --config <exact-config-path>`.
   - Search for the matching `accelerate launch` command if relevant.
4. Check checkpoint/output evidence only as a secondary signal.
   - Report the newest `checkpoint-*` if present, but keep it separate from live-step evidence.
5. Summarize in the user’s preferred shape:
   - GPU count
   - latest step or startup milestone
   - whether the run is still alive
   - whether the run has reached first loss / stable training yet

## Efficiency plan

1. Read the experiment’s own logs before broad process scans.
2. Narrow every search to the exact experiment config path to avoid noisy `ps` output.
3. Stop once you have all three user-facing answers with evidence:
   - GPU count
   - latest step or startup milestone
   - liveness
4. If startup is slow and there is no `Steps:` line yet, do not keep searching blindly; switch to startup markers and process counts.

## Pitfalls and fixes

- Symptom: broad `ps -ef` results are noisy.
  - Likely cause: unrelated cluster jobs dominate process output.
  - Fix: grep for the exact `train_helios.py --config ...` path.

- Symptom: no `Steps:` line yet, but the user wants a progress update.
  - Likely cause: the run is still in initialization.
  - Fix: report `DistributedType.DEEPSPEED`, worker count, `Pretrained LoRA` / `Pretrained Partial`, and `Loading weights` progress as the current milestone.

- Symptom: newest checkpoint lags behind live progress.
  - Likely cause: checkpoint save interval is coarser than log updates.
  - Fix: report both separately and prefer stderr `Steps:` for the live step count.

- Symptom: startup warnings mention missing FA/xformers kernels.
  - Likely cause: environment-specific informational warnings.
  - Fix: do not call them failures unless logs also show an actual crash or stalled process exit.

## Verification checklist

- Intended GPU/world-size evidence was read from the experiment scripts.
- Latest log milestone was taken from the experiment’s own latest log files.
- Liveness was confirmed with an exact process match for the config path.
- The final answer distinguishes:
  - live step vs last saved checkpoint
  - “still initializing” vs “already reached first loss”
