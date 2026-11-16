---
name: "video-timestep-evaluation"
description: "Design and run model-agnostic video denoising-timestep evaluations, including candidate schedules, resident multi-GPU inference queues, MMS publication, and comparison dashboards. Use when testing custom timestep lists across video models or inference implementations."
metadata:
  source-snapshot: "2026-11-16"
---

# Video Timestep Evaluation

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


Use this skill to evaluate a video model at custom denoising timestep lists without assuming a particular model family, scheduler implementation, checkpoint format, or inference CLI.

For a concise Chinese request template, see [使用前信息清单.md](使用前信息清单.md).

## Minimal request and invariants

To start, the user only needs to provide:

1. model checkpoint/weight path;
2. a reference inference entrypoint;
3. requested step-count groups and, if already decided, candidate lists; and
4. approved GPU nodes, with GPU indices optional.

If candidates are absent, inspect the reference code/config to identify sampler, timestep space/shift, and native schedule. Propose candidates and the original-sampling baseline first, explicitly state the discovered assumptions, and obtain a **candidate-only confirmation**. After it is accepted, handle those candidates exactly as user-supplied candidates: prepare the complete requirement summary below and obtain its separate preflight confirmation before submitting jobs. If the user supplies candidates, skip only the candidate-only confirmation; still verify their semantics and complete the mandatory preflight confirmation.

Unless the user requests another prompt set, use the long-lived 16-prompt CSV at:

`/aigc/avatar/hanzhen/outputs/vimoo/results/exp411_steps100_180_euler50_selected16_20260919_033638/selected_prompts.csv`

For the default smoke test, run only `t2v_007`（揉面团）and `t2v_011`（芦苇荡）first. Extend to the other prompts only when requested or after the user approves the quick result.

When the user requests the complete 16-prompt matrix after testing has begun, treat it as an append-only expansion: reuse every matching successful task and its verified MMS URL, and enqueue only missing prompts. Matching means the resolved model assets, prompt, sampler, final timestep list, CFG/rescale, seed(s), and video settings are identical; verify this from retained manifests/status/URL mapping before deciding a task is reusable. The default delivery for this 16-prompt expansion is the URL CSV in source-CSV order. Do **not** modify the dashboard during this expansion unless the user explicitly asks for dashboard changes.

Do not infer CFG, VAE, runtime base, or timestep semantics from a checkpoint name. Inspect the reference entrypoint/config and run a single-task smoke test when any of these are uncertain. Choose a unique timestamped run root and new CSV/dashboard paths when the user has not named them.

If GPU indices are given, use exactly those cards. If only nodes are given, inspect currently free GPUs on those nodes, propose the full card list in the preflight summary, and—after confirmation—start one persistent worker per confirmed card. Never silently fall back to one card. Recheck availability immediately before launch; if the confirmed allocation changed, report the new allocation and obtain confirmation again.

## Mandatory preflight confirmation

Before starting workers, enqueuing jobs, or consuming GPU resources, present a concise requirement summary and obtain explicit user confirmation. This gate applies whether candidates were user-supplied or just approved in the candidate-only confirmation.

The summary must state: model mode and resolved assets; reference entrypoint and sampler/shift semantics; every candidate list in its actual input space; prompt scope (including whether the default two prompts are used); GPU nodes/indices and one-worker-per-card plan; resolved CFG/rescale/seed/video settings; unique run root; MMS, CSV, and dashboard paths; the shared public URL prefix; the page URL under that prefix; and its serving/tunnel process. Do not launch until the user confirms this summary or changes it.

Treat a supplied post-shift list as final input: do not shift it again. Persist the actual list passed to the sampler in every task manifest and dashboard card.

## Route by task

### Designing timestep candidates

Read [references/candidate-design.md](references/candidate-design.md) when asked to propose a step-count split, identify the original-sampling baseline, or generate candidate lists.

Return actual sampler-ready values, not only a construction rule. State which coordinate space they occupy, use consistent displayed precision, and mark the high/low boundary explicitly.

### Running a new model or inference implementation

Read [references/execution-and-publishing.md](references/execution-and-publishing.md) when asked to run candidate inference, make workers resident, monitor a run, upload MMS, export CSV, or build/update a dashboard.

Create a thin adapter around the reference inference code rather than changing candidate, monitoring, or dashboard logic to fit an implementation. The adapter must accept one immutable job and produce a MP4, a structured manifest, and a terminal status file.

