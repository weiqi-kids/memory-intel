#!/usr/bin/env python3
"""
Add llm_analysis and generated_by fields to daily and 7d report JSONs.
Generates summaries and signals/watchlist based on event data, topics, and companies.
No external API calls - all analysis logic is inline.
"""

import json
import os

BASE = "/Users/lightman/weiqi.kids/agent.follower/repos/memory-intel"

DATES = [
    "2025-10-29", "2025-12-17", "2026-01-05", "2026-01-22", "2026-01-28",
    "2026-02-02", "2026-02-05", "2026-02-25", "2026-03-03", "2026-03-05",
    "2026-03-11", "2026-03-12", "2026-03-13", "2026-03-14", "2026-03-15",
]

# ─── Topic display names ───
TOPIC_NAMES = {
    "hbm": "HBM",
    "dram_price": "DRAM 價格",
    "nand_price": "NAND 價格",
    "capacity": "產能",
    "capex": "資本支出",
    "ai_server": "AI 伺服器",
    "ai_memory": "AI 記憶體",
    "earnings": "財報",
    "outlook": "展望",
    "shortage": "缺貨",
    "inventory": "庫存",
    "ddr5": "DDR5",
    "advanced_packaging": "先進封裝",
    "euv": "EUV",
}

COMPANY_NAMES = {
    "samsung": "Samsung",
    "skhynix": "SK hynix",
    "micron": "Micron",
    "nanya": "南亞科",
    "winbond": "華邦電",
    "asml": "ASML",
    "tel": "東京威力",
    "lam_research": "Lam Research",
    "sumco": "SUMCO",
    "sk_siltron": "SK Siltron",
    "ase": "日月光",
    "ptl": "力成",
    "chipmos": "南茂",
    "nvidia": "NVIDIA",
    "amd": "AMD",
    "apple": "Apple",
    "aws": "AWS",
    "microsoft": "Microsoft",
    "google": "Google",
    "intel": "Intel",
    "tsmc": "TSMC",
    "cxmt": "CXMT",
    "hp": "HP",
    "dell": "Dell",
}


def read_events(date):
    """Read events from JSONL file. Returns list of event dicts."""
    path = os.path.join(BASE, "data", "events", f"{date}.jsonl")
    events = []
    if not os.path.exists(path):
        return events
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def topic_name(t):
    return TOPIC_NAMES.get(t, t)


def company_name(c):
    return COMPANY_NAMES.get(c, c)


def generate_daily_analysis(date, daily_data, events):
    """Generate summary and signals for a daily report."""
    top_events = daily_data.get("top_events", [])
    stats = daily_data.get("stats", {})
    total = stats.get("total_events", 0)
    top_topics = stats.get("top_topics", [])
    top_companies = stats.get("top_companies", [])
    topic_trends = daily_data.get("topic_trends", {})
    anomalies = daily_data.get("anomalies", [])
    sentiment_dist = stats.get("sentiment_distribution", {})

    # ─── Build summary ───
    if total == 0:
        summary = f"{date} 無記憶體產業相關事件。市場處於平靜狀態，無重大訊號。"
    else:
        # First sentence: overview of what happened
        topic_strs = [topic_name(t["id"]) for t in top_topics[:3]]
        company_strs = [company_name(c["id"]) for c in top_companies[:3]]

        parts1 = []
        if company_strs:
            parts1.append("、".join(company_strs))
        if topic_strs:
            parts1.append("、".join(topic_strs))

        if top_events:
            top_title = top_events[0].get("title", "").strip()
            # Truncate long titles
            if len(top_title) > 60:
                top_title = top_title[:57] + "..."
            first_sentence = f"今日共 {total} 則事件，焦點為{parts1[0] if parts1 else '記憶體產業'}相關動態：「{top_title}」。"
        else:
            first_sentence = f"今日共 {total} 則事件，涵蓋{'、'.join(parts1) if parts1 else '記憶體產業'}等領域。"

        # Second sentence: sentiment or trend
        pos = sentiment_dist.get("positive", 0)
        neg = sentiment_dist.get("negative", 0)
        neu = sentiment_dist.get("neutral", 0)

        if neg > pos:
            second_sentence = "整體情緒偏負面，需留意潛在風險。"
        elif pos > neg:
            second_sentence = "整體情緒偏正面，市場信心回溫。"
        else:
            # Look at topics for more detail
            if topic_strs:
                second_sentence = f"主要關注主題為{'、'.join(topic_strs)}，市場情緒中性。"
            else:
                second_sentence = "市場情緒中性，暫無明顯方向。"

        summary = first_sentence + second_sentence

    # ─── Build signals ───
    signals = []

    # Signal from top event importance
    for ev in top_events[:2]:
        imp = ev.get("importance_score", 0)
        title = ev.get("title", "").strip()
        if len(title) > 80:
            title = title[:77] + "..."
        topics = ev.get("topics", [])
        sentiment = ev.get("sentiment", {})
        sent_label = sentiment.get("label", "neutral")

        if imp >= 0.9:
            level = "red"
        elif imp >= 0.7:
            level = "yellow"
        else:
            level = "green"

        topic_note = ""
        if topics:
            topic_note = f"（{'、'.join(topic_name(t) for t in topics)}）"

        signals.append({
            "text": f"{title}{topic_note}",
            "level": level,
        })

    # Signal from topic trends
    for t_id, trend_info in topic_trends.items():
        trend = trend_info.get("trend", "")
        today_count = trend_info.get("today", 0)
        avg_7d = trend_info.get("7d_avg", 0)
        if today_count > 0 and t_id in ("shortage", "dram_price", "nand_price"):
            signals.append({
                "text": f"{topic_name(t_id)}話題出現 {today_count} 則，需持續關注供應鏈壓力。",
                "level": "yellow",
            })
        elif today_count > 0 and t_id in ("hbm", "ai_memory", "ai_server"):
            signals.append({
                "text": f"{topic_name(t_id)}持續受關注，技術演進帶動需求成長。",
                "level": "green",
            })

    # Ensure 2-3 signals
    if len(signals) == 0:
        signals.append({
            "text": "今日無重大異常訊號，產業動態平穩。",
            "level": "green",
        })
    if len(signals) == 1:
        if total > 0 and top_companies:
            signals.append({
                "text": f"{'、'.join(company_name(c['id']) for c in top_companies[:3])}為今日主要關注企業。",
                "level": "green",
            })
        else:
            signals.append({
                "text": "建議持續監控後續發展動態。",
                "level": "green",
            })

    # Cap at 3
    signals = signals[:3]

    return {
        "summary": summary,
        "signals": signals,
    }


