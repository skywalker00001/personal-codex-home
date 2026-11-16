---
name: "h3-performer-training-delivery"
description: "Prepare, launch, validate, and publish a scoped MiniMax-H3 Performer continuation when the user delegates a Performer experiment end to end."
metadata:
  source-snapshot: "2026-11-16"
  legacy-argument-hint: "[run_name] [parent_checkpoint] [training_pods] [inference_pods]"
  legacy-disable-model-invocation: "true"
  legacy-user-invocable: "false"
  legacy-allowed-tools: "[\"Bash\"]"
---

# H3 Performer training delivery

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


## When to use

Use for an approved H3 Performer continuation, especially a step-2100 warm start that needs balanced data, scoped GPU ownership, ten-case validation, dashboard publication, and an audited handoff.

Do not use for proposal-only prompt/data discussion: preserve the approval gate. Do not use this to override a foreign GPU guard or to infer that a previous Cloudflare URL remains live.

## Inputs / context to gather

1. Record the approved protocol, parent checkpoint, all recipe changes, target training/inference pod scopes, and protected workloads.
2. Resolve the code root and output root under `/aigc/avatar/houyi/26_q3/DiffSynth-Studio_AR/examples/minimax_h3/` and `outputs/`.
3. Inspect exact GPU compute apps, utilization, `pmon`, process argv, ownership, and any occupier/guard before changing GPU state.
4. Read the training config, data acceptance report, checkpoint contract, current dashboard/server, and the existing comparison result families.

## Procedure

1. Freeze the approved annotation contract before data generation. For v1.5.5 the ordered fields are `State`, `Action`, `Action progress`, `Speech`, `Current speech`; `Speaking` may retain `Speech` with blank `Current speech`, while `Listening` blanks both speech fields. Derive action N/i from measured source boundaries plus visual review; VAD is diagnostic only.
2. Build and audit the accepted data pool and deterministic sampling. Preserve baseline modes unless explicitly changed. Keep suspect pure-action candidates quarantined rather than silently relaxing the contract.
3. Smoke the exact remote Python environment before expensive preprocessing or launch. Confirm dependencies such as `cv2`; set `CUDA_VISIBLE_DEVICES` in the subprocess environment before any Torch import.
4. Validate parent checkpoint load and a small distributed smoke: finite loss/gradients, optimizer updates, tensor counts, and an independent native A/V TP2 reload when required.
5. Touch only approved GPUs. If E32 occupancy is approved for release, use `/aigc/avatar/houyi/26_q1/self_forcing_plus_infi/training_shells/oc/start_occupy_e32.sh stop`; prove all four E32 Pods have no compute apps before launch. Never broad-kill foreign processes or bypass foreign guards.
6. Launch and monitor training with exact process/config matching. Keep training status distinct from saved checkpoint status.
7. Run comparable validation with fixed prompt/noise/reference bundles and fixed inference contract. For the v1.5.5 delivery: 768x1280, 243 frames, 24 fps, 15 blocks, 50 denoising steps/block, TP2, seed 200, native H3 A/V decode, no external audio or ground-truth media.
8. Publish through the existing dashboard while preserving older result families. Audit per checkpoint/results count, format, faststart, protocol invariants, hashes/receipts, and public HTTP 200 plus representative media Range 206.
9. Restore temporary inference-resource policy and exit temporary processes. Report training, inference, publication, dashboard, and audit status separately.

## Efficiency plan

1. Reuse the baseline run's known code/config/data acceptance structure; do not rebuild generic launch logic first.
2. Do one consolidated GPU ownership preflight immediately before each launch, then inspect only approved alternatives if requested cards are busy.
3. Treat `final_delivery.audit.json`, protocol audit, and representative Range checks as the delivery stop gate; do not wait on unrelated exploratory diagnostics.

## Pitfalls and fixes

- Symptom: multiple workers use physical GPU0 and OOM. Cause: visibility was assigned after Torch import. Fix: set it before the interpreter starts, then inspect argv and per-pod `nvidia-smi`.
- Symptom: preprocessing reports `ModuleNotFoundError: No module named 'cv2'`. Fix: test the exact remote environment first or use a dependency-free decoder path.
- Symptom: target G8 cards are busy. Fix: recheck ownership and use only explicitly approved idle alternatives; preserve A32/B32/foreign protections.
- Symptom: smoke, a live training step, or a checkpoint is called complete. Fix: require separately successful inference, publication, dashboard, final audit, and policy restoration.
- Symptom: browser media plays but cannot seek. Fix: require `HTTP 206`, `content-range`, and `accept-ranges: bytes` on a real Range request.

## Verification checklist

- Approved protocol and resource boundaries are recorded.
- Parent checkpoint/data/smoke/reload evidence is present.
- GPU action used exact owned processes and post-action compute-app proof.
- Training and saved-checkpoint status are reported separately.
- Validation contract is invariant across compared checkpoints.
- Dashboard preserves prior result families and representative MP4s pass Range 206.
- Final audit, publication receipts, temporary-process exit, and resource-policy restoration are evidenced.