Use one shared queue and one persistent worker per allocated GPU. Continue monitoring until all planned jobs are terminal and their required MMS URLs have been recorded. Do not rerun successful generation merely because upload or dashboard publication failed. For a complete-16-prompt expansion, enqueue only tasks without a matching successful manifest and verified MMS URL; reuse all prior matching URLs and deliver the combined CSV without changing the dashboard unless requested.

### Publishing a comparison page

Every evaluation must create a new dashboard. If the user gives a name/path, use it; otherwise create a unique `index.html` under the new run/dashboard output. Start from a byte-preserving copy of this canonical template—not a newly written approximation—and modify only the experiment data/configuration, titles, result-state path, and necessary runtime wiring:

`/aigc/avatar/hsiaoyuan/distillation/vimoo_8step_dmd_noise_test/by_vfm_script/index_5-3_1200.html`

UI parity with the canonical template is a delivery requirement, not inspiration. Preserve its design tokens, filter hierarchy, controls, card geometry (four cards per desktop row), color semantics, wording, spacing, responsive behavior, and all interaction behavior. Do not replace the template with a simplified page or omit controls because a run has no current data; unavailable entries must remain as template-style placeholders.

Create the dashboard before inference starts. For dashboards under the same dashboard root, use one stable public URL prefix and one shared static server/tunnel; create each experiment as a different named HTML page (and its distinct state/result paths) beneath that prefix. Discover and reuse a healthy existing endpoint before starting a new one. Do not create a second Cloudflare/public site merely because a new dashboard or run is being added. Only provision a tunnel when no compatible shared endpoint exists, then record its public prefix for reuse by later dashboards. Verify the new page URL is reachable, and report it to the user before or together with worker launch. Keep the shared service alive while any active run uses it. The endpoint must serve both every page and its polled result JSON/state on compatible relative paths, so its initial pending view and later card updates work from the public URL. Before reporting it available, perform the dashboard acceptance checks in [references/execution-and-publishing.md](references/execution-and-publishing.md).

Run generation, MMS upload, and dashboard updates as one concurrent per-task pipeline. Before workers start, initialize the dashboard state with every planned `<schedule, prompt>` task as `pending`, so the public page already shows the complete matrix as template-style placeholders. The monitor must advance each task independently through `pending → running → uploading → published` (or `failed`): observe worker status while jobs run, immediately queue each finished MP4 for its own upload, then atomically update the shared state and render the card as soon as its URL is verified. Never defer upload, state writes, or dashboard updates until a prompt, candidate, schedule, or full run completes.

Keep the page data-driven: while active it must fetch the new run's result JSON/state at a fixed short interval using cache-bypassing requests, repaint from every new state version, use MMS URLs rather than local MP4 paths, and display each card's actual timestep list and live task state. Do not claim a public page is live if it only renders initial HTML or waits for inference completion to receive data. Creating the dashboard, verified public access, streaming MMS publication, and exporting the URL CSV are default delivery steps, not optional follow-up work.

Before a user supplies selected candidates, render “只看已选候选” **unchecked and disabled**. Disable only the top-level candidate-group checkboxes in that same filter row; “清空 / 默认 / 全选” keep their template behavior. The lower complete-candidate panel's subgroup switches and C1–Cx checkboxes must remain enabled and interactive. This initial state must have every candidate group and every C candidate selected and visible (not merely rendered as available), alongside original-sampling and full subgroup controls. Once the user explicitly supplies selected candidates, update the existing page state rather than creating a divergent page: enable the scope control and top-level candidate-group checkboxes, remove their disabled styling/attributes, rebind their handlers after render, and make the scope checked by default. Its checked view must show exactly the user-selected schedules. Verify every re-enabled control works: the scope toggle, each top-level group switch, “清空 / 默认 / 全选”, lower subgroup switches, and C1–Cx; unchecking scope must restore the full candidate controls and cards.

## Operational boundaries

- Never overwrite an existing run root, task output, manifest, URL mapping, CSV, or dashboard unless the user explicitly requests replacement.
- A task is complete only when inference succeeded, its video exists, and the requested result surface has the MMS URL. Keep inference and upload retries separate.
- Play-one-section dashboard actions must pause videos in every other prompt section.
- Give the user progress while a run is active; do not report completion from queued/running state alone.
