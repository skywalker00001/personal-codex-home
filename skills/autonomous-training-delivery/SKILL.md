---
name: "autonomous-training-delivery"
description: "Use when a user delegates a model training, inference, evaluation, or training-debug task and expects Codex to own the full workflow end to end: infer the goal from context, inspect the repo and environment, choose or build launchers, prepare configs/data, run smoke tests, launch or stage training, monitor/debug, run inference tests, preserve artifacts, self-audit correctness against the user's intent, and deliver evidence without asking for every intermediate step."
metadata:
  source-snapshot: "2026-11-16"
---

# Autonomous Training Delivery

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


Use this skill when the user wants Codex to take a training-related task from assignment to verified handoff with minimal intermediate prompting.

The core contract: own the middle. The user should not have to tell Codex to inspect the repo, find the launcher, check the data, run smoke, fix import/env issues, monitor logs, run inference, or collect the final evidence. Do those steps unless there is a real blocker.

For hard deliveries, also own the first review pass. Treat the user's later
questions and corrections as the shape of a future internal reviewer: before
handoff, ask the questions a careful user would ask about correctness,
provenance, hidden config drift, and whether the artifact actually satisfies the
original request.

## Operating Posture

- Act from the workspace, not from memory alone. Read the actual code, configs, launchers, logs, and artifacts.
- Prefer concrete progress over plans. Plans are useful only when the task is broad or risky; after that, execute.
- Ask questions only when the answer cannot be discovered locally and a wrong assumption would waste large resources, destroy artifacts, or invalidate the experiment.
- Keep user updates short and evidence-based while working.
- Preserve unrelated user changes. Check `git status --short` before editing.
- Do not claim success from intent. Success requires logs, processes, checkpoints, generated outputs, metrics, or other artifacts.
- Keep intent, runtime truth, and artifact truth separate. The requested path,
  the config value, the runtime log, and the produced artifact can disagree; when
  correctness matters, inspect all of them.
- When comparing variants, isolate one factor at a time. If weights, prompts,
  scheduler, data, seeds, or runtime overrides all change together, do not treat
  the result as diagnostic.
- If the user gives a cadence or milestone, keep monitoring until that exact condition is reached or a concrete blocker appears.
- Match the user's language in the final report when practical.

## Autonomy Boundary

Do without asking again:

- Inspect repos, docs, configs, shell scripts, Python entrypoints, logs, process trees, GPU state, and data metadata.
- Patch code or scripts needed for the assigned task, then run syntax/static checks.
- Create or update experiment configs, launchers, smoke scripts, validation scripts, and markdown runbooks.
- Build filtered/sampled data manifests when the criteria are inferable from the request.
- Run non-destructive smoke tests, dry-runs, imports, small validation jobs, and short training sanity checks.
- Monitor launched jobs and debug startup failures.
- Run inference/evaluation from checkpoints produced by the task.
- Save final artifacts and report their exact paths.

Proceed when the user has already assigned the outcome:

- If the user says to start, launch, train, test, debug, or deliver results, treat that as permission to perform the required intermediate steps.
- If a formal training run is the requested deliverable, do not stop after smoke unless the user explicitly asked to stop there.
- If the user says "before formal training, stop" or similar, stop at that boundary and report readiness.

Ask or pause only for:

- Destructive cleanup of unknown processes or user artifacts.
- Overwriting or deleting checkpoints, datasets, model roots, or logs.
- Launching a large/expensive job when the user only asked for a plan, comparison, or feasibility check.
- Missing credentials, private data access, or unavailable hardware that cannot be worked around.
- Ambiguous success criteria that cannot be inferred from context.

## Houyi LongCat B200 Training Defaults

For LongCat / LongCat-Causal-Forcing training on Houyi B200 machines, default to
the proven stable stack unless the user explicitly asks for a precision or
communication ablation:

- Use BF16 training with FA4 attention by default.
- Use `/aigc/avatar/houyi/venvs/multitalk_b200_fa4` as the default B200
  LongCat training environment.
- For multi-node B200 training, enable IB/GDRDMA by default: keep
  `NCCL_IB_DISABLE=0`, set `NCCL_IB_HCA=mlx5_0,mlx5_1,mlx5_2,mlx5_3,mlx5_4,mlx5_5,mlx5_6,mlx5_7`,
  set `NCCL_SOCKET_IFNAME=eth0`, `GLOO_SOCKET_IFNAME=eth0`, and
  `NCCL_CROSS_NIC=1`, and leave `NCCL_NET` unset unless the local launcher
  requires otherwise.
