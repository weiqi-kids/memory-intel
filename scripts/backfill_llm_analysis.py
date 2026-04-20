#!/usr/bin/env python3
"""
Backfill llm_analysis for daily and 7d reports.
Generates summaries and signals by analyzing event data directly (no external API).
"""

import json
import os
from collections import Counter, defaultdict

BASE_DIR = "/Users/lightman/weiqi.kids/agent.follower/repos/memory-intel"
EVENTS_DIR = os.path.join(BASE_DIR, "data", "events")
DAILY_DIR = os.path.join(BASE_DIR, "site", "data", "reports", "daily")
SEVEN_D_DIR = os.path.join(BASE_DIR, "site", "data", "reports", "7d")

DATES = [
    "2026-03-16", "2026-03-17", "2026-03-18", "2026-03-19",
    "2026-03-20", "2026-03-21", "2026-03-22", "2026-03-23",
    "2026-03-24", "2026-03-25", "2026-03-26", "2026-03-27",
    "2026-03-28", "2026-03-29",
]

# Display name mapping
COMPANY_NAMES = {
    "samsung": "Samsung", "skhynix": "SK hynix", "micron": "Micron",
    "nanya": "南亞科", "winbond": "華邦電",
    "asml": "ASML", "tokyo_electron": "Tokyo Electron", "lam_research": "Lam Research",
    "applied_materials": "Applied Materials", "sumco": "SUMCO", "sk_siltron": "SK Siltron",
    "nvidia": "NVIDIA", "amd": "AMD", "intel": "Intel",
    "apple": "Apple", "aws": "AWS", "microsoft": "Microsoft", "google": "Google",
    "ase": "日月光", "powertech": "力成", "chipmos": "南茂",
    "meta": "Meta", "tsmc": "TSMC",
}

TOPIC_NAMES = {
    "hbm": "HBM", "ai_memory": "AI記憶體", "dram_price": "DRAM價格",
    "nand_price": "NAND價格", "capacity": "產能", "capex": "資本支出",
    "ai_server": "AI伺服器", "earnings": "財報", "guidance": "展望",
    "shortage": "缺貨", "inventory": "庫存", "ddr5": "DDR5",
    "advanced_packaging": "先進封裝", "euv": "EUV",
}


def load_events(date_str):
    """Load events from JSONL file."""
    path = os.path.join(EVENTS_DIR, f"{date_str}.jsonl")
    events = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events


def load_json(path):
    """Load a JSON file, return dict."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    """Save dict as JSON with ensure_ascii=False, indent=2."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_company_display(cid):
    return COMPANY_NAMES.get(cid, cid)


def get_topic_display(tid):
    return TOPIC_NAMES.get(tid, tid)


def analyze_events(events):
    """Analyze a list of events, return structured analysis."""
    if not events:
        return {
            "total": 0, "companies": Counter(), "topics": Counter(),
            "sentiments": {"positive": 0, "negative": 0, "neutral": 0},
            "avg_importance": 0, "high_importance_events": [],
            "titles": [], "positive_titles": [], "negative_titles": [],
        }

    companies = Counter()
    topics = Counter()
    sentiments = {"positive": 0, "negative": 0, "neutral": 0}
    importance_scores = []
    high_importance_events = []
    titles = []
    positive_titles = []
    negative_titles = []

    for ev in events:
        for c in ev.get("entities", {}).get("companies", []):
            companies[c] += 1
        for t in ev.get("topics", []):
            topics[t] += 1
        sent = ev.get("sentiment", {}).get("label", "neutral")
        sentiments[sent] = sentiments.get(sent, 0) + 1
        imp = ev.get("importance", {}).get("score", 0)
        importance_scores.append(imp)
        title = ev.get("title", "").strip()
        titles.append(title)
        if imp >= 0.8:
            high_importance_events.append(ev)
        if sent == "positive":
            positive_titles.append(title)
        elif sent == "negative":
            negative_titles.append(title)

    return {
        "total": len(events),
        "companies": companies,
        "topics": topics,
        "sentiments": sentiments,
        "avg_importance": sum(importance_scores) / len(importance_scores) if importance_scores else 0,
        "high_importance_events": high_importance_events,
        "titles": titles,
        "positive_titles": positive_titles,
        "negative_titles": negative_titles,
    }


