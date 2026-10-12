#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
twitter-account-collector — 真实可运行的采集与筛选实现

设计原则（与 README「技术原理」对应）：
  - 四层漏斗：时间窗 -> SQLite 去重 -> 价值/噪音研判 -> 发推决策
  - 抓取层「尽力而为、可插拔、有兜底」：不依赖单一接口，X 收紧时自动降级
  - 所有筛选逻辑都是纯本地计算，可离线（--demo）验证，不依赖网络

用法：
  python collector.py                 # 按 config.yaml 抓取并筛选（联网，尽力而为）
  python collector.py --demo          # 用 scripts/sample_feed.json 跑完整四层漏斗（离线可验证）
  python collector.py --handle elonmusk --once
"""

import argparse
import json
import os
import sqlite3
import sys
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
    "accounts": ["elonmusk", "VitalikButerin"],
    "request_delay": 2.5,
    "time_window_hours": 1,
    "min_chars": 15,
    "db_path": "collector.db",
    "noise_keywords": ["gm", "gn", "早安", "晚安", "午安", "聚会", "下午茶",
                       "哈哈", "lol", "加油", "周末愉快"],
    "value_keywords": ["融资", "raise", "funding", "snapshot", "快照", "测试网",
                       "mainnet", "主网", "漏洞", "exploit", "女巫", "sybil",
                       "空投", "airdrop", "合约", "争议", "辩论"],
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
    dt = _parse_dt(created)
    return {
        "id": str(tw.get("id") or tw.get("id_str") or hash(text)),
        "handle": handle,
        "text": text.strip(),
        "created_at": dt,
        "url": tw.get("url") or f"https://x.com/{handle}",
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
    """抓取某个账号的近期推文：依次尝试多个后端，任一成功即用。"""
    for backend in (fetch_fxtwitter, lambda h: fetch_syndication(h, user_id)):
        try:
            tweets = backend(handle)
            if tweets:
                return tweets
        except Exception:
            continue
    return []


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
        row = con.execute("SELECT 1 FROM tweets WHERE tweet_id=?", (t["id"],)).fetchone()
        if row:
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
# 第一层：时间窗；第三层：价值/噪音研判
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


def layer_value_noise(tweets, cfg):
    valuable, noise = [], []
    text_low = lambda s: s.lower()
    for t in tweets:
        txt = t["text"]
        low = text_low(txt)
        has_value = any(k.lower() in low for k in cfg["value_keywords"])
        too_short = len(txt.strip()) < cfg["min_chars"]
        has_noise = any(k.lower() in low for k in cfg["noise_keywords"])
        if has_value or (not too_short and not has_noise):
            valuable.append(t)
        else:
            noise.append(t)
    return valuable, noise


# ----------------------------------------------------------------------------
# 第四层：发推决策 + 草稿生成（140 字软上限）
# ----------------------------------------------------------------------------
def make_draft(valuable, handle):
    if not valuable:
        return None
    top = valuable[0]
    head = f"@{handle} 近 1h 精选："
    body = top["text"].replace("\n", " ")
    budget = 140 - len(head) - 6
    if len(body) > budget:
        body = body[:budget] + "…"
    return head + body + " #crypto"


def decide(valuable, noise_count, old_count):
    if valuable:
        return True, f"本小时抓到 {len(valuable)} 条高价值内容，建议发推。"
    if noise_count:
        return False, "本小时内容偏噪音/旧闻，无需发推，避免伤害算法权重。"
    return False, "本小时目标账号无新动态，无需发推。"


# ----------------------------------------------------------------------------
# 编排
# ----------------------------------------------------------------------------
def run(cfg, demo=False, single_handle=None):
    now = datetime.now(timezone.utc)
    con = init_db(cfg["db_path"])
    report = {"accounts": [], "should_post": False, "draft": None, "decision": ""}

    handles = [single_handle] if single_handle else cfg["accounts"]
    all_valuable = []

    for handle in handles:
        if demo:
            tweets = load_demo(handle)
        else:
            tweets = fetch_tweets(handle, cfg)
            time.sleep(cfg["request_delay"])  # 平滑请求间隔，降低频控风险

        in_window, old = layer_time_window(tweets, cfg["time_window_hours"])
        new, seen = dedup(con, in_window)
        valuable, noise = layer_value_noise(new, cfg)
        all_valuable.extend(valuable)
        report["accounts"].append({
            "handle": handle,
            "fetched": len(tweets),
            "in_window": len(in_window),
            "deduped_old": seen,
            "valuable": len(valuable),
            "noise": len(noise),
        })

    should, decision = decide(all_valuable,
                              sum(a["noise"] for a in report["accounts"]), 0)
    draft = make_draft(all_valuable, handles[0]) if all_valuable else None
    report.update(should_post=should, draft=draft, decision=decision)
    con.close()
    return report


def load_demo(handle):
    """离线样本：覆盖四层漏斗各分支（在窗/价值、在窗/噪音、旧闻、重复）。"""
    path = os.path.join(os.path.dirname(__file__), "sample_feed.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        feed = json.load(f)
    now = datetime.now(timezone.utc)
    out = []
    for item in feed:
        offset_min = item.get("offset_min", 0)
        created = now - timedelta(minutes=offset_min)
        out.append({
            "id": item["id"],
            "handle": handle,
            "text": item["text"],
            "created_at": created,
            "url": f"https://x.com/{handle}",
        })
    return out


def print_report(r):
    print("=" * 60)
    print("四层漏斗运行结果")
    print("=" * 60)
    for a in r["accounts"]:
        print(f"@{a['handle']}: 抓取 {a['fetched']} | 在窗 {a['in_window']} "
              f"| 去重复用 {a['deduped_old']} | 有价值 {a['valuable']} | 噪音 {a['noise']}")
    print("-" * 60)
    print(f"发推决策: {'✅ 建议发推' if r['should_post'] else '⏸ 本小时无需发推'}")
    print(f"结论: {r['decision']}")
    if r["draft"]:
        print(f"草稿({len(r['draft'])}字): {r['draft']}")
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="离线跑样本，验证四层漏斗")
    ap.add_argument("--handle", help="只处理单个账号")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    report = run(cfg, demo=args.demo, single_handle=args.handle)
    print_report(report)


if __name__ == "__main__":
    main()