- For single-node 8-GPU B200 training, keep BF16 + FA4; IB is only a
  multi-node communication requirement.
- Keep `gradient_checkpointing: true` for the real LongCat training configs
  unless the user explicitly asks for a diagnostic that changes memory behavior.
- Do not choose FP8/FP4/TransformerEngine as the default training stack. Treat
  FP8/FP4/TE as explicit experiments only, with a one-variable benchmark and a
  precision-risk note. The 2026-07-30 LongCat B200 16-GPU real-training probe
  with FP8 + FA4 + IB + `gradient_checkpointing: true` reached only a small
  speedup over BF16 + FA4 + IB (`100.159949s/step` vs `101.760230s/step` for
  step 5-10), so it should not be promoted as a default. See
  `/aigc/avatar/houyi/26_q3/LongCat-Causal-Forcing-AR-Stage1/docs/longcat_b200_fa4_ib_fp8_benchmark_20260730.md`.

## End-To-End Workflow

### 1. Capture The Contract

Extract these from the request and open files:

- Goal: train, fine-tune, distill, resume, evaluate, export, or debug.
- Model/checkpoint inputs and expected output format.
- Negative requirements and invariants: weights that must not be loaded, modules
  that must stay frozen or active, prompts/inputs that must stay identical,
  save cadence, output layout, or comparison variables that must not drift.
- Dataset paths and filtering rules.
- Hardware target: local, pod names, GPU count, environment, ports, tmux session.
- Training framework and launcher family.
- Stop boundary: plan only, smoke only, dry-run only, start training, monitor to step N, or deliver inference results.
- Success evidence: loss, checkpoint, eval metric, generated video/image/audio, exact tensor/key parity, or deployable model root.
- Review evidence the user will need to accept the result: URLs, media metadata,
  load-order logs, key counts, before/after row counts, or a comparison against a
  known-good baseline.

If details are missing, infer from nearby configs and prior experiment patterns before asking.

### 2. Build The Map

Find the actual execution path:

- Start from user-mentioned files, then inspect neighboring configs and launchers.
- Trace shell wrappers to the real Python training/inference entrypoint.
- Identify which arguments are hardcoded, inherited from environment variables, or overridden by CLI.
- Trace loader order and override precedence for every model component that can
  affect semantics, such as base weights, adapters, partial checkpoints,
  scheduler configs, prompts, reference media, or postprocessing.
- Locate logs, output dirs, checkpoints, and validation outputs before launching.
- Check whether there is an existing runbook or skill for this repo/task.

For distributed runs, determine:

- Intended world size, pod list, rank mapping, main IP/port, launcher backend.
- Which process command uniquely identifies the run.
- How to stop and verify cleanup.

### 3. Verify Inputs

Before training, verify the ingredients:

- Check model/checkpoint paths exist and match the expected layout.
- For multi-component models, build a provenance table before launch:
  expected source, actual config source, runtime-loaded source, key/tensor count
  when available, and whether any later component overwrites an earlier one.
- Check data manifests exist, row counts are plausible, and required columns are present.
- For media training, sample real files and verify fps, frames, duration, resolution/aspect, and decode path.
- For conditional generation, verify the actual condition artifacts: prompts,
  audio, reference images, masks, tail frames, labels, embeddings, or metadata
  keys. Do not assume a dataset column or path exists because a script name
  implies it.
- Check environment binaries, Python env, CUDA device type, package imports, and attention/kernel compatibility.
- For media inference, verify `ffmpeg` from the exact non-interactive launch
  environment before spending GPU time. New pods may contain `ffmpeg` inside a
  conda env while `command -v ffmpeg` fails in the tmux/launcher PATH, and some
  shell launchers validate `ffmpeg` before `conda activate`. Prefer launching
  with `PATH=/path/to/env/bin:$PATH` or a repo-local env fix, then verify
  `command -v ffmpeg` and `ffmpeg -version` in the same pod/session.
- Check ports, tmux sessions, and output directories for conflicts.

When filtering data, save the filtered manifest or the exact command/script that produced it, and report the before/after counts.

### 4. Prepare The Experiment

Use existing repo conventions:

