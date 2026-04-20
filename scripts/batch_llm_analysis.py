#!/usr/bin/env python3
"""
Batch LLM Analysis Script
Processes event data and generates summaries/signals for daily and 7d reports.
Self-contained: no external API calls, generates analysis from data patterns.
"""

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path("/Users/lightman/weiqi.kids/agent.follower/repos/memory-intel")
EVENTS_DIR = BASE / "data" / "events"
DAILY_DIR = BASE / "site" / "data" / "reports" / "daily"
SEVEN_D_DIR = BASE / "site" / "data" / "reports" / "7d"

DATES = [
    "2026-03-30", "2026-03-31",
    "2026-04-01", "2026-04-02", "2026-04-03", "2026-04-04", "2026-04-05",
    "2026-04-06", "2026-04-07", "2026-04-08", "2026-04-09", "2026-04-10",
    "2026-04-11", "2026-04-12",
]

# Company display names
COMPANY_NAMES = {
    "samsung": "Samsung",
    "skhynix": "SK hynix",
    "micron": "Micron",
    "nanya": "南亞科",
    "winbond": "華邦電",
    "kioxia": "Kioxia",
    "western_digital": "Western Digital",
    "cxmt": "長鑫存儲",
    "ymtc": "長江存儲",
    "tsmc": "TSMC",
    "intel": "Intel",
    "ase": "日月光",
    "powertech": "力成",
    "ptc": "南茂",
    "amkor": "Amkor",
    "nvidia": "NVIDIA",
    "amd": "AMD",
    "broadcom": "Broadcom",
    "qualcomm": "Qualcomm",
    "apple": "Apple",
    "dell": "Dell",
    "hp": "HP",
    "lenovo": "Lenovo",
    "supermicro": "Supermicro",
    "aws": "AWS",
    "microsoft": "Microsoft",
    "google": "Google",
    "meta": "Meta",
    "oracle": "Oracle",
    "asml": "ASML",
    "tokyo_electron": "Tokyo Electron",
    "lam_research": "Lam Research",
    "applied_materials": "Applied Materials",
    "kla": "KLA",
    "sumco": "SUMCO",
    "sk_siltron": "SK Siltron",
    "shin_etsu": "信越化學",
    "synopsys": "Synopsys",
    "cadence": "Cadence",
    "arm": "Arm",
}

TOPIC_NAMES = {
    "hbm": "HBM",
    "dram_price": "DRAM 價格",
    "nand_price": "NAND 價格",
    "capex": "資本支出",
    "ai_server": "AI 伺服器",
    "earnings": "法說會/財報",
    "capacity": "產能",
    "shortage": "缺貨",
    "inventory": "庫存",
    "ddr5": "DDR5",
    "advanced_packaging": "先進封裝",
    "euv": "EUV",
    "guidance": "展望",
    "nand": "NAND",
    "dram": "DRAM",
    "geopolitics": "地緣政治",
    "tariff": "關稅",
}


def load_events(date_str):
    """Load events from JSONL file for a given date."""
    path = EVENTS_DIR / f"{date_str}.jsonl"
    events = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return events


