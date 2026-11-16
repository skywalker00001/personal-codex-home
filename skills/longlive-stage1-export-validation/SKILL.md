---
name: "longlive-stage1-export-validation"
description: "Export a LongLive or LongCat stage-1 AR sharded checkpoint to a native generator directory and validate it efficiently, especially when the user wants fast T2V/I2V checkpoint verification without disturbing the active training pod."
metadata:
  source-snapshot: "2026-11-16"
  legacy-argument-hint: "[checkpoint_dir_or_step] [logdir_or_run_name]"
  legacy-disable-model-invocation: "false"
  legacy-user-invocable: "false"
  legacy-allowed-tools: "[\"Bash\"]"
---

# LongLive stage1 export and validation

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


Use this when the task is “validate this LongLive/LongCat stage1 checkpoint”, “export the sharded checkpoint to native generator”, or “run fast T2V/I2V KV-cache validation”.

Do not use this for stage-2 DMD questions or for general code-orientation requests. Search `MEMORY.md` for `CausalWanModel`, `teacher_forcing`, or `train_ar.yaml` in those cases instead.

## Inputs / context to gather

1. Resolve the target checkpoint directory or step number.
2. Confirm the source logdir / run directory and whether a native export already exists under:
   - `exports_ckpt<step>/checkpoint_model_<step>/native_generator`
3. Confirm candidate machines:
   - active training pod
   - idle or lightly loaded pod with the same shared filesystem and Python environment
4. Check whether the user wants:
   - export only
   - T2V validation
   - I2V validation
   - both T2V and I2V

## Procedure

1. Check for an existing completed export before doing any heavy work.
   - Prefer reusing an existing `native_generator` export instead of re-exporting the same checkpoint.
2. Keep the active training pod untouched unless the user explicitly accepts the risk.
   - Prefer an idle H200 or similar same-filesystem worker.
3. Verify the source checkpoint is structurally complete before export.
   - Require `meta.pt`.
   - Confirm the sharded `generator/__rank_0.distcp` files are present.
4. Export with compile disabled.
   - Set:
     - `TORCHDYNAMO_DISABLE=1`
     - `SELF_FORCING_DISABLE_TORCH_COMPILE=1`
     - `SELF_FORCING_DISABLE_FLEX_COMPILE=1`
   - Run `export_longcat_generator_to_pretrained.py` to:
     - `exports_ckpt<step>/checkpoint_model_<step>/native_generator`
5. Verify export success immediately.
   - Require `load_state_dict missing=0 unexpected=0`.
   - Confirm the native generator directory and shard files were written.
6. Run KV-cache validation from the exported native checkpoint.
   - Prefer separate GPUs for T2V and I2V when possible.
   - Keep `kv_trace.json`, run logs, ffprobe metadata, and the output mp4 together.
7. Summarize in the user’s preferred shape:
   - whether an existing export was reused or a new one was created
   - where the export lives
   - what validation ran
   - what artifacts prove success

## Efficiency plan

1. Search for an existing native export first; this is the biggest time saver.
2. Avoid exporting on a busy training pod when a same-filesystem idle pod exists.
3. Disable compile/inductor during export and inference to avoid wasting CPU on `torch/_inductor/compile_worker`.
4. If a partially occupied GPU is the only option, downscope to a shorter smoke before burning time on a full validation run.
5. Stop once you have:
   - export completeness
   - `missing=0 unexpected=0`
   - validation artifacts for the requested mode

## Pitfalls and fixes

- Symptom: export is unexpectedly slow even before inference.
  - Likely cause: sharded DCP export is reading tens of GB and competing with the active training job for CPU, page cache, or shared filesystem bandwidth.
  - Fix: move export onto an idle or lightly loaded pod with the same environment.

- Symptom: export or inference spawns `torch/_inductor/compile_worker` processes.
  - Likely cause: compile was left enabled.
  - Fix: set `TORCHDYNAMO_DISABLE=1`, `SELF_FORCING_DISABLE_TORCH_COMPILE=1`, and `SELF_FORCING_DISABLE_FLEX_COMPILE=1`.

- Symptom: a GPU looks available but validation OOMs mid-run.
  - Likely cause: another process is already holding tens of GB, and LongCat KV-cache growth pushes the run over the edge.
  - Fix: prefer a truly empty GPU, especially on H200; otherwise shorten the smoke or reduce cache length.

- Symptom: an empty B200 pod still fails right after `DiT ready` without a Python traceback.
  - Likely cause: machine or interconnect issues outside the Python process.
  - Fix: check `dmesg` for mlx5/CXI errors and switch to a known-good H200 node.

## Verification checklist

- Checked whether an existing export already existed.
- Verified `meta.pt` and the source sharded checkpoint structure before export.
- Disabled compile/inductor for export and validation.
- Confirmed `load_state_dict missing=0 unexpected=0`.
- Saved or identified the validation artifacts:
  - `kv_trace.json`
  - run log
  - ffprobe metadata
  - output mp4