- Clone a nearby experiment skeleton when available.
- Keep only intentional deltas: model path, data path, output path, ports, ranks, seed, train length, validation settings.
- Remove stale names, wandb labels, output dirs, ports, and tmux targets.
- Prefer repo-local launchers or wrappers over one-off pasted commands.
- Add validation/smoke hooks into the real training path when the user's requested guarantee depends on it.
- For resume/continuation, preserve the distinction between full optimizer resume, trainable-state checkpoint load, and bake-into-base initialization.
- For baked checkpoints, make inference entrypoints explicit about what external
  modules are disabled. If a trained checkpoint should contain a component, do
  not reload a stale external copy at inference unless the task explicitly asks
  for that ablation.

After edits:

- Run `bash -n` for shell scripts.
- Run Python syntax checks or targeted imports for changed Python files.
- Grep the new experiment for stale source-experiment names and old paths.
- Grep configs/scripts for stale weights, prompts, ports, output roots, and
  hidden defaults that would confound the intended experiment.

### 5. Smoke Before Spending

Run the cheapest checks that can catch expensive failures:

- Import and environment smoke.
- For video/audio generation, smoke the postprocessing binaries too:
  `ffmpeg`/`ffprobe` visibility, audio mux command, and output-directory write
  permissions. Do not infer media postprocessing health from model load success
  alone.
- Dataset decode/sample smoke.
- Model load or checkpoint-key smoke.
- Prompt/input/condition smoke for generation tasks, including generated
  schedules or runtime config files.
- One-batch or tiny-step training smoke where feasible.
- Validation/inference smoke with a small prompt/input set.
- Distributed dry-run that prints commands, ranks, and log paths without launching.

A smoke pass is not enough to declare the training delivered. It is a gate before the real run or a stated stop boundary.

### 6. Launch And Monitor

When launching:

- Start from the intended tmux/session/launcher so the run survives the shell.
- Capture the exact launch command, working directory, environment overrides, log root, output dir, and run name.
- Immediately verify processes and GPUs on every relevant node/pod.
- Tail the authoritative run log, not generic terminal output.

Monitoring evidence should include:

- GPU count and node/pod count.
- Matching `accelerate`, `torchrun`, `mpirun`, or training-entrypoint processes.
- Latest log line showing initialization, loss, `Steps:`, eval metric, or checkpoint save.
- Latest checkpoint on disk and whether it matches the live step.
- Any warnings that affect correctness.

For slow startup, do not call it stalled until checking process count, model loading progress, distributed init, and recent log movement.

### 7. Debug Without Waiting For Permission

If startup fails:

- Read the first traceback and the launcher log, then patch the root cause.
- Prefer the real failing code path over an external wrapper workaround.
- Re-run the smallest failing command first.
- If a media run fails at mux/postprocess with `ffmpeg not found`, treat it as
  an environment PATH bug, not a model/checkpoint bug. Fix the PATH in the
  launcher/tmux environment and rerun only the failed mode or checkpoint when
  possible.
- When rerunning only a failed mode/checkpoint, pass the same experiment-scoped
  variables explicitly (`EXP_DIR`, `CONFIG_PATH`, `EXPORT_ROOT`,
  `OUTPUT_ROOT_BASE`, mode flags). Wrapper defaults can silently fall back to a
  neighboring experiment and produce a misleading export or no output.
- Keep a short loop: patch, syntax check, smoke, relaunch.
- If a dependency/env issue is local to the requested environment and install/fix is safe, fix it and verify.
- If a run dies after partial progress, preserve logs before relaunching.

Do not keep relaunching blindly. If the same class of failure repeats, reduce to a targeted reproducer.

### 8. Self-Audit Before Handoff

Before handing a result to the user, pause for an internal review. The goal is
not to be pessimistic; it is to catch the same issues a sharp user would catch
after looking at the artifact.

Ask:

- Does the delivered artifact answer the original request, including negative
  requirements, hardware/env constraints, and output format?
- Can I prove the runtime used the weights/configs/inputs I claim it used?
- Did training and inference use the same conceptual model, or did inference add
  or overwrite components that training did not have?
- Did only the intended variable change between comparisons?
- If the output looks wrong, have I separated likely causes: data, prompt/input,
  merge/export, inference runtime, training instability, or incompatible
  checkpoint lineage?
- Is there a known-good baseline I can run through the same path to distinguish
  a bad model from a bad inference script?
- Would a reviewer be able to inspect the logs, commands, configs, paths, URLs,
  and metrics without asking me for missing context?

If the answer is no, iterate once more: inspect, patch, rerun the smallest useful
test, and update the evidence. Do not hand off a result simply because a command
exited successfully.