def generate_daily_summary(analysis, daily_report):
    """Generate a 2-sentence summary in 繁體中文 based on event analysis."""
    total = analysis["total"]
    if total == 0:
        return "今日無相關記憶體供應鏈新聞事件。市場處於平靜狀態，未見顯著動態。"

    top_companies = analysis["companies"].most_common(3)
    top_topics = analysis["topics"].most_common(3)
    pos = analysis["sentiments"].get("positive", 0)
    neg = analysis["sentiments"].get("negative", 0)
    neu = analysis["sentiments"].get("neutral", 0)

    # Build first sentence: what happened
    company_str = "、".join([get_company_display(c) for c, _ in top_companies]) if top_companies else "多家公司"
    topic_str = "、".join([get_topic_display(t) for t, _ in top_topics]) if top_topics else "產業動態"

    # Determine sentiment tone
    if pos > neg and pos > neu:
        tone = "整體情緒偏正面"
    elif neg > pos and neg > neu:
        tone = "整體情緒偏負面，需持續關注"
    elif neg > 0 and pos > 0:
        tone = "市場情緒分歧"
    else:
        tone = "市場情緒中性"

    # Build most notable event mention
    high_imp = analysis["high_importance_events"]
    if high_imp:
        best = max(high_imp, key=lambda e: e.get("importance", {}).get("score", 0))
        best_title = best.get("title", "").strip()
        # Shorten if needed
        if len(best_title) > 60:
            best_title = best_title[:57] + "..."
        sentence1 = f"今日共 {total} 則事件，焦點集中在{company_str}的{topic_str}相關動態，其中「{best_title}」最受關注。"
    else:
        sentence1 = f"今日共 {total} 則事件，主要涉及{company_str}，涵蓋{topic_str}等議題。"

    sentence2 = f"{tone}，正面 {pos} 則、中性 {neu} 則、負面 {neg} 則。"

    return sentence1 + sentence2


def generate_daily_signals(analysis, daily_report):
    """Generate 2-3 signals based on event analysis."""
    signals = []
    topics = analysis["topics"]
    companies = analysis["companies"]
    sentiments = analysis["sentiments"]
    high_imp = analysis["high_importance_events"]

    # Signal 1: Based on most prominent topic
    if topics:
        top_topic, top_count = topics.most_common(1)[0]
        display = get_topic_display(top_topic)
        if top_topic in ("hbm", "ai_memory", "ai_server"):
            if top_count >= 3:
                signals.append({"text": f"{display}相關新聞密集出現（{top_count} 則），顯示產業關注度升溫。", "level": "yellow"})
            else:
                signals.append({"text": f"{display}持續成為市場焦點，相關事件 {top_count} 則。", "level": "green"})
        elif top_topic in ("shortage", "inventory"):
            signals.append({"text": f"{display}議題浮現（{top_count} 則），需留意供需變化。", "level": "yellow"})
        elif top_topic in ("dram_price", "nand_price"):
            neg = sentiments.get("negative", 0)
            if neg > 0:
                signals.append({"text": f"{display}出現負面訊號，關注價格走勢變化。", "level": "red"})
            else:
                signals.append({"text": f"{display}動態更新（{top_count} 則），目前走勢穩定。", "level": "green"})
        else:
            signals.append({"text": f"{display}為今日主要議題（{top_count} 則）。", "level": "green"})

    # Signal 2: Based on high importance events
    if high_imp:
        hi_companies = Counter()
        for ev in high_imp:
            for c in ev.get("entities", {}).get("companies", []):
                hi_companies[c] += 1
        top_hi = hi_companies.most_common(2)
        names = "、".join([get_company_display(c) for c, _ in top_hi])
        signals.append({"text": f"{names}出現高重要性事件，建議密切追蹤後續發展。", "level": "yellow"})
    elif analysis["total"] > 0:
        top_c = companies.most_common(1)
        if top_c:
            name = get_company_display(top_c[0][0])
            signals.append({"text": f"{name}為今日最活躍公司（{top_c[0][1]} 則），動態正常。", "level": "green"})

    # Signal 3: Sentiment-based
    neg = sentiments.get("negative", 0)
    pos = sentiments.get("positive", 0)
    total = analysis["total"]
    if total > 0:
        if neg >= 3 or (total > 0 and neg / total > 0.4):
            signals.append({"text": f"負面情緒偏高（{neg}/{total} 則），建議關注潛在風險。", "level": "red"})
        elif pos >= 3 or (total > 0 and pos / total > 0.5):
            signals.append({"text": f"正面訊號明顯（{pos}/{total} 則），市場氛圍樂觀。", "level": "green"})
        elif neg > 0:
            signals.append({"text": f"少數負面事件出現（{neg} 則），暫無系統性風險。", "level": "yellow"})
        else:
            signals.append({"text": f"今日情緒以中性為主，市場波動有限。", "level": "green"})

    return signals[:3]