def generate_7d_analysis(date, report_data, all_events_in_week):
    """Generate summary and watchlist for a 7d report."""
    highlights = report_data.get("highlights", [])
    topic_7d = report_data.get("topic_7d_summary", {})
    company_7d = report_data.get("company_7d_summary", {})
    comparisons = report_data.get("comparisons", {})
    date_range = report_data.get("date_range", {})
    start = date_range.get("start", "")
    end = date_range.get("end", date)
    daily_breakdown = report_data.get("daily_breakdown", [])

    total_events_week = sum(d.get("event_count", 0) for d in daily_breakdown)
    vs_last = comparisons.get("vs_last_week", {}).get("event_count", {})
    this_count = vs_last.get("this", total_events_week)
    last_count = vs_last.get("last", 0)
    change_pct = vs_last.get("change_pct", 0)

    # ─── Build summary ───
    if total_events_week == 0:
        summary = f"本週（{start} ~ {end}）記憶體產業動態較為平靜，未有重大事件發生。建議持續追蹤下週動態。"
    else:
        # Identify key topics and companies this week
        active_topics = []
        for t_id, info in topic_7d.items():
            count = info.get("this_week", 0)
            if count > 0:
                active_topics.append((t_id, count, info.get("sentiment_this_week", 0)))

        active_topics.sort(key=lambda x: -x[1])

        active_companies = []
        for c_id, info in company_7d.items():
            count = info.get("event_count", 0)
            if count > 0:
                active_companies.append((c_id, count, info.get("sentiment_avg", 0)))

        active_companies.sort(key=lambda x: -x[1])

        # First sentence
        topic_strs = [topic_name(t[0]) for t in active_topics[:3]]
        company_strs = [company_name(c[0]) for c in active_companies[:3]]

        if highlights:
            top_highlight = highlights[0].get("title", "").strip()
            if len(top_highlight) > 50:
                top_highlight = top_highlight[:47] + "..."
            first = f"本週（{start} ~ {end}）共 {this_count} 則事件，重點為「{top_highlight}」。"
        else:
            first = f"本週（{start} ~ {end}）共 {this_count} 則事件，主要涉及{'、'.join(topic_strs) if topic_strs else '記憶體產業'}。"

        # Second sentence: comparison and sentiment
        if change_pct > 50 and last_count > 0:
            second = f"事件量較上週增加 {change_pct:.0f}%，產業動態明顯升溫，需密切關注。"
        elif change_pct < -30 and last_count > 0:
            second = f"事件量較上週減少，市場進入觀望階段。"
        else:
            neg_companies = [c for c in active_companies if c[2] < -0.2]
            pos_companies = [c for c in active_companies if c[2] > 0.2]
            if neg_companies:
                second = f"{'、'.join(company_name(c[0]) for c in neg_companies[:2])}情緒偏負面，建議留意相關風險。"
            elif pos_companies:
                second = f"{'、'.join(company_name(c[0]) for c in pos_companies[:2])}表現正面，整體氣氛穩健。"
            elif topic_strs:
                second = f"{'、'.join(topic_strs)}為本週焦點話題。"
            else:
                second = "產業動態穩定，無異常訊號。"

        summary = first + second

    # ─── Build watchlist ───
    watchlist = []

    # Companies with negative sentiment
    for c_id, info in company_7d.items():
        sent = info.get("sentiment_avg", 0)
        count = info.get("event_count", 0)
        name = company_name(c_id)
        if sent < -0.2:
            watchlist.append({
                "company": name,
                "reason": f"本週情緒偏負面（{sent:.1f}），共 {count} 則相關事件，需關注後續發展。",
            })

    # Companies with high event count
    for c_id, info in company_7d.items():
        sent = info.get("sentiment_avg", 0)
        count = info.get("event_count", 0)
        name = company_name(c_id)
        if count >= 3 and name not in [w["company"] for w in watchlist]:
            if sent >= 0:
                reason = f"本週出現 {count} 則相關事件，為高關注企業，動態頻繁。"
            else:
                reason = f"本週出現 {count} 則相關事件且情緒偏負面，需特別關注。"
            watchlist.append({
                "company": name,
                "reason": reason,
            })

    # Topics that indicate supply chain pressure
    for t_id, info in topic_7d.items():
        count = info.get("this_week", 0)
        if count > 0 and t_id in ("shortage", "dram_price", "nand_price"):
            # Find related companies from highlights
            related = []
            for h in highlights:
                title = h.get("title", "")
                for cid, cname in COMPANY_NAMES.items():
                    if cname.lower() in title.lower() or cid in title.lower():
                        if cname not in [w["company"] for w in watchlist] and cname not in related:
                            related.append(cname)
            if related:
                for r in related[:1]:
                    watchlist.append({
                        "company": r,
                        "reason": f"受{topic_name(t_id)}議題影響，供應鏈壓力可能上升。",
                    })
            elif not watchlist:
                # Add a generic entry from the most active company
                for c_id, info2 in company_7d.items():
                    name = company_name(c_id)
                    if name not in [w["company"] for w in watchlist]:
                        watchlist.append({
                            "company": name,
                            "reason": f"{topic_name(t_id)}趨勢值得關注，可能影響供應鏈佈局。",
                        })
                        break

    # If still empty, add top companies
    if not watchlist:
        for c_id, info in company_7d.items():
            name = company_name(c_id)
            count = info.get("event_count", 0)
            watchlist.append({
                "company": name,
                "reason": f"本週有 {count} 則相關事件，建議持續追蹤動態。",
            })
            if len(watchlist) >= 2:
                break

    # If completely empty (no companies at all)
    if not watchlist:
        watchlist.append({
            "company": "記憶體產業",
            "reason": "本週無特定企業異常，建議持續追蹤整體產業走勢。",
        })

    # Cap at 3
    watchlist = watchlist[:3]

    return {
        "summary": summary,
        "watchlist": watchlist,
    }


