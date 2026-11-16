---
name: "wan-h200-sft-sop"
description: "Use when working on the Wan2.1-T2V-14B 25fps/33-frame SFT workflow in DiffSynth-Studio on H200 pods, including training-rule design, data/aspect-bucket checks, smoke tests, 64-GPU kubectl/tmux launch, monitoring, checkpoint validation, inference/AB eval, and Helios DMD teacher export planning."
metadata:
  source-snapshot: "2026-11-16"
---

# Wan H200 SFT SOP

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


Use this skill for the Wan2.1-T2V-14B SFT workflow that adapts the teacher from 16fps/81f behavior to 25fps/33f chunks before using it as the Helios DMD teacher.

This SOP is for SFT of Wan T2V, not SFT of Helios.

## Authoritative Workspace Files

Start by refreshing the current repo state and reading the latest versions of these files:

- Repo: `/aigc/avatar/houyi/26_q2/DiffSynth-Studio`
- Plan: `docs/wan_t2v_25fps_33f_sft_plan.md`
- 64-GPU node command: `examples/wanvideo/model_training/full/Wan2.1-T2V-14B_25fps_33f_h200_64gpu_node.sh`
- 64-GPU tmux launcher: `examples/wanvideo/model_training/full/launch_Wan2.1-T2V-14B_25fps_33f_h200_64gpu_tmux.sh`
- 64-GPU dry-run launcher: `examples/wanvideo/model_training/full/dryrun_Wan2.1-T2V-14B_25fps_33f_h200_64gpu.sh`
- Single-node backup/smoke command: `examples/wanvideo/model_training/full/Wan2.1-T2V-14B_25fps_33f.sh`
- Validation entrypoint: `examples/wanvideo/model_training/validate_full/Wan2.1-T2V-14B_25fps_33f.py`
- AB eval launchers:
  - `examples/wanvideo/model_training/validate_full/run_Wan2.1-T2V-14B_25fps_33f_ab_eval.sh`
  - `examples/wanvideo/model_training/validate_full/run_Wan2.1-T2V-14B_25fps_33f_ab_eval_parallel.sh`

Before editing, run `git status --short` in the DiffSynth repo and preserve unrelated user changes.

## Fixed Training Rules

Keep these invariants unless the user explicitly changes the experiment:

- Base model: `/aigc/avatar/model_zoo/Wan-AI/Wan2.1-T2V-14B`
- Diffusers teacher source for later Helios use: `/aigc/avatar/model_zoo/Wan-AI/Wan2.1-T2V-14B-Diffusers`
- Data CSV: `/aigc/avatar/hanzhen/projects/data_info/merged_all_videos_portrait_head_shoulder_updated_fps25_pm005_33f.csv`
- Original merged CSV: `/aigc/avatar/hanzhen/projects/data_info/merged_all_videos_portrait_head_shoulder_updated.csv`
- Filter target: near 25fps, `33` frames per sample, `--fix_frame_rate`, `FRAME_RATE=25`, `NUM_FRAMES=33`
- Known data stats from the current plan snapshot: total rows `671105`; near-25fps rows `469108`; ratio `69.9008%`; filtered rows all have at least `33` frames.
- Output path: `/aigc/avatar/houyi/26_q2/DiffSynth-Studio/models/train/Wan2.1-T2V-14B_full_25fps_33f_aspect_bucket_h200_64gpu`
- Tokenizer: `/aigc/avatar/model_zoo/Wan-AI/Wan2.1-T2V-14B/google/umt5-xxl`
- Use aspect buckets by default:
  - `landscape:480x832`
  - `portrait:832x480`
  - `square:640x640`
  - `ASPECT_BUCKET_THRESHOLD=1.2`

Reasoning: fixed `height/width` resizing is likely to crop portrait head/shoulder data badly. Keep aspect buckets unless the user asks for a controlled no-bucket ablation.

## Pod And Environment Rules

Formal SFT should run on H200 pods, not the local B200 environment, unless the user explicitly asks for local code-only debugging.

Expected 64-card pod order and ranks:

- rank 0: `avatar-b32-master-0`
- rank 1: `avatar-b32-worker-0`
- rank 2: `avatar-b32-worker-1`
- rank 3: `avatar-b32-worker-2`
- rank 4: `avatar-a32-master-0`
- rank 5: `avatar-a32-worker-0`
- rank 6: `avatar-a32-worker-1`
- rank 7: `avatar-a32-worker-2`