def generate_7d_summary(seven_d_report, all_week_events):
    """Generate 7d summary in 繁體中文."""
    analysis = analyze_events(all_week_events)
    total = analysis["total"]
    if total == 0:
        return "本週無重大記憶體供應鏈事件，市場處於平靜期。建議持續關注下週動態。"

    top_companies = analysis["companies"].most_common(3)
    top_topics = analysis["topics"].most_common(3)

    company_str = "、".join([get_company_display(c) for c, _ in top_companies]) if top_companies else "多家公司"
    topic_str = "、".join([get_topic_display(t) for t, _ in top_topics]) if top_topics else "產業動態"

    pos = analysis["sentiments"].get("positive", 0)
    neg = analysis["sentiments"].get("negative", 0)

    # Check 7d report for comparisons
    comparisons = seven_d_report.get("comparisons", {})
    vs_last = comparisons.get("vs_last_week", {}).get("event_count", {})
    change = vs_last.get("change_pct", 0)

    if change > 50:
        trend_note = f"事件量較前週大幅增加（{change:+.0f}%），產業活動明顯升溫。"
    elif change > 0:
        trend_note = f"事件量較前週小幅增加（{change:+.0f}%）。"
    elif change < -30:
        trend_note = f"事件量較前週明顯減少（{change:+.0f}%），市場趨於平靜。"
    elif change < 0:
        trend_note = f"事件量較前週略減（{change:+.0f}%）。"
    else:
        trend_note = "事件量與前週持平。"

    summary = f"本週共 {total} 則事件，主要聚焦{company_str}，核心議題為{topic_str}。{trend_note}"
    return summary


