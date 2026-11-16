# Inference queue, MMS, CSV, and dashboard publication

Use this reference when moving from approved schedules to execution or presentation.

## Adapter contract

Wrap any reference inference implementation so one job takes:

```text
checkpoint/runtime assets, prompt ID and text, sampler,
final timestep list, CFG/rescale, seed(s), output directory
```

and writes:

```text
output video (.mp4)
manifest.json
status.json
```

The manifest must contain the resolved runtime assets, sampler, CFG, rescale, seed(s), the exact list passed to sampling, its coordinate space, and the MP4 path. `status.json` must reach exactly one terminal state:

```json
{"state":"complete","manifest":{...}}
```

or

```json
{"state":"failed","error":"..."}
```

## Resident worker queue

Use a unique run root with a shared queue visible to every approved GPU node. Each job should have a stable ID such as `<schedule_key>_<prompt_id>` and a unique output directory.

Before launching a worker or writing a request, summarize the resolved model, schedules, prompt scope, GPUs, runtime parameters, run root, and delivery outputs to the user. Start only after explicit confirmation.

Suggested lifecycle:

```text
request.json -> running.json -> done.json / failed.json
tasks/<schedule_key>/<prompt_id>/status.json
tasks/<schedule_key>/<prompt_id>/output/
state.json
```

Start one long-lived worker process per confirmed GPU. If the user named only nodes, discover free cards first and list the exact proposed allocation in the preflight confirmation; never silently select a single-card fallback. Recheck those cards immediately before launch and reconfirm if availability changed. A worker loads the model once, atomically claims queue jobs, calls the adapter, and writes status/manifest. Before using multiple nodes, confirm the queue and task directories are shared; namespace logs by pod and GPU so concurrent nodes do not overwrite each other's logs.

Run a smoke test before enqueuing the full matrix. Verify the MP4, status, manifest, and actual scheduler calls. Extend a partially completed schedule only by appending missing prompt IDs; never overwrite completed task directories.

## Full 16-prompt expansion

When expanding a tested schedule to all 16 prompts, first resolve each task's immutable identity from its manifest: model/runtime assets, prompt ID/text, sampler, final timestep list, CFG/rescale, seed(s), and video settings. For every matching prior task with a successful video and verified MMS URL, reuse that URL; do not enqueue, regenerate, or re-upload it. Queue only missing identities.

Export one URL CSV in source-CSV order containing reused and new URLs. The default deliverable for this expansion is that CSV only. Do not add cards, alter filters, or otherwise modify the dashboard unless the user explicitly asks.

## Monitor and MMS

Generation, upload, and display are concurrent per-task stages. A completed MP4 must enter upload immediately while remaining workers continue inference; do not accumulate finished MP4s for a terminal bulk upload. The monitor should repeatedly:

1. read job statuses;
2. validate completed MP4 files;
3. immediately enqueue/upload each individual completed video with no MMS URL, independently of other running tasks;
4. verify the returned URLs;
5. after every verified individual upload, atomically update `state.json` and a URL mapping immediately;
6. report planned, queued, running, complete, failed, and uploaded counts.

The environment's usual uploader is:

```bash
/aigc/avatar/wentao/t2v_dmd_tracker/upload-mms-oneclick.sh \
  --html <run-root>/mms_manifest.html \
  --mapping <run-root>/mms_uploads.json \
  --workers <N>
```

Use it only for videos the user has asked to publish. If upload fails, retry upload from the retained MP4; do not rerun a successful inference.

## Dashboard state synchronization contract

The monitor, not a terminal bulk post-processing step, owns the dashboard state. Before workers launch, write an initial `state.json` containing one record for every planned `<schedule_key, prompt_id>` pair. Each record includes at least `state`, schedule metadata, prompt ID, and optional `mms_url`/error; initialize it as `pending`.

The monitor must poll/observe task status for the entire active run and atomically replace `state.json` (write temp file, then rename) whenever an individual task changes state:

```text
pending -> running -> uploading -> published
                 \-> failed
```

`published` requires a verified MMS URL. A completed MP4 must become `uploading` and trigger its independent MMS upload immediately; it must not wait for sibling tasks or an uploader batch. Retain the `failed` error in state. Update a monotonically increasing `version`/`updated_at` field on every write.

