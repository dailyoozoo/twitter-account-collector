---
name: twitter-account-collector
description: Collect, monitor, and summarize updates, breaking AI developments, and shared resources from Twitter (X). Supports target creator tracking and automated keyword radar retrieval with semantic deduplication and value filtering.
---

# Twitter Account & AI Intelligence Collector

A structured skill for dual-track tracking, high-value filtering, and intelligence synthesis on Twitter (X).

## Summary

This skill empowers the agent to conduct real-time intelligence collection on Twitter (X). It integrates targeted creator surveillance (AI labs, key founders, and tech reporters) with an automated boolean search radar to discover breaking AI model releases, agent frameworks, industry shifts, and technical resources within a defined time window (e.g. past 1 hour, past 24 hours). It enforces semantic topic deduplication, source verification, and strict value filtering to eliminate noise.

## When to Use

- Tracking specific Twitter/X creators, AI research labs, or tech founders.
- Conducting hourly or periodic AI intelligence sweeps on X.
- Catching breaking model releases, open-weights drops, and agent skill announcements.
- Filtering high-signal breaking news from secondary commentary, retweets, and promotional noise.
- Extracting clean external links, GitHub repositories, and papers from posts.
- Compiling concise intelligence briefings with direct primary sources.

## Core Directives & Retrieval Tools

Utilizes public-read X API capabilities (subject to frequency limits and max 25 posts per request):
- `search_posts_all`: Global boolean keyword and batch-account search (supports `start_time`, `until_id`, `-is:retweet`, language filters).
- `get_users_posts`: Chronological timeline retrieval for target profiles.
- `get_news` / `search_news`: Trending topic discovery and official X editorial summaries.
- `get_posts_counts_recent`: Sudden volume spike and sentiment acceleration detection.

---

## Operational Workflow

### Phase 1: Dual-Track Retrieval Strategy

#### Track 1: Targeted Creator & Lab Surveillance (Batched & Tiered)
To avoid rate limits from polling 30+ accounts individually, group handles into batched `from:` queries in `search_posts_all` (e.g., `(from:OpenAI OR from:AnthropicAI OR from:GoogleDeepMind OR from:xai) -is:retweet`):
- **Tier 1 (Official Labs & Research Teams)**:
  - OpenAI: `@OpenAI`, `@OpenAIDevs`, `@OpenAINewsroom`, `@ChatGPTapp`
  - Anthropic: `@AnthropicAI`, `@claudeai`
  - Google: `@GoogleDeepMind`, `@GoogleAI`, `@GeminiApp`, `@googleaidevs`
  - Meta & xAI: `@AIatMeta`, `@xai`
  - Open Source & Ecosystem: `@MistralAI`, `@deepseek_ai`, `@Alibaba_Qwen`, `@huggingface`, `@nvidia`, `@cursor_ai`, `@perplexity_ai`, `@LangChainAI`
- **Tier 2 (Key Pioneers & Executives)**:
  - OpenAI: `@sama`, `@gdb`
  - Anthropic: `@DarioAmodei`, `@jackclarkSF`
  - Google: `@sundarpichai`, `@demishassabis`, `@OfficialLoganK`, `@JeffDean`
  - Industry: `@elonmusk`, `@karpathy`, `@AndrewYNg`, `@ylecun`
- **Tier 3 (News Curators & Tech Reporters)**:
  - `@TheInformation`, `@theverge`, `@TechCrunch`, `@Reuters`, `@testingcatalog`, `@btibor91`, `@rowancheung`, `@swyx`, `@simonw`

#### Track 2: Global Boolean Keyword Radar
Run queries with `-is:retweet` and strict `start_time` (e.g., past 1 hour) across categorized topics:
- **Model Releases**:
  - `(GPT OR Claude OR Gemini OR Llama OR Grok OR Qwen OR DeepSeek OR Mistral) (release OR launch OR announce OR "now available") -is:retweet`
  - `("new model" OR "open weights" OR "open-source model") AI -is:retweet`
- **Products & Agents**:
  - `("AI agent" OR "coding agent" OR "agent skills" OR MCP) (launch OR ships OR introducing) -is:retweet`
  - `(Cursor OR "Claude Code" OR Codex OR Antigravity OR Devin) (launch OR update) -is:retweet`
- **Industry & Regulatory Milestones**:
  - `AI (acquires OR acquisition OR "raises" OR bankruptcy OR "Series A" OR "Series B") -is:retweet`
  - `AI (regulation OR lawsuit OR ban OR "executive order" OR "AI Act") -is:retweet`
  - `AI ("safety" OR "security" OR vulnerability OR jailbreak OR leak) -is:retweet`
- **Leaks & Early Intel**:
  - `(spotted OR leaked OR "coming soon") (GPT OR Claude OR Gemini) -is:retweet`
- **Chinese AI Ecosystem**:
  - `(大模型 OR AI) (发布 OR 开源 OR 上线) lang:zh -is:retweet`
- **User-Specific Verticals (Adjustable)**:
  - `("text to speech" OR TTS OR "video editing" OR "speech to text") AI (release OR open) -is:retweet`

#### Track 3: External Cross-Verification
- Check trending X topics against Hacker News frontpage, TechCrunch, The Verge, Reuters, and official company engineering blogs.
- If an X post shares a screenshot or summary of external news, penetrate the secondary post and locate the canonical primary URL (GitHub repo, research paper, blog post).

---

### Phase 2: Deduplication & Watermark Tracking

1. **Semantic Topic Fingerprinting**:
   - Maintain a 7-day rolling seen store (`references/seen_store.json`).
   - Group by `[Entity] + [Action] + [Key Version/Parameter]` (e.g. `[Claude Code] + [Release] + [v1.0]`).
   - If multiple accounts post about the identical announcement, cluster them and keep only the earliest or highest-engagement primary tweet.
   - Discard rewrites, quote tweets, and secondary reports unless a material new milestone occurs (e.g., rumor officially confirmed).
2. **Snowflake ID Watermark**:
   - Record the latest tweet `max_id` from each retrieval cycle to set `since_id` on the subsequent request, avoiding time-window boundary gaps.

---

### Phase 3: Value Judgment Matrix

| Category | Decision | Criteria |
| :--- | :--- | :--- |
| **Breaking Releases** | 💡 **Push** | SOTA foundation model release, general availability (GA), major open-weights drop. |
| **Major Business Shifts** | 💡 **Push** | Significant funding rounds (Series A+), strategic acquisitions, prominent leadership shake-ups. |
| **Governance & Security** | 💡 **Push** | Major regulatory rulings, landmark lawsuits, confirmed zero-day exploits, model weights leak. |
| **Tool & Agent Innovations** | 💡 **Push** | Novel agent architectures, MCP implementations, developer tooling with working code. |
| **Routine Chatter / Noise** | ☕ **Skip** | Minor patch bumps, unconfirmed rumors without proof, pure personal opinions, reposted memes. |

---

### Phase 4: Output Delivery Format

- **Header / Time Window**: e.g., `【过去 1 小时 AI 核心热点快报】`
- **Item Format**:
  - **[Bold Headline]**: Concise 1-2 sentence breakdown of what occurred and its broader industry significance.
  - 🔗 **Direct Sources**: Canonical primary source (official announcement / blog / GitHub) + original X discussion link.
- **Quiet Mode**: If no high-signal event meets the push threshold during the monitored window, output a concise single-line confirmation (or silence) to avoid message fatigue.