### 9. Evaluate And Infer

After a checkpoint exists:

- Run the repo's intended validation or inference path.
- Use representative prompts/inputs that cover the requested modes, resolutions, chunks, fps, or conditioning.
- Confirm outputs are actually written and readable.
- For media tasks, verify frame count, fps, duration, audio alignment, and visible quality signals relevant to the request.
- Compare against baseline only when it isolates the intended variable.
- When results look suspicious, run a known-good checkpoint or input through the
  same inference/evaluation path before concluding the new training failed.
- Save outputs under a traceable eval directory named by checkpoint/run.

### 10. Package The Handoff

Final report should be short but evidence-rich:

- What was changed or created, with file paths.
- What was launched or intentionally not launched.
- Current training state: alive/dead, GPU count, latest step/loss, latest checkpoint.
- Test/inference results: output paths, metrics, media properties, and any residual risks.
- Provenance summary: expected vs actual loaded components and any intentionally
  disabled external modules.
- Exact blockers if unfinished, plus the next command or decision needed.
- When handing off video results, write each item as `主题：直接 URL`, with the
  full browser-openable URL visible as plain text (for example,
  `滑雪摔倒：https://example.com/result.mp4`). Do not write `主题：视频`, do not
  use `视频` as the hyperlink label, and do not hide the URL behind other link
  text.
- When publishing or extending an experiment-comparison web dashboard, preserve
  all previously accepted result families and views, especially diagnostic or
  DFD results; adding a new experiment series must not silently replace or hide
  them. Keep experiments that answer the same research question in one Block
  unless the user asks for separate navigation. Select no more than three
  experiment results by default, and keep each selected video large enough for
  visual review: use three large columns on desktop, two on tablet, and one on
  mobile. Additional results may remain manually selectable. Before publishing,
  verify the default selection count, expected experiment and diagnostic
  inventory, responsive card width, browser errors, playback, and public URL
  byte-range loading against a staging build; then re-verify the live page.
- For Houyi outputs under
  `/aigc/avatar/houyi/26_q2/Self-Forcing/outputs/houyi`, report both local
  paths and browser URLs. Do not hardcode the Cloudflare prefix: read the current
  prefix from
  `/aigc/avatar/houyi/26_q1/self_forcing_plus_infi/.tunnel_url_5106` at handoff
  time, trim whitespace, and replace the local output prefix with that URL. The
  tunnel is Cloudflare and may change between sessions.

Do not bury the important result behind a long narrative.

## Evidence Standards

Use exact artifacts:

- Config path and run script path.
- Log path and the latest meaningful lines.
- Process command matched by exact config/run name.
- GPU/process release evidence for stop requests.
- Checkpoint path and step number.
- Output media paths and basic media metadata.
- Data count before and after filtering.
- Tensor/key inventories when the question is about checkpoint loading.
- Runtime configs and generated schedules when prompts, condition media,
  inference steps, or other dynamic inputs can change the result.
- Provenance tables for multi-component systems: expected source, actual loaded
  source, overwrite behavior, and evidence.

Avoid weak statements:

- "Should be running" without process/log evidence.
- "Loaded correctly" without key/tensor/log evidence.
- "Training is fine" before first loss or requested milestone.
- "Evaluation passed" without output artifacts or metrics.
- "Only X changed" without checking prompts, data, scheduler, seed,
  checkpoint lineage, and runtime overrides.
- "The checkpoint contains X" without checking saved keys or runtime load logs.

## Common Failure Modes

- Shell wrappers hide the real Python entrypoint; trace the full path before reasoning.
- Live step and saved checkpoint step diverge; report both.
- Broad `ps` output is noisy; match the exact config, run name, or entrypoint.
- Long model initialization can look frozen; check distributed init, worker count, and model loading progress.
- A clean structural load can still be semantically wrong if the base checkpoint is wrong.
- A one-factor ablation is invalid if paths, seeds, scheduler, data, or checkpoint base also changed.
- Background helper scripts can fail silently; verify their logs/processes before relying on them.
- Temporary smoke scripts become confusing if not named and scoped clearly.
- Hidden inference defaults can silently reload old adapters, partial weights, or
  prompt schedules; inspect generated runtime configs and logs after the run.
- A bad visual or metric result may be caused by prompt/input drift or
  evaluation wiring, not only by training. Reproduce with a known-good model
  through the same path before deciding.
- Save cadence and live step can diverge; report both the latest loss step and
  latest completed checkpoint.