The HTML must render placeholders for `pending`, visible in-progress status for `running`/`uploading`, an error state for `failed`, and the video card for `published`. It must poll the relative state path on a short fixed interval (for example 2–5 seconds) with cache bypassing, such as `fetch(stateUrl + '?v=' + versionOrTimestamp, {cache: 'no-store'})`, and rerender whenever the received version changes. Do not rely on a manual refresh, static embedded data, a one-time fetch, or browser-cached JSON. Verify this on the public URL by changing one test task state and observing the page transition without reload before workers are launched.

## Result CSV

After all requested URLs exist, export in the source prompt CSV order. Minimum fields:

```csv
prompt_id,mms_url,schedule_key,group,candidate,denoising_step_list
```

Validate that row count equals the requested prompt count and every `mms_url` is nonempty before delivering the CSV.

## Dashboard requirements

Create this page before workers start. Copy `/aigc/avatar/hsiaoyuan/distillation/vimoo_8step_dmd_noise_test/by_vfm_script/index_5-3_1200.html` first, then apply the smallest data/runtime edits required for the new run. Do not reproduce it from memory, substitute a new layout, or remove template controls for missing/pending results. Treat the dashboard root as a public-site namespace: reuse one verified public URL prefix and one static server/tunnel for all named pages and result assets beneath that root. Before launching a service, discover whether that shared endpoint is healthy and compatible; reuse it if so. Do not create another Cloudflare/public site for a separate experiment, HTML filename, or run. If no compatible shared endpoint exists, provision one, record its public prefix and process/command for reuse, and use only page-specific URLs such as `<public-prefix>/<named-page>.html`. Immediately verify the new page loads and report that page URL to the user before or at worker launch. Keep the shared serving/tunnel process alive while any active run relies on it. Implement the state-synchronization contract above: the initial public page must show every planned pending placeholder, then poll without caching and render every individual status/MMS update while other tasks continue generating and uploading. Preserve:

- original-sampling cards as independent controls;
- candidate group and per-candidate filters;
- actual high/low lists on each card;
- uniform video geometry and MMS “打开视频” links;
- “播放本区 / 暂停” in each prompt section, with global pausing before play;
- a visible completion summary.

## Required UI acceptance before reporting the page

Validate the newly served public page against the canonical template, not merely that it returns HTTP 200. Use browser inspection/screenshot when available; otherwise inspect the generated DOM/CSS/JS and exercise the controls. Correct any mismatch before reporting the URL as available.

- The template's layout and design tokens remain: header, grouped filter bars, card styling, uniform 16:9 media, and desktop grid of four cards per row.
- The filter area retains original-sampling controls above the candidate-group controls; the prominent dark-red “只看已选候选” control; clear/default/select-all actions; subgroup switches with separators; and C1–Ck controls.
- Candidate-selection state follows the specified rule exactly: before selections, “只看已选候选” and **only the top-level candidate-group checkboxes in its filter row** are disabled, **and all groups plus C1–Ck are selected and visible by default**. The lower complete-candidate panel's subgroup switches and C1–Cx checkboxes remain interactive; “清空 / 默认 / 全选” retain their template behavior. After explicit selections, update this same page's state: remove disabled attributes/classes from the scope and top-level controls, rebind their handlers after render, and initialize “只看已选候选” checked. Exercise the scope toggle, every top-level group switch, the three action buttons, lower subgroup switches, and C1–Cx to verify each works. Toggling scope restores/hides the same controls and cards as the template.
- Every prompt section retains its top-right adjacent “播放本区” and “暂停” buttons. Playing one section pauses all videos in other sections.
- Cards retain the template color semantics, high/low timestep display, pending placeholder behavior, video dimensions, “打开视频” link, and completion summary.
- Confirm the public page can fetch its relative state/JSON path without caching, render the full planned pending matrix, and render each transition (`running`, `uploading`, `published`/`failed`) after an individual test state update without refresh.

Selection state is user authority. With no declared selected set, initialize every group and C1–Ck as selected/visible, and disable only “只看已选候选” plus the top-level candidate-group checkboxes; lower subgroup and C1–Ck controls remain interactive. After explicit selection, enable the top-level controls, initialize “只看已选候选” checked, and make its checked state filter to exactly the selected set. Unchecking it must restore the full subgroup and C1–Ck controls.

Do not consider the selected-state update complete merely because the page text changed. Reload the public page after the update and verify the enabled controls have no stale `disabled` attribute, disabled visual class, or detached event handler.