def process_daily(date, events):
    """Process a single daily report."""
    path = os.path.join(BASE, "site", "data", "reports", "daily", f"{date}.json")
    if not os.path.exists(path):
        print(f"  [SKIP] daily/{date}.json not found")
        return False

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    analysis = generate_daily_analysis(date, data, events)
    data["llm_analysis"] = analysis
    data["generated_by"] = "claude-cli"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"  [OK] daily/{date}.json - summary: {analysis['summary'][:50]}...")
    return True


def process_7d(date, events):
    """Process a single 7d report."""
    path = os.path.join(BASE, "site", "data", "reports", "7d", f"{date}.json")
    if not os.path.exists(path):
        print(f"  [SKIP] 7d/{date}.json not found")
        return False

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    analysis = generate_7d_analysis(date, data, events)
    data["llm_analysis"] = analysis
    data["generated_by"] = "claude-cli"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"  [OK] 7d/{date}.json - summary: {analysis['summary'][:50]}...")
    return True


def main():
    print("=" * 60)
    print("Add LLM Analysis to Daily & 7d Reports")
    print("=" * 60)

    daily_count = 0
    weekly_count = 0

    for date in DATES:
        print(f"\n--- {date} ---")

        # Read events
        events = read_events(date)
        print(f"  Events: {len(events)} found")

        # Process daily report
        if process_daily(date, events):
            daily_count += 1

        # Process 7d report
        if process_7d(date, events):
            weekly_count += 1

    print(f"\n{'=' * 60}")
    print(f"Done! Processed {daily_count} daily reports, {weekly_count} 7d reports.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