Before launch, verify pods and IPs instead of trusting stale values:

```bash
/opt/kube/kubectl get pod \
  avatar-b32-master-0 avatar-b32-worker-0 avatar-b32-worker-1 avatar-b32-worker-2 \
  avatar-a32-master-0 avatar-a32-worker-0 avatar-a32-worker-1 avatar-a32-worker-2 \
  -o wide
```

Use non-interactive kubectl commands for automation:

```bash
/opt/kube/kubectl exec avatar-b32-master-0 -c main -- bash -lc 'COMMAND'
```

Use interactive `-it` only when the user wants to attach manually:

```bash
/opt/kube/kubectl exec -it avatar-b32-master-0 -c main -- bash
```

Expected environment:

- Accelerate binary: `/aigc/avatar/wang.li/miniforge3/envs/fastvideo/bin/accelerate`
- Python binary: `/aigc/avatar/wang.li/miniforge3/envs/fastvideo/bin/python`
- 64-card launch uses `NUM_MACHINES=8`, `NUM_PROCESSES=64`
- Multinode launcher must be `DEEPSPEED_MULTINODE_LAUNCHER=standard`
- `pdsh` is not the intended launcher here; it can accidentally create independent 8-GPU jobs.

Attention rule:

- On H200, expect FlashAttention 2 / fastvideo environment to work.
- On B200 or SM100+ debugging, prefer native PyTorch SDPA fallback if FlashAttention kernels do not support the device.
- Do not force B200 fallback behavior onto H200 unless debugging a real H200 kernel failure.

## Smoke Checklist

Do these before a formal run.

1. Static checks in DiffSynth repo:

```bash
bash -n examples/wanvideo/model_training/full/Wan2.1-T2V-14B_25fps_33f_h200_64gpu_node.sh
bash -n examples/wanvideo/model_training/full/launch_Wan2.1-T2V-14B_25fps_33f_h200_64gpu_tmux.sh
bash -n examples/wanvideo/model_training/full/dryrun_Wan2.1-T2V-14B_25fps_33f_h200_64gpu.sh
/aigc/avatar/wang.li/miniforge3/envs/fastvideo/bin/python -m py_compile examples/wanvideo/model_training/train.py
```

2. H200 environment smoke on `avatar-b32-master-0`:

```bash
/opt/kube/kubectl exec avatar-b32-master-0 -c main -- bash -lc '
cd /aigc/avatar/houyi/26_q2/DiffSynth-Studio &&
/aigc/avatar/wang.li/miniforge3/envs/fastvideo/bin/python - <<PY
import torch
print("cuda:", torch.cuda.is_available())
print("device:", torch.cuda.get_device_name(0))
print("capability:", torch.cuda.get_device_capability(0))
print("flash_sdp:", torch.backends.cuda.flash_sdp_enabled())
print("mem_efficient_sdp:", torch.backends.cuda.mem_efficient_sdp_enabled())
print("math_sdp:", torch.backends.cuda.math_sdp_enabled())
PY
'
```

3. Dataset smoke:

- Confirm the filtered CSV exists and has rows.
- Verify sampled videos can produce exactly `33` frames at `25fps`.
- Verify portrait, landscape, and square-ish samples map to the intended buckets.
- If errors mention unsupported extensionless video files or `variable_fps`, inspect the DiffSynth data loading path around `RouteByExtensionName`, `LoadVideo`, and OpenCV fallback before blaming the model.

4. Optional short training smoke:

- Use `avatar-b32-master-0` first.
- Use a tiny filtered CSV subset and a smoke output path.
- Stop after the first loss values and at least one tiny checkpoint.
- Report exact command, log path, latest step/loss, and checkpoint file.

Do not start formal 64-GPU training during smoke unless the user explicitly says to start it.

## 64-GPU Dry Run

Run the dry-run launcher before formal launch:

```bash
cd /aigc/avatar/houyi/26_q2/DiffSynth-Studio
bash examples/wanvideo/model_training/full/dryrun_Wan2.1-T2V-14B_25fps_33f_h200_64gpu.sh
```

Verify the printed commands include:

- `MAIN_PROCESS_IP` matching the current rank-0 pod IP.
- `MAIN_PROCESS_PORT=29577` or the user-selected free port.
- `NUM_MACHINES=8`
- `NUM_PROCESSES=64`
- `DEEPSPEED_MULTINODE_LAUNCHER=standard`
- Rank mapping exactly as listed above.
- `DATASET_METADATA_PATH` is the filtered 25fps/33f CSV.
- `USE_ASPECT_BUCKETS=1` and bucket config is present.
- `OUTPUT_PATH` is the intended H200 64-GPU output directory.

If any of these drift, patch the launcher or set environment overrides before starting.

## Formal Launch

Only start formal training when the user explicitly asks to begin.

```bash
cd /aigc/avatar/houyi/26_q2/DiffSynth-Studio
bash examples/wanvideo/model_training/full/launch_Wan2.1-T2V-14B_25fps_33f_h200_64gpu_tmux.sh start
```

Status:

```bash
bash examples/wanvideo/model_training/full/launch_Wan2.1-T2V-14B_25fps_33f_h200_64gpu_tmux.sh status
```

Stop:

```bash
bash examples/wanvideo/model_training/full/launch_Wan2.1-T2V-14B_25fps_33f_h200_64gpu_tmux.sh stop
```

Monitoring expectations:

- Before first training loss, check every 60s if the user asked you to watch it.
- After first loss, check every 30s until the run is clearly healthy.
- Report both live log step/loss and saved checkpoints; they can diverge.
- Always cite exact evidence: pod count, GPU count, process command, log path, latest `Steps:` line, checkpoint path.
- For stop requests, kill plus prove release with `ps` and GPU/process evidence.

Expected log root:

```text
/aigc/avatar/houyi/26_q2/DiffSynth-Studio/logs/wan21_t2v_14b_25fps33f_bucket_h200_64gpu/
```

## Validation And Inference

After checkpoints are available, validate with the DiffSynth validation entrypoint and AB eval launchers.

Important validation targets:

- Checkpoint can be loaded from the SFT output path.
- Generated videos have `33` frames and `25fps` metadata.
- Motion speed is visually aligned with Helios-style 25fps chunks.
- Portrait, landscape, and square buckets all render without bad crop.
- Compare base Wan output versus SFT output when doing AB eval.

Useful launchers:

```bash
cd /aigc/avatar/houyi/26_q2/DiffSynth-Studio
bash examples/wanvideo/model_training/validate_full/run_Wan2.1-T2V-14B_25fps_33f_ab_eval.sh
bash examples/wanvideo/model_training/validate_full/run_Wan2.1-T2V-14B_25fps_33f_ab_eval_parallel.sh
```

The current AB eval uses representative prompts for portrait, landscape, and square buckets. If a checkpoint path in the validation script is stale, update only that path and keep the rest of the evaluation controlled.

## Teacher Export For Helios DMD

The final artifact for Helios should be a Diffusers-style model root usable as:

```yaml
real_score_model_name_or_path: "/path/to/Wan2.1-T2V-14B-Diffusers-SFT-25fps-33f"
```

Do not hand Helios only a standalone SFT `.safetensors` file unless the Helios loader has been explicitly patched for that format.

Export plan:

1. Copy the base Diffusers teacher root:

```text
/aigc/avatar/model_zoo/Wan-AI/Wan2.1-T2V-14B-Diffusers
```

to a new root such as:

```text
/aigc/avatar/model_zoo/Wan-AI/Wan2.1-T2V-14B-Diffusers-SFT-25fps-33f
```

2. Convert or place the SFT DiT weights into the new root's `transformer/` layout.
3. Smoke-test loading with the same `from_pretrained(..., subfolder="transformer")` contract Helios uses.
4. Update the Helios DMD config only after the exported teacher loads and generates 33-frame/25fps samples.

## Common Pitfalls

- Starting formal training from a local B200 shell when the intended run is on H200 pods.
- Trusting stale `MAIN_PROCESS_IP`; always re-check `kubectl get pod -o wide`.
- Using `pdsh` or a launcher path that spawns separate 8-GPU jobs.
- Forgetting aspect buckets and accidentally cropping portrait data.
- Treating a saved checkpoint step as the live training step.
- Reporting "still running" without process and log evidence.
- Letting smoke become a formal run before the user approves the launch.
- Updating Helios `real_score_model_name_or_path` before the SFT teacher has been exported into a Diffusers-style root.
