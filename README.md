# Twitter Account & AI Intelligence Collector Skill

An AI Agent Skill for tracking, collecting, and synthesizing breaking AI intelligence, tools, and creator updates from Twitter (X).

## 📖 Overview

`twitter-account-collector` is an upgraded intelligence radar designed for AI Agents (Claude Code, Cursor, Codex, and OpenAI/Gemini Agent frameworks supporting `SKILL.md`).

It combines **targeted creator surveillance** with a **global boolean keyword radar** to capture verified AI intelligence within 1-hour or 24-hour windows.

### 🌟 Key Capabilities
- **Dual-Track Surveillance**:
  - **Tier 1 Official Labs & Leaders**: Batched polling of OpenAI, Anthropic, Google DeepMind, Meta, xAI, Mistral, DeepSeek, and top researchers.
  - **Global Boolean Radar**: Targeted keyword streams covering Model Drops, Open Weights, Coding Agents (MCP, Cursor, Claude Code), Venture/M&A, and Policy/Security.
- **API Budgeting & Rate-Limit Protection**: Groups accounts into composite `from:A OR from:B` queries to respect the 25-item per request ceiling.
- **Semantic Topic Deduplication**: Evaluates `[Entity + Action + Version]` signatures against a 7-day rolling store (`seen_store.json`), preventing duplicate reporting across multiple curators.
- **Value Judgment Filter**: Automatically suppresses low-signal commentary, small patch releases, and speculative noise.
- **First-Party Traversal**: Traces secondary tweets back to canonical GitHub repos, official blogs, or research papers.

## 📁 Repository Structure

```
twitter-account-collector/
├── SKILL.md                 # Agent Skill definition, rules & workflow
├── README.md                # Project documentation & integration guide
└── references/
    ├── watchlist.json       # Tiered directory of monitored accounts
    ├── query_matrix.json    # Categorized boolean search queries
    └── template.md          # Output briefing format template
```

## 🚀 Installation & Usage

### 1. In Claude Code / Cursor / Agent frameworks
Copy this folder into your agent skills path:
```bash
# Example for Claude Code:
mkdir -p ~/.claude/skills/twitter-account-collector
cp -r * ~/.claude/skills/twitter-account-collector/
```

### 2. Prompting Examples
- *"运行 X AI 资讯检索，抓取过去 1 小时内顶级实验室和全网关键词的重大发布，按标准格式输出"*
- *"收集 @sama 和 @AnthropicAI 最近 24 小时的重要动态，剔除日常水推并提取相关链接"*
- *"用布尔雷达搜索最近是否有开源大模型发布或重大代码 Agent 更新"*

## 📄 License
MIT License
