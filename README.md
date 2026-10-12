# Twitter Account Collector Skill

A generic, local-runnable tool for collecting and filtering recent messages from Twitter (X) accounts, and producing a structured briefing. No domain lock-in, no auto-posting.

## 📖 Overview

本仓库包含两层：

1. **Skill 层（SKILL.md）**：给 AI Agent（Claude Code / Cursor / Codex 等支持 `SKILL.md` 的框架）的提示词与工作流指引。
2. **工具层（scripts/collector.py）**：一套**真实可运行**的 Python 实现，把"采集 → 时间窗 → 去重 → 噪音过滤 → 汇总"落成代码，可离线验证、可接入定时任务。

> ⚠️ 定位澄清：本仓库是一个**通用的消息抓取工具**，不做任何领域绑定，也不含"自动发推 / 包装文案"等能力。抓取层是**尽力而为、可插拔、有兜底**的本地脚本，是否可用取决于你运行环境的网络与 X 当时的接口策略（详见「限制与真实边界」）。

## 📁 Repository Structure

```
├── SKILL.md                     # Agent Skill 定义与工作流
├── README.md                    # 本文件
├── config.yaml                  # 跟踪账号与抓取深度参数（驱动工具层）
├── scripts/
│   ├── collector.py             # 真实可运行的抓取与过滤实现
│   └── sample_feed.json         # 离线 demo 样本（验证过滤链用）
└── references/
    └── template.md              # 简报输出模板
```

## 🎯 账号范围与抓取深度（需求规格）

### 账号范围（Account Scope）
- **驱动方式**：全部由 `config.yaml` 的 `accounts` 列表配置，纯 `@handle`，不内置任何领域偏好。
- **数量边界**：脚本层**无硬上限**；建议聚焦 **20~50 个高质量公开账号**以保信噪比，超过 100 建议配代理轮换与频控管理。
- **账号类型**：任意公开 X 账号（个人 / 媒体 / 机构 / 项目官方），统一以 handle 配置。

### 抓取深度（Scraping Depth）— 四个维度
| 维度 | 参数 | 默认 | 说明 |
|---|---|---|---|
| 时间深度 | `time_window_hours` | 1（1~72 可调） | 只采集窗口内发布的推文 |
| 条数深度 | `max_tweets_per_account` | 20 | 单次每账号最多处理条数，防一次拉爆 |
| 内容维度 | — | — | 主推文文本 + UTC 时间 + 链接 + 媒体描述；长线程按时间顺序展开为单条叙事；quote 抓被引原文链接 |
| 包含开关 | `include_replies` / `include_retweets` | false / false | 默认不含回复与转推（转推按噪音过滤） |

## 🚀 安装与使用

```bash
pip install pyyaml            # 可选；无 pyyaml 时自动退回内置默认配置
python scripts/collector.py                 # 按 config.yaml 联网抓取并筛选
python scripts/collector.py --demo          # 离线跑样本，验证过滤链（无需网络）
python scripts/collector.py --handle NASA --once
```
- 结果打印到终端，并写入 SQLite（`collector.db`）做去重。
- 接定时任务示例（每小时一次）：`0 * * * * cd /path/to/skill && python scripts/collector.py`

## 🧠 技术原理（真实实现）

流水线：`config.yaml` → 抓取层（可插拔后端）→ **三层过滤** → SQLite 去重 → 汇总简报。

### 三层过滤
1. **第一层 · 时间窗（Time Filter，硬门槛）**
   只保留 `created_at` 落在「当前时间前 N 小时」（默认 1 小时，可配）内的推文。
   **为什么按时间而不是按"最新 N 条"**：按条数会在目标账号当天没发推时，把昨天的旧推当新动态重复抓出。本实现解析每条推文的 UTC 时间戳做判断。
2. **第二层 · SQLite 去重（Deduplication）**
   每条推文以唯一 `tweet_id` 入库比对；上一周期已处理过的（即使因时间边界重叠再次抓到）直接丢弃，保证不重复。
3. **第三层 · 噪音过滤（Noise Filter）**
   过滤明确噪音：过短（`< min_chars`）、纯打卡/问候（gm / 早安 / 下午茶 等且内容短）、以及按开关排除的回复 / 转推。**不做"价值判定"**——哪些消息对你有用由你自行决定，工具只剔除明显低信息内容。

### 第四层 · 汇总输出
将保留下来的消息按账号 + 时间排序，产出结构化简报（套用 `references/template.md`）。工具只负责"把消息抓干净并摆好"，不做任何发推或文案包装。

### 抓取层（尽力而为、可插拔、有兜底）
`fetch_tweets()` 依次尝试多个后端，任一成功即采用：
- **后端 A · fxtwitter 免登录接口**：返回该账号最新推文（最佳情况，但仅单条、易限流）。
- **后端 B · Syndication 嵌入时间线**：尽力而为；X 经常变动/封锁该接口，失败时返回空并降级。
- **兜底 · 文件投放**：可将抓到的 JSON 直接放入流程（接口全面不可用时手动/半自动接料）。

请求之间按 `request_delay`（默认 2.5s）平滑间隔，降低触发频控的概率。

## ⚠️ 限制与真实边界（必读）

| 维度 | 真实情况 |
|---|---|
| **免登录抓取** | 技术上存在但**脆弱且处于 ToS 灰区**。X 不公开任何频控数字；网传"单 IP 150~300 次/15 分钟""2.5 秒间隔"均为**经验估计，非官方保证**。接口随时可能失效，本工具已做降级处理，但无法保证长期可用。 |
| **账号数量上限** | 脚本本身**无硬上限**；实际能稳定跟踪多少，取决于接口稳定性、是否使用代理轮换、以及账号发推频率。运营上建议聚焦 20~50 个高质量信源；盲目堆到 200+ 需配多代理且风险升高。 |
| **抓取深度上限** | 受后端能力制约：fxtwitter 仅返回最新单条，syndication 时间线（若可用）才支持多条约覆盖；`max_tweets_per_account` 为本地裁剪上限，不保证后端真能返回那么多。 |
| **运行环境** | 需在**你本机/可联网环境**运行（如有代理请通过 `https_proxy` 环境变量传入）。沙箱、部分服务器、或受限网络可能直接抓不到数据——此时用 `--demo` 验证逻辑，抓取层按需替换后端。 |
| **时间窗默认值** | 默认 1 小时，可在 `config.yaml` 调；去重库 `collector.db` 随运行累积，如需重置直接删除该文件。 |
| **噪音词表** | 内置词表为通用起点，请按你的场景在 `config.yaml` 中增删；误判需自行校准。 |

## 📄 License
MIT License
