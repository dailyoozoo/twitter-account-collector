#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
twitter-account-collector — 通用消息抓取与筛选实现

设计原则（与 README「技术原理」对应）：
  - 三层过滤：时间窗 -> SQLite 去重 -> 噪音过滤
  - 抓取层「尽力而为、可插拔、有兜底」：不依赖单一接口，X 收紧时自动降级
  - 所有筛选逻辑都是纯本地计算，可离线（--demo）验证，不依赖网络
  - 只做"抓取消息"这一件事：产出结构化简报，不做任何发推/包装

用法：
  python collector.py                 # 按 config.yaml 抓取并筛选（联网，尽力而为）
  python collector.py --demo          # 用 scripts/sample_feed.json 跑完整过滤链（离线可验证）
  python collector.py --handle NASA --once
"""

import argparse
import json
import os
import sqlite3
import time
import urllib.request
from datetime import datetime, timedelta, timezone

try:
    import yaml
except ImportError:
    yaml = None  # 无 yaml 时退回内置默认配置

# ----------------------------------------------------------------------------
# 默认配置（config.yaml 缺失或无法解析时使用）
# ----------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "accounts": ["twitter", "BBCBreaking", "NASA", "TheVerge"],
    "request_delay": 2.5,
    "time_window_hours": 1,
    "max_tweets_per_account": 20,
    "include_replies": False,
    "include_retweets": False,
    "min_chars": 15,
    "db_path": "collector.db",
    "noise_keywords": ["gm", "gn", "早安", "晚安", "午安", "聚会",
                       "下午茶", "哈哈", "lol", "打卡", "转发微博"],
}


def load_config(path="config.yaml"):
    if yaml is not None and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return {**DEFAULT_CONFIG, **cfg}
    return dict(DEFAULT_CONFIG)


# ----------------------------------------------------------------------------
# 抓取层：尽力而为、可插拔、有兜底
# ----------------------------------------------------------------------------
def _make_opener():
    """尊重环境代理（http_proxy / https_proxy），否则直连。"""
    proxies = {}
    for k in ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"):
        if os.environ.get(k):
            proxies["https" if k.lower().startswith("https") else "http"] = os.environ[k]
    if proxies:
        return urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
    return urllib.request.build_opener()


def _http_get(url, timeout=15):
    opener = _make_opener()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; tac/1.0)"})
    with opener.open(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def fetch_fxtwitter(handle):
    """后端 A：fxtwitter 免登录接口，返回该账号最新一条推文（最佳情况）。"""
    try:
        data = json.loads(_http_get(f"https://api.fxtwitter.com/{handle}"))
        tw = data.get("tweet")
        if not tw:
            return []
        return [_normalize(tw, handle)]
    except Exception:
        return []


def fetch_syndication(handle, user_id=None):
    """后端 B：Syndication 嵌入时间线（尽力而为，X 经常变动/封锁，失败返回空）。"""
    if not user_id:
        return []
    try:
        url = (f"https://cdn.syndication.twimg.com/timeline/profile/{user_id}"
               f"?include_available_features=1&include_entities=1")
        _http_get(url, timeout=15)
        # 解析逻辑随接口格式变化，这里仅占位：真实可用时需按返回 JSON 适配
        return []
    except Exception:
        return []


def _normalize(tw, handle):
    """把不同后端的推文字段统一成内部格式。"""
    text = tw.get("text") or tw.get("full_text") or ""
    created = tw.get("created_at") or tw.get("createdAt")
    return {
        "id": str(tw.get("id") or tw.get("id_str") or hash(text)),
        "handle": handle,
        "text": text.strip(),
        "created_at": _parse_dt(created),
        "url": tw.get("url") or f"https://x.com/{handle}",
        "is_reply": bool(tw.get("in_reply_to_status_id") or tw.get("reply")),
        "is_retweet": text.startswith("RT @") or bool(tw.get("retweet")),
    }


def _parse_dt(s):
    if not s:
        return None
    for fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s.replace("Z", "+0000") if s.endswith("Z") else s, fmt)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def fetch_tweets(handle, cfg, user_id=None):
    """抓取某账号近期推文：依次尝试多个后端，任一成功即用；再按深度参数裁剪。"""
    tweets = []
    for backend in (fetch_fxtwitter, lambda h: fetch_syndication(h, user_id)):
        try:
            tweets = backend(handle)
            if tweets:
                break
        except Exception:
            continue
    # 条数深度：每账号最多保留 max_tweets_per_account 条
    return tweets[: cfg.get("max_tweets_per_account", 20)]


# ----------------------------------------------------------------------------
# 第二层：SQLite 去重
# ----------------------------------------------------------------------------
def init_db(db_path):
    con = sqlite3.connect(db_path)
    con.execute("""CREATE TABLE IF NOT EXISTS tweets (
        tweet_id TEXT PRIMARY KEY,
        handle TEXT,
        text TEXT,
        created_at TEXT,
        processed_at TEXT
    )""")
    con.commit()
    return con


def dedup(con, tweets):
    """只保留数据库里没有的推文；已存在则视为重复丢弃。"""
    new, seen = [], 0
    for t in tweets:
        if con.execute("SELECT 1 FROM tweets WHERE tweet_id=?", (t["id"],)).fetchone():
            seen += 1
            continue
        new.append(t)
        con.execute("INSERT INTO tweets VALUES (?,?,?,?,?)",
                    (t["id"], t["handle"], t["text"],
                     t["created_at"].isoformat() if t["created_at"] else "",
                     datetime.now(timezone.utc).isoformat()))
    con.commit()
    return new, seen


# ----------------------------------------------------------------------------
# 第一层：时间窗；第三层：噪音过滤
# ----------------------------------------------------------------------------
def layer_time_window(tweets, hours):
    now = datetime.now(timezone.utc)
    lo, out = [], []
    for t in tweets:
        if t["created_at"] and t["created_at"] >= now - timedelta(hours=hours):
            lo.append(t)
        else:
            out.append(t)
    return lo, out


def layer_noise(tweets, cfg):
    """过滤明确噪音：过短、纯打卡问候、转推（如禁用）、回复（如禁用）。"""
    kept, noise = [], []
    inc_replies = cfg.get("include_replies", False)
    inc_rt = cfg.get("include_retweets", False)
    for t in tweets:
        txt = t["text"].strip()
        reasons = []
        if not inc_replies and t.get("is_reply"):
            reasons.append("回复")
        if not inc_rt and t.get("is_retweet"):
            reasons.append("转推")
        if len(txt) < cfg["min_chars"]:
            reasons.append("过短")
        has_noise = any(k.lower() in txt.lower() for k in cfg["noise_keywords"])
        if has_noise and len(txt) < 40:
            reasons.append("打卡/问候")
        if reasons:
            noise.append((t, reasons))
        else:
            kept.append(t)
    return kept, noise


# ----------------------------------------------------------------------------
# 第四层：汇总输出（只做抓取消息，不做发推/包装）
# ----------------------------------------------------------------------------
def summarize(kept, cfg):
    lines = []
    for t in kept:
        when = t["created_at"].strftime("%Y-%m-%d %H:%M UTC") if t["created_at"] else "未知时间"
        lines.append(f"- @{t['handle']} · {when}\n  {t['text']}\n  {t['url']}")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# 编排
# ----------------------------------------------------------------------------
def run(cfg, demo=False, single_handle=None):
    con = init_db(cfg["db_path"])
    report = {"accounts": [], "collected": []}

    handles = [single_handle] if single_handle else cfg["accounts"]

    for handle in handles:
        tweets = load_demo(handle) if demo else fetch_tweets(handle, cfg)
        if not demo:
            time.sleep(cfg["request_delay"])  # 平滑请求间隔，降低频控风险

        in_window, old = layer_time_window(tweets, cfg["time_window_hours"])
        new, seen = dedup(con, in_window)
        kept, noise = layer_noise(new, cfg)
        report["collected"].extend(kept)
        report["accounts"].append({
            "handle": handle,
            "fetched": len(tweets),
            "in_window": len(in_window),
            "deduped_old": seen,
            "kept": len(kept),
            "noise": len(noise),
        })

    report["briefing"] = summarize(report["collected"], cfg)
    con.close()
    return report


def load_demo(handle):
    """离线样本：覆盖过滤链各分支（在窗/保留、在窗/噪音、旧闻、重复）。按账号分桶。"""
    path = os.path.join(os.path.dirname(__file__), "sample_feed.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        feed = json.load(f)
    items = feed.get(handle, []) if isinstance(feed, dict) else feed
    now = datetime.now(timezone.utc)
    out = []
    for item in items:
        created = now - timedelta(minutes=item.get("offset_min", 0))
        out.append({
            "id": item["id"],
            "handle": handle,
            "text": item["text"].strip(),
            "created_at": created,
            "url": f"https://x.com/{handle}",
            "is_reply": False,
            "is_retweet": False,
        })
    return out


def print_report(r):
    print("=" * 64)
    print("消息抓取结果")
    print("=" * 64)
    for a in r["accounts"]:
        print(f"@{a['handle']}: 抓取 {a['fetched']} | 在窗 {a['in_window']} "
              f"| 去重复用 {a['deduped_old']} | 保留 {a['kept']} | 噪音 {a['noise']}")
    print("-" * 64)
    print(f"本周期共保留 {len(r['collected'])} 条消息")
    if r["briefing"]:
        print(r["briefing"])
    else:
        print("（无符合时间窗与噪音过滤条件的消息）")
    print("=" * 64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="离线跑样本，验证过滤链")
    ap.add_argument("--handle", help="只处理单个账号")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    print_report(run(cfg, demo=args.demo, single_handle=args.handle))


if __name__ == "__main__":
    main()
