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

## Workflow Steps

1. Clarify Target and Scope
   - Identify the target handle (e.g. `@Gorden_Sun`, `@xiaomovps`).
   - Define the time window (e.g. latest 24 hours, past 3 days, or specific topic).
   - Determine the output goal: brief summary, resource list, or deep-dive thread breakdown.

2. Retrieve and Parse Account Data
   - Access recent posts, replies, and pinned tweets from the target profile.
   - For long threads, unroll all chained tweets in chronological order to maintain full context.
   - Capture media descriptions, video transcripts (if available), and referenced quote tweets.

3. Extract and Verify Key Intelligence
   - Categorize items by topic: product releases, prompt techniques, code repos, tutorials.
   - Extract raw external URLs (expanding shortened links where applicable).
   - Filter out noise, pure self-promotion, and repetitive retweets.

4. Produce Structured Output
   - Title and Author: Handle, collection date, total posts analyzed.
   - Top Highlights: 1-3 major updates with brief context.
   - Resource Index: Markdown table or bullet list with tools, GitHub links, and descriptions.
   - Key Takeaways: Actionable insights for the user.

## Gotchas and Constraints

- Rate Limits and Login Walls: Direct browsing may hit login prompts; fall back to search-based retrieval or RSS feeds when available.
- Link Shorteners: Verify destination URLs before presenting them to avoid broken t.co links.
- Thread Continuity: Ensure reply chains from the author are gathered as a single narrative rather than fragmented posts.