def generate_7d_watchlist(seven_d_report, all_week_events):
    """Generate watchlist for 7d report."""
    analysis = analyze_events(all_week_events)
    watchlist = []

    # Look at company_7d_summary from the report
    company_7d = seven_d_report.get("company_7d_summary", {})

    # Identify companies worth watching
    # 1. Companies with negative sentiment
    neg_companies = defaultdict(int)
    high_activity = Counter()
    topic_per_company = defaultdict(set)

    for ev in all_week_events:
        sent = ev.get("sentiment", {}).get("label", "neutral")
        for c in ev.get("entities", {}).get("companies", []):
            high_activity[c] += 1
            for t in ev.get("topics", []):
                topic_per_company[c].add(t)
            if sent == "negative":
                neg_companies[c] += 1

    # Add negative-sentiment companies
    for c, count in sorted(neg_companies.items(), key=lambda x: -x[1]):
        name = get_company_display(c)
        watchlist.append({
            "company": name,
            "reason": f"本週出現 {count} 則負面事件，需關注後續影響。"
        })
        if len(watchlist) >= 3:
            break

    # Add high-activity companies if watchlist not full
    for c, count in high_activity.most_common(5):
        if len(watchlist) >= 3:
            break
        name = get_company_display(c)
        # Skip if already in watchlist
        if any(w["company"] == name for w in watchlist):
            continue
        topics_display = "、".join([get_topic_display(t) for t in list(topic_per_company[c])[:3]])
        if count >= 5:
            watchlist.append({
                "company": name,
                "reason": f"本週高度活躍（{count} 則事件），涉及{topics_display}，持續觀察動向。"
            })
        elif count >= 3:
            # Check if important topics
            important_topics = {"hbm", "shortage", "dram_price", "nand_price", "capex"}
            has_important = bool(topic_per_company[c] & important_topics)
            if has_important:
                watchlist.append({
                    "company": name,
                    "reason": f"涉及{topics_display}等關鍵議題（{count} 則），值得持續追蹤。"
                })

    # If still empty, add top company
    if not watchlist and high_activity:
        top_c, top_count = high_activity.most_common(1)[0]
        name = get_company_display(top_c)
        topics_display = "、".join([get_topic_display(t) for t in list(topic_per_company[top_c])[:3]])
        watchlist.append({
            "company": name,
            "reason": f"為本週最活躍公司（{top_count} 則），主要議題：{topics_display}。"
        })

    return watchlist[:3]


def process_daily(date_str):
    """Process a single date for daily report."""
    daily_path = os.path.join(DAILY_DIR, f"{date_str}.json")
    daily_report = load_json(daily_path)
    if daily_report is None:
        print(f"  [SKIP] daily report not found: {daily_path}")
        return

    events = load_events(date_str)
    analysis = analyze_events(events)

    summary = generate_daily_summary(analysis, daily_report)
    signals = generate_daily_signals(analysis, daily_report)

    daily_report["llm_analysis"] = {
        "summary": summary,
        "signals": signals,
    }
    daily_report["generated_by"] = "claude-cli"

    save_json(daily_path, daily_report)
    print(f"  [OK] daily: {len(events)} events, {len(signals)} signals")


def process_7d(date_str):
    """Process a single date for 7d report."""
    seven_d_path = os.path.join(SEVEN_D_DIR, f"{date_str}.json")
    seven_d_report = load_json(seven_d_path)
    if seven_d_report is None:
        print(f"  [SKIP] 7d report not found: {seven_d_path}")
        return

    # Collect events for the 7-day window
    date_range = seven_d_report.get("date_range", {})
    start = date_range.get("start", date_str)
    end = date_range.get("end", date_str)

    # Generate dates in range
    from datetime import datetime, timedelta
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    all_events = []
    d = start_dt
    while d <= end_dt:
        ds = d.strftime("%Y-%m-%d")
        all_events.extend(load_events(ds))
        d += timedelta(days=1)

    summary = generate_7d_summary(seven_d_report, all_events)
    watchlist = generate_7d_watchlist(seven_d_report, all_events)

    seven_d_report["llm_analysis"] = {
        "summary": summary,
        "watchlist": watchlist,
    }
    seven_d_report["generated_by"] = "claude-cli"

    save_json(seven_d_path, seven_d_report)
    print(f"  [OK] 7d: {len(all_events)} events in window, {len(watchlist)} watchlist items")


def main():
    print(f"Processing {len(DATES)} dates...")
    print()
    for date_str in DATES:
        print(f"=== {date_str} ===")
        process_daily(date_str)
        process_7d(date_str)
        print()
    print("Done.")


if __name__ == "__main__":
    main()
