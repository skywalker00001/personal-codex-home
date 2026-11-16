# 项目背景：按需读取

这是一份筛选后的背景说明，不是服务器实时状态。整理于 2026-11-16；启动任务前以实际代码、合同和产物为准。

## 服务器与模型项目

- 主要工作区在服务器 `/aigc/avatar/houyi`。
- MiniMax-H3 AR/Performer 源码位于 `26_q3/DiffSynth-Studio_AR`；实验配置、日志、权重和验收通常在 `outputs/` 的独立 run 目录。
- 工作涉及 H3 50 步 AR SFT、4/6 步加速适配、DMD、Performer 逐块动作/语音条件、训练与验证看板。
- `clawbot` 是当前工作区的飞书/微信 Codex 桥接维护技能；独立的新飞书部署使用 `clawbot-feishu-deploy`。二者不等于第三方同名产品。

## Performer 的关键区别

不要按版本号猜实现。每次先确定初始化链、task LoRA、Prompt 协议、Qwen 编码范围、DiT 文本 KV 范围、音视频历史窗口、RoPE、监督掩码及训练 CFG。

已出现的协议包括：

- 四字段：`Action`、`Action progress`、`Speech`、`Current speech`，段落间留空行；动作通常一对 `<a>...</a>`，局部台词在 `<d>...</d>` 中。
- 某些四字段实验用两行真正空的 `Speech:` 与 `Current speech:` 表达静音；不可擅自替换成 `silence` 或 `<d></d>`。
- 另有 State-first 协议：`State`、`Action`、`Action progress`、`Speech`、`Current speech`。在该协议里，`Speaking` 保留完整 Speech、空 Current speech 表示没有新词但延续表达；`Listening` 才清空两个语音字段。

这些是不同实验的约定，不能混进同一个对照。先读当前实验合同。

## 编码与推理

部分实现使用 Qwen 第 49 层、final norm 之前的 raw hidden。参考图可同时走 Qwen 图文语义条件与 VAE anchor，两路的作用和 timestep 约定需要分别核实。

局部文本实验中，过去 D 可能只参与 Qwen 可见前缀，DiT 仅接收固定 S/参考条件与当前 D；其他实现会累积历史文本 KV。音视频历史 KV 与文本 KV 是不同缓存来源。需读代码确认，不能把任一画法当作所有版本的固定结构。

“step2100”等通常是训练更新数；“50步”是每个 AR 小块的去噪更新数。每 100 步存权重并不表示每个推理块执行 100 步。Turbo/Pika 等适配器也不会因为文件名出现就自动加载。

视频 training CFG 与音频 training CFG 可以不同；训练反向 CFG 的配置不能直接当作推理额外 CFG。LoRA 要核对主块/token_refiner、QKV 独立或合并、rank、alpha 和初始化链，而不是仅比较张量键数。

## 结果评估

重点关注动作有没有遗漏、重复或延后，台词是否一次完整说出，句中是否卡顿，聆听时是否乱讲话，以及较长视频的外推和历史缓存行为。

评估页面应显示真实输入和每块区间。ASR/VAD、静态截图和误差统计能帮助定位，不能替代对原生音视频的审查。历史临时 Cloudflare 域名不是永久入口，交付前重新确认。
