---
name: "houyi-video-publish-verify"
description: "Publish a completed Houyi video directory through an existing file server/Cloudflare path and prove browser-seekable playback with HTTP Range, not only HTTP 200."
metadata:
  source-snapshot: "2026-11-16"
  legacy-argument-hint: "[source_video_dir] [server_root_or_url]"
  legacy-disable-model-invocation: "true"
  legacy-user-invocable: "false"
  legacy-allowed-tools: "[\"Bash\"]"
---

# Houyi video publish and verify

> 跨机器使用：文中的 `/aigc`、`/proc`、GPU 和集群操作属于原 Linux 服务器环境；在 Mac 上先确认远程目标与路径。历史参数和操作授权不是当前任务的默认授权。


## When to use

Use when the user asks to put completed inference/validation MP4s “online”, requests a web-openable URL, or needs confirmation that browser seeking works. Do not use to expose a directory unless the user has authorized that publication, or to claim a temporary Cloudflare URL will remain stable after a tunnel restart.

## Inputs / context to gather

1. Resolve the source video directory, intended public alias, and the existing file-server root.
2. Inspect the server process/command to confirm its actual root and port; do not infer them from an old URL.
3. Inventory the intended subdirectories, MP4 count, and the relevant manifests or media metadata.
4. Obtain the current public tunnel URL from the running service or its established publishing path.

## Procedure

1. Prefer a symlink beneath the confirmed server root over copying or moving the original results. Refuse/ask if the alias already exists and points elsewhere.
2. Check the public directory listing and each intended checkpoint/result subdirectory.
3. Verify manifest status and task metadata where present; for videos without manifests, use `ffprobe` on representative MP4s.
4. Perform a real Range request against a representative MP4:
   ```bash
   curl -L -s -D - -H 'Range: bytes=0-1023' -o /dev/null "$URL" | tr -d '\r' | sed -n '1,12p'
   ```
5. Report the clickable root/subdirectory URLs, local source path, counts/metadata, and whether the response had `HTTP 206`, `content-range`, and `accept-ranges: bytes`.

## Efficiency plan

1. Inspect the existing server before searching repositories or starting a second server.
2. Validate one representative MP4 per result/checkpoint family; expand only if results differ.
3. Stop after public listing, metadata/count checks, and Range evidence are all present. Treat the tunnel hostname as point-in-time information.

## Pitfalls and fixes

- Symptom: the MP4 opens but the browser progress bar cannot be dragged.
  - Likely cause: the tunnel returned HTTP 200 to a Range request.
  - Fix: use a URL/path whose Range response is `206 Partial Content` with `content-range` and `accept-ranges: bytes`.
- Symptom: publication would duplicate a large results directory.
  - Likely cause: copying was used instead of the existing served-root link pattern.
  - Fix: create a checked symlink after confirming the public alias and source are correct.
- Symptom: a previously reported link no longer works.
  - Likely cause: the Cloudflare Tunnel restarted.
  - Fix: recover the live tunnel URL and re-run directory plus Range checks.

## Verification checklist

- The source directory was neither moved nor copied.
- The alias resolves under the confirmed live server root.
- The expected result/checkpoint directories and MP4 count are visible.
- Manifest or `ffprobe` metadata matches the claimed artifacts.
- A representative MP4 returns HTTP 206, `content-range`, and `accept-ranges: bytes` to the Range request.
- The final report labels the Cloudflare URL temporary when applicable.
