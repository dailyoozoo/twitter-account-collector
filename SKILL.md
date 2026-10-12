---
name: twitter-account-collector
description: Collect, monitor, and summarize updates and shared resources from Twitter (X) accounts. Use when tracking specific X creators, extracting daily AI digests, summarizing threads, or compiling links and tools from Twitter handles.
---

# Twitter Account Collector

A structured skill for tracking, extracting, and synthesizing information from target Twitter (X) creators and accounts.

## Summary

This skill guides the agent in gathering recent posts from specified Twitter/X accounts, extracting core technical points, external links, and recommended tools, and formatting them into high-value digests or structured briefings.

## When to Use

- Tracking specific Twitter/X creators or thought leaders (e.g. AI researchers, developers, founders).
- Compiling daily or weekly digests from target accounts.
- Extracting GitHub repositories, articles, and product links mentioned in tweets.
- Summarizing multi-tweet threads and discussions into coherent notes.

## Tooling (真实可运行实现)

本 skill 附带一套本地可运行的 Python 工具，把采集与筛选落成代码，避免只停留在提示词层面：

- `scripts/collector.py` —— 通用消息抓取实现（时间窗 → SQLite 去重 → 噪音过滤 → 汇总简报），支持 `--demo` 离线验证。
- `config.yaml` —— 跟踪账号列表与筛选参数（request_delay / time_window_hours / min_chars / 噪音词 / 价值词）。
- `scripts/sample_feed.json` —— 离线 demo 样本。

优先用工具跑出真实结果；纯 Agent 模式下若无工具运行环境，再按下面的工作流以检索/RSS 兜底手动完成。

## Workflow Steps

1. Clarify Target and Scope
   - Identify the target handle (e.g. `@Gorden_Sun`, `@xiaomovps`).
   - Define the time window (e.g. latest 24 hours, past 3 days, or specific topic).
   - Determine the output goal: brief summary, resource list, or deep-dive thread breakdown.

2. Retrieve and Parse Account Data
   - 首选运行 `scripts/collector.py`（按 `config.yaml` 的账号与参数自动采集）。
   - 无运行环境时，访问目标 profile 的最近推文、回复与置顶推文；长推文线程按时间顺序展开以保持完整上下文。
   - 抓取媒体描述、视频转写（如有）与被引用的 quote 推文。

3. Extract and Verify Key Intelligence
   - 按主题归类：产品发布、提示词技巧、代码仓库、教程。
   - 提取原始外链（展开短链），过滤噪音、纯自推与重复转推。
   - 价值/噪音判定参考 `config.yaml` 的 `value_keywords` / `noise_keywords`（可随领域增删）。

4. Produce Structured Output
   - 套用 `references/template.md` 产出简报：目标账号、时间范围、采集条数、保留消息列表（含时间、原文、链接）。
   - 工具只负责"把消息抓干净并摆好"，不做任何发推或文案包装；哪些消息有价值由用户自行判断。

## Gotchas and Constraints

- 免登录抓取是尽力而为、可插拔、有兜底：X 不公开频控数字，网传「单 IP 150~300 次/15 分钟」「2.5 秒间隔」均为经验估计，非官方保证；接口可能随时失效。
- 本工具只做消息抓取与简报汇总，不含任何发推或文案包装能力；如需自动发布请另接 X 官方 API（收费）并遵守其开发者协议。
- Rate Limits and Login Walls: Direct browsing may hit login prompts; fall back to search-based retrieval or RSS feeds when available.
- Link Shorteners: Verify destination URLs before presenting them to avoid broken t.co links.
- Thread Continuity: Ensure reply chains from the author are gathered as a single narrative rather than fragmented posts.