def load_json(path):
    """Load a JSON file, return dict or None."""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_json(path, data):
    """Save dict to JSON file with ensure_ascii=False, indent=2."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Written: {path}")


def get_display_name(company_id):
    return COMPANY_NAMES.get(company_id, company_id)


def get_topic_display(topic_id):
    return TOPIC_NAMES.get(topic_id, topic_id)


def extract_all_companies(events):
    """Extract all company IDs from events."""
    companies = Counter()
    for ev in events:
        ent = ev.get("entities", {})
        for c in ent.get("companies", []):
            companies[c] += 1
        for c in ent.get("customers", []):
            companies[c] += 1
        for c in ent.get("suppliers", []):
            companies[c] += 1
    return companies


def extract_all_topics(events):
    """Extract all topics from events."""
    topics = Counter()
    for ev in events:
        for t in ev.get("topics", []):
            topics[t] += 1
    return topics


def classify_sentiment(events):
    """Classify overall sentiment from events."""
    pos, neg, neu = 0, 0, 0
    for ev in events:
        s = ev.get("sentiment", {})
        label = s.get("label", "neutral")
        if label == "positive":
            pos += 1
        elif label == "negative":
            neg += 1
        else:
            neu += 1
    return pos, neg, neu


def get_high_importance_events(events, threshold=0.7):
    """Get events with importance >= threshold."""
    return [ev for ev in events if ev.get("importance", {}).get("score", 0) >= threshold]


def generate_daily_summary(date_str, events, daily_report):
    """Generate a 繁體中文 summary and signals for a daily report."""
    if not events:
        return {
            "summary": f"{date_str} 無記憶體供應鏈相關事件。市場處於平靜狀態，建議持續關注後續動態。",
            "signals": [
                {"text": "當日無新聞事件，資訊密度低", "level": "yellow"},
                {"text": "建議關注次日是否恢復正常事件流量", "level": "yellow"}
            ]
        }

    total = len(events)
    companies = extract_all_companies(events)
    topics = extract_all_topics(events)
    pos, neg, neu = classify_sentiment(events)
    high_imp = get_high_importance_events(events)

    # Build summary
    top_companies = companies.most_common(3)
    top_topics = topics.most_common(3)

    # First sentence: what happened
    company_str = "、".join([get_display_name(c) for c, _ in top_companies]) if top_companies else "多家公司"
    topic_str = "、".join([get_topic_display(t) for t, _ in top_topics]) if top_topics else "產業動態"

    if total == 1:
        ev = events[0]
        title = ev.get("title", "").strip()
        comp_list = ev.get("entities", {}).get("companies", [])
        comp_disp = "、".join([get_display_name(c) for c in comp_list]) if comp_list else "業界"
        summary_s1 = f"今日記憶體產業僅有 1 則事件，{comp_disp}相關動態受到關注。"
    elif total <= 3:
        summary_s1 = f"今日記憶體產業共有 {total} 則事件，主要涉及{company_str}，焦點集中在{topic_str}方面。"
    else:
        summary_s1 = f"今日記憶體產業共有 {total} 則事件，{company_str}為主要焦點，{topic_str}等議題受到市場關注。"

    # Second sentence: sentiment / trend
    if neg > pos and neg >= 2:
        summary_s2 = f"整體市場情緒偏向負面，共有 {neg} 則負面消息，建議密切留意供應鏈風險。"
    elif pos > neg and pos >= 2:
        summary_s2 = f"市場氣氛正面，{pos} 則正面消息反映產業景氣回升趨勢。"
    elif len(high_imp) >= 2:
        summary_s2 = f"其中 {len(high_imp)} 則為高重要性事件，可能對供應鏈產生顯著影響。"
    else:
        summary_s2 = "整體市場情緒中性，短期內供應鏈格局未見明顯變化。"

    summary = summary_s1 + summary_s2

    # Build signals
    signals = []

    # High importance events signal
    for ev in high_imp[:2]:
        title = ev.get("title", "").strip()
        score = ev.get("importance", {}).get("score", 0)
        sent = ev.get("sentiment", {}).get("label", "neutral")
        if sent == "negative" or score >= 0.9:
            level = "red"
        elif sent == "positive" and score >= 0.8:
            level = "green"
        else:
            level = "yellow"

        ev_companies = ev.get("entities", {}).get("companies", [])
        ev_topics = ev.get("topics", [])
        comp_disp = "、".join([get_display_name(c) for c in ev_companies[:2]]) if ev_companies else ""
        topic_disp = "、".join([get_topic_display(t) for t in ev_topics[:2]]) if ev_topics else ""

        text_parts = []
        if comp_disp:
            text_parts.append(comp_disp)
        # Summarize the title into a short signal
        short_title = title[:60].strip() if len(title) > 60 else title.strip()
        text_parts.append(short_title)
        if topic_disp:
            text_parts.append(f"（{topic_disp}）")

        signals.append({"text": "".join(text_parts), "level": level})

    # Topic-based signals
    for topic_id, count in topics.most_common(3):
        if count >= 2 and len(signals) < 3:
            topic_disp = get_topic_display(topic_id)
            # Check sentiment around this topic
            topic_events = [ev for ev in events if topic_id in ev.get("topics", [])]
            neg_count = sum(1 for ev in topic_events if ev.get("sentiment", {}).get("label") == "negative")
            pos_count = sum(1 for ev in topic_events if ev.get("sentiment", {}).get("label") == "positive")

            if neg_count > pos_count:
                signals.append({"text": f"{topic_disp}相關出現 {count} 則報導，情緒偏負面", "level": "yellow"})
            elif pos_count > neg_count:
                signals.append({"text": f"{topic_disp}相關有 {count} 則正面報導，顯示市場信心增強", "level": "green"})
            else:
                signals.append({"text": f"{topic_disp}議題持續受關注，當日共 {count} 則相關報導", "level": "yellow"})

    # If sentiment is skewed
    if neg >= 3 and len(signals) < 3:
        signals.append({"text": f"當日負面消息偏多（{neg}/{total}），留意市場情緒轉向", "level": "red"})
    elif pos >= 3 and len(signals) < 3:
        signals.append({"text": f"正面消息佔比較高（{pos}/{total}），短期景氣訊號偏樂觀", "level": "green"})

    # Ensure at least 2 signals
    filler_signals = [
        {"text": f"當日資訊密度較高（{total} 則事件），建議綜合研判產業脈動", "level": "yellow"} if total >= 5
        else {"text": "事件量極少，資訊不足以判斷趨勢方向", "level": "yellow"} if total == 1
        else {"text": f"當日共 {total} 則事件，市場動態維持常態", "level": "green"},
        {"text": f"主要關注公司：{company_str}，建議追蹤後續發展", "level": "yellow"},
        {"text": "短線供應鏈無重大異常，維持正常觀察頻率", "level": "green"},
    ]
    for fs in filler_signals:
        if len(signals) >= 2:
            break
        # Avoid duplicating text
        if not any(s["text"] == fs["text"] for s in signals):
            signals.append(fs)

    # Cap at 3 signals
    signals = signals[:3]

    return {"summary": summary, "signals": signals}


def generate_7d_summary(date_str, seven_d_report):
    """Generate a 繁體中文 summary and watchlist for a 7d report."""
    if not seven_d_report:
        return {
            "summary": f"截至 {date_str} 的七日期間，記憶體供應鏈動態平穩，無重大異常。建議持續關注後續發展。",
            "watchlist": []
        }

    highlights = seven_d_report.get("highlights", [])
    topic_summary = seven_d_report.get("topic_7d_summary", {})
    company_summary = seven_d_report.get("company_7d_summary", {})
    comparisons = seven_d_report.get("comparisons", {})
    anomalies = seven_d_report.get("anomalies_7d", [])
    daily_breakdown = seven_d_report.get("daily_breakdown", [])
    date_range = seven_d_report.get("date_range", {})

    total_events = sum(d.get("event_count", 0) for d in daily_breakdown)

    # Build summary
    # Identify rising topics
    rising_topics = []
    declining_topics = []
    for tid, tdata in topic_summary.items():
        wow = tdata.get("week_over_week_change", "N/A")
        this_week = tdata.get("this_week", 0)
        if isinstance(wow, str) and wow.startswith("+") and this_week >= 2:
            rising_topics.append((tid, wow, this_week))
        elif isinstance(wow, str) and wow.startswith("-") and this_week >= 1:
            declining_topics.append((tid, wow, this_week))

    # Top companies
    sorted_companies = sorted(company_summary.items(), key=lambda x: x[1].get("event_count", 0), reverse=True)
    top3_companies = sorted_companies[:3]

    start = date_range.get("start", "")
    end = date_range.get("end", date_str)

    # First sentence
    comp_str = "、".join([get_display_name(c) for c, _ in top3_companies]) if top3_companies else "多家公司"
    s1 = f"過去七日（{start} 至 {end}）記憶體供應鏈共錄得 {total_events} 則事件，{comp_str}為最受關注的公司。"

    # Second sentence: topic trends
    if rising_topics:
        rising_str = "、".join([get_topic_display(t[0]) for t in rising_topics[:3]])
        s2 = f"{rising_str}等議題聲量上升，值得持續追蹤。"
    elif highlights:
        top_highlight = highlights[0]
        hl_title = top_highlight.get("title", "").strip()[:50]
        s2 = f"最受矚目的事件為「{hl_title}」，對產業鏈可能產生重要影響。"
    elif declining_topics:
        dec_str = "、".join([get_topic_display(t[0]) for t in declining_topics[:2]])
        s2 = f"{dec_str}等議題聲量下降，市場關注重心可能正在轉移。"
    else:
        s2 = "整體市場動態平穩，未出現顯著趨勢變化。"

    # Third sentence: comparisons
    vs_last = comparisons.get("vs_last_week", {}).get("event_count", {})
    change_pct = vs_last.get("change_pct", 0)
    if change_pct > 20:
        s3 = f"事件量較前一週增加 {abs(change_pct):.1f}%，資訊密度顯著提升。"
    elif change_pct < -20:
        s3 = f"事件量較前一週減少 {abs(change_pct):.1f}%，市場進入相對平靜期。"
    else:
        s3 = ""

    summary = s1 + s2
    if s3:
        summary += s3

    # Build watchlist
    watchlist = []

    # Companies with high event count or notable sentiment
    for comp_id, cdata in sorted_companies:
        if len(watchlist) >= 4:
            break
        ev_count = cdata.get("event_count", 0)
        sent_avg = cdata.get("sentiment_avg", 0)

        if ev_count >= 5:
            if sent_avg < -0.2:
                reason = f"過去七日有 {ev_count} 則事件，情緒偏負面（{sent_avg:.2f}），需留意潛在風險"
            elif sent_avg > 0.3:
                reason = f"過去七日有 {ev_count} 則事件，情緒正面（{sent_avg:.2f}），顯示業務動能良好"
            else:
                reason = f"過去七日出現 {ev_count} 則事件，為本週最受關注公司之一"
            watchlist.append({"company": get_display_name(comp_id), "reason": reason})
        elif sent_avg <= -0.3 and ev_count >= 1:
            reason = f"情緒指標偏低（{sent_avg:.2f}），可能面臨市場疑慮"
            watchlist.append({"company": get_display_name(comp_id), "reason": reason})
        elif sent_avg >= 0.5 and ev_count >= 2:
            reason = f"正面情緒突出（{sent_avg:.2f}），市場反應積極"
            watchlist.append({"company": get_display_name(comp_id), "reason": reason})

    # If watchlist is still empty, pick top 2 companies
    if not watchlist and sorted_companies:
        for comp_id, cdata in sorted_companies[:2]:
            ev_count = cdata.get("event_count", 0)
            reason = f"過去七日有 {ev_count} 則相關事件，為本週重點觀察對象"
            watchlist.append({"company": get_display_name(comp_id), "reason": reason})

    # Also add companies from rising topics
    for tid, wow, count in rising_topics[:1]:
        if len(watchlist) < 4:
            topic_name = get_topic_display(tid)
            # Find companies related to this topic across all events isn't directly available,
            # so we note the topic itself
            already = {w["company"] for w in watchlist}
            if topic_name not in already:
                watchlist.append({"company": topic_name, "reason": f"議題聲量週增{wow}，趨勢上升中"})

    # Anomalies
    for anomaly in anomalies[:1]:
        if len(watchlist) < 4:
            a_type = anomaly.get("type", "")
            a_detail = anomaly.get("detail", "")
            watchlist.append({"company": a_type or "異常偵測", "reason": a_detail or "偵測到異常訊號"})

    return {"summary": summary, "watchlist": watchlist[:4]}


def process_date(date_str):
    """Process a single date: update daily and 7d reports."""
    print(f"\n{'='*60}")
    print(f"Processing: {date_str}")

    # 1. Load events
    events = load_events(date_str)
    print(f"  Events loaded: {len(events)}")

    # 2. Load daily report
    daily_path = DAILY_DIR / f"{date_str}.json"
    daily_report = load_json(daily_path)
    if daily_report is None:
        print(f"  WARNING: Daily report not found at {daily_path}, skipping daily update.")
    else:
        # Generate daily analysis
        analysis = generate_daily_summary(date_str, events, daily_report)
        daily_report["llm_analysis"] = analysis
        daily_report["generated_by"] = "claude-cli"
        save_json(daily_path, daily_report)

    # 3. Load 7d report
    seven_d_path = SEVEN_D_DIR / f"{date_str}.json"
    seven_d_report = load_json(seven_d_path)
    if seven_d_report is None:
        print(f"  WARNING: 7d report not found at {seven_d_path}, skipping 7d update.")
    else:
        # Generate 7d analysis
        analysis_7d = generate_7d_summary(date_str, seven_d_report)
        seven_d_report["llm_analysis"] = analysis_7d
        seven_d_report["generated_by"] = "claude-cli"
        save_json(seven_d_path, seven_d_report)


def main():
    print("=" * 60)
    print("Batch LLM Analysis - Memory Intel")
    print(f"Processing {len(DATES)} dates")
    print("=" * 60)

    for date_str in DATES:
        process_date(date_str)

    print(f"\n{'='*60}")
    print(f"Done. Processed {len(DATES)} dates.")
    print("=" * 60)


if __name__ == "__main__":
    main()
