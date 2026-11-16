---
name: "helios-transformer-distill-diff"
description: "Build or verify a Helios transformer A-B distill diff when the user wants a reusable diff artifact, especially if they insist the 6 patch_short/mid/long weight+bias keys must participate."
metadata:
  source-snapshot: "2026-11-16"
  legacy-argument-hint: "[a_model_dir] [b_model_dir] [out_dir]"
  legacy-disable-model-invocation: "false"
  legacy-user-invocable: "false"
  legacy-allowed-tools: "[\"Bash\"]"
---

# Helios transformer distill diff

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


Use this when the task is “输出 A - B 存成类似 distill diff 的目录”, “算 partial diff”, or “严格确认 partial 的 6 个 key 都参与了运算”.

Do not use this for ordinary LoRA merge debugging or `hy_exp` process monitoring; search `MEMORY.md` for those.

## Inputs / context to gather

1. Resolve the exact A model dir, B model dir, and output dir.
2. Confirm whether the task is in `/aigc/avatar/wentao/Helios_hz_2`, where the validated tooling lives:
   - `tools/build_transformer_distill_diff.py`
   - `scripts/tools/build_distill_diff_ab.sh`
3. Check whether the user expects:
   - a transformer-only diff directory
   - a 6-key partial diff artifact
   - or both

## Procedure

1. Verify the source models contain the required transformer and patch tensors.
   - For strict Helios diffs, require:
     - `patch_short.weight`
     - `patch_short.bias`
     - `patch_mid.weight`
     - `patch_mid.bias`
     - `patch_long.weight`
     - `patch_long.bias`
2. Use the validated builder instead of re-implementing the math.
   - Preferred wrapper:
     - `bash scripts/tools/build_distill_diff_ab.sh "$A" "$B" "$OUT"`
   - Or call:
     - `python tools/build_transformer_distill_diff.py ...`
3. After build, verify the Helios diff layout:
   - `OUT/diff_stats.json`
   - `OUT/transformer/config.json`
   - `OUT/transformer/diffusion_pytorch_model.safetensors.index.json`
   - transformer shard files referenced by the index
4. Verify the 6 patch keys explicitly.
   - Check they were present in A and B.
   - Check they appear in the output index / stats.
   - If the task is a partial-only diff, verify the saved artifact contains all 6 keys.
5. If the user wants to load the diff later, confirm the consumer path.
   - In this workflow, `infer_a2v_custom_distilled.py` applies `distill_diff_path` before PEFT LoRA loading.

## Efficiency plan

1. Reuse `tools/build_transformer_distill_diff.py`; do not re-derive shard rewriting by hand unless the existing tool is broken.
2. Read only the shard(s) containing the patch keys if the task is patch-focused.
3. Stop once you have:
   - built the diff
   - verified layout
   - verified all 6 patch keys participated
4. If reconstruction mismatch is tiny fp32 noise, do not keep digging forever.

## Pitfalls and fixes

- Symptom: the diff “works” but patch behavior is wrong.
  - Likely cause: the 6 patch keys were not explicitly required or verified.
  - Fix: enforce those exact keys in A, B, and output validation.

- Symptom: exact reconstruction check fails around `1e-10` to `1e-9`.
  - Likely cause: fp32 roundoff.
  - Fix: use a small tolerance instead of treating it as a semantic error.

- Symptom: output is huge or duplicated unnecessarily.
  - Likely cause: every transformer shard was rewritten.
  - Fix: only rewrite the shard containing modified patch keys and hardlink/symlink the rest when appropriate.

## Verification checklist

- The diff was produced with the validated Helios builder, not ad hoc tensor edits.
- `diff_stats.json` exists.
- The transformer index exists and references actual shard files.
- All 6 patch keys were explicitly checked and confirmed to participate.
- If the task involved later loading, the answer states that `infer_a2v_custom_distilled.py` applies the diff before PEFT LoRA loading.
