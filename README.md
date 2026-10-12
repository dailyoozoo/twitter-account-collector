# Twitter Account Collector Skill

An AI Agent Skill for tracking, collecting, and synthesizing intelligence, tools, and daily updates from Twitter (X) creators.

## 📖 Overview

This repository contains the `twitter-account-collector` skill designed for AI Agents (such as Claude Code, Cursor, Codex, and other Agent frameworks supporting `SKILL.md`).

It provides a standardized workflow for:
- Monitoring target accounts (e.g. AI news curators, tech founders, developers).
- Parsing threads, media descriptions, and discussions.
- Extracting clean URLs, GitHub repositories, and recommended tools.
- Generating structured daily/weekly intelligence briefings.

## 📁 Repository Structure

```
├── SKILL.md                 # Agent Skill definition & operational rules
├── README.md                # Project documentation & GitHub guide
└── references/
    └── template.md          # Output briefing template format
```

## 🚀 Installation & Usage

### 1. In Claude Code / Cursor / Agent frameworks
Copy this folder or download `SKILL.md` into your agent's skills directory:
```bash
# Example for Claude Code:
mkdir -p ~/.claude/skills/twitter-account-collector
cp SKILL.md ~/.claude/skills/twitter-account-collector/
```

### 2. Prompting the Agent
Once installed, simply prompt your agent:
> "帮我收集 @Gorden_Sun 最近3天的推文，整理出一份AI工具日报"
> "Summarize recent threads from @xiaomovps and extract all referenced tools and GitHub links."

## 📄 License
MIT License
