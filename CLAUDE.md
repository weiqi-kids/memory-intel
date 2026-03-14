# Memory Intel - 記憶體供應鏈情報追蹤

## 專案現況 (2026-03-14)

### ✅ 已完成

1. **股價抓取** - `scripts/fetch_stocks.py`
   - 增量抓取邏輯：每次補最新 + 往前 3 個月歷史
   - 18 檔股票，目前約 120 天資料
   - 資料來源：Yahoo Finance (yfinance)

2. **新聞爬蟲** - `fetchers/`
   - `samsung.py` - RSS 優先，Playwright 備用
   - `skhynix.py` - Playwright + AJAX 等待
   - `base.py` - Playwright 共用邏輯

3. **前端 Dashboard** - `site/index.html`
   - D3.js 視覺化
   - 繁體中文介面
   - 供應鏈圖（19 家公司、34 條關係）
   - 事件時間軸

4. **規則引擎** - `lib/`（新）
   - `matcher.py` - 關鍵字匹配（公司、主題）
   - `sentiment.py` - 情緒分析（含否定詞處理）
   - `scorer.py` - 重要性評分
   - `anomaly.py` - 異常偵測

5. **報告生成** - `scripts/`（新）
   - `fetch_news.py` - 整合抓取腳本（會自動呼叫後續流程）
   - `enrich_event.py` - 事件標註
   - `generate_metrics.py` - 每日指標
   - `detect_anomalies.py` - 異常偵測
   - `generate_daily.py` - 每日報告
   - `generate_7d_report.py` - 7 日報告
   - `sync_to_frontend.py` - 同步事件到前端
   - `update_baselines.py` - 更新歷史基準線

---

## 標準流程

```
fetch_news.py
    │
    ├─→ data/raw/{date}/news.jsonl    (原始抓取資料)
    │
    └─→ enrich_event.py
            │
            └─→ data/events/{date}.jsonl  (標準格式，唯一資料源)
                    │
            ┌───────┴───────────────┐
            │                       │
      sync_to_frontend.py     generate_metrics.py
            │                       │
            │                 data/metrics/{date}.json
            │                       │
            │                 generate_7d_report.py
            │                       │
            │                 reports/7d/{date}.json
            │                       │
      site/data/events.json   site/data/reports/7d/{date}.json
```

### 執行順序

1. `fetch_news.py` - 抓取所有公司新聞，輸出到 `data/raw/`
2. `enrich_event.py` - 標註事件，輸出到 `data/events/`（**唯一資料源**）
3. `generate_metrics.py` - 計算每日指標
4. `generate_7d_report.py` - 生成 7 日報告
5. `sync_to_frontend.py` - 同步事件到前端
6. `update_baselines.py` - 更新歷史基準線（最後執行）

**重要**：
- `data/events/*.jsonl` 是唯一的事件資料源
- 前端的 `site/data/events.json` 由 `sync_to_frontend.py` 生成
- 不要直接寫入 `site/data/events.json`

---

## 快速啟動

```bash
cd repos/memory-intel
source .venv/bin/activate

# 啟動本地伺服器 (port 6229)
python3 -m http.server 6229 -d site

# 瀏覽器開啟
open http://localhost:6229
```

## 抓取與處理資料

```bash
source .venv/bin/activate

# 1. 抓取新聞
python -m fetchers.samsung
python -m fetchers.skhynix

# 2. 標註事件
python scripts/enrich_event.py --date 2026-03-14 --input raw_news.json

# 3. 計算指標
python scripts/generate_metrics.py --date 2026-03-14

# 4. 偵測異常
python scripts/detect_anomalies.py --date 2026-03-14

# 5. 生成報告
python scripts/generate_daily.py --date 2026-03-14
python scripts/generate_7d_report.py --date 2026-03-14

# 6. 更新基準線（最後執行）
python scripts/update_baselines.py --date 2026-03-14
```

---

## 資料夾結構

```
memory-intel/
├── .venv/                      # Python 虛擬環境
├── lib/                        # 規則引擎
│   ├── __init__.py
│   ├── matcher.py              # 關鍵字匹配
│   ├── sentiment.py            # 情緒分析
│   ├── scorer.py               # 重要性評分
│   └── anomaly.py              # 異常偵測
│
├── scripts/                    # 執行腳本
│   ├── fetch_news.py           # 整合抓取（自動呼叫後續流程）
│   ├── fetch_stocks.py         # 股價抓取
│   ├── enrich_event.py         # 事件標註
│   ├── generate_metrics.py     # 每日指標
│   ├── detect_anomalies.py     # 異常偵測
│   ├── generate_daily.py       # 每日報告
│   ├── generate_7d_report.py   # 7 日報告
│   ├── sync_to_frontend.py     # 同步事件到前端
│   ├── update_baselines.py     # 更新基準線
│   └── serve.sh
│
├── configs/                    # 設定檔
│   ├── companies.yml           # 19 家公司 + 上下游關係
│   ├── topics.yml              # 主題 + 關鍵字
│   ├── sentiment_rules.yml     # 情緒詞典
│   ├── importance_rules.yml    # 重要性規則
│   ├── anomaly_rules.yml       # 異常偵測規則
│   └── 7d_highlights_rules.yml # 7 日報告規則
│
├── fetchers/                   # 公司新聞爬蟲
│   ├── base.py
│   ├── samsung.py
│   └── skhynix.py
│
├── data/
│   ├── raw/                    # 原始抓取資料 (按日期分目錄)
│   ├── events/                 # 標準格式事件 (JSONL，唯一資料源)
│   ├── metrics/                # 每日指標 (JSON)
│   ├── baselines/              # 歷史基準線
│   └── normalized/             # 股價資料
│
├── reports/
│   ├── daily/                  # 每日報告
│   └── 7d/                     # 7 日報告
│
├── site/
│   ├── index.html              # D3.js Dashboard
│   └── data/                   # 前端資料
│
└── CLAUDE.md
```

---

## 追蹤範圍

### 公司 (19 家)

**上游 - 設備/材料** (5 家)
- ASML 艾司摩爾, Tokyo Electron 東京威力, Lam Research 科林研發
- SUMCO, SK Siltron SK實特隆

**中游 - 製造/封測** (8 家)
- Samsung 三星, SK hynix SK海力士, Micron 美光, 南亞科, 華邦電
- 日月光, 力成, 南茂

**下游 - 客戶** (6 家)
- NVIDIA 輝達, AMD 超微
- Apple 蘋果
- AWS, Microsoft 微軟, Google 谷歌

### 主題 (configs/topics.yml)

- HBM
- DRAM 價格 / NAND 價格
- 產能 / 資本支出
- AI 伺服器
- 財報 / 展望
- 缺貨 / 庫存
- DDR5 / 先進封裝 / EUV

---

## 事件結構

```json
{
  "id": "samsung-2026-03-14-001",
  "date": "2026-03-14",
  "time_tags": {
    "year": 2026, "quarter": "Q1", "month": 3, "week": 11, "weekday": "Thu"
  },
  "entities": {
    "companies": ["samsung"],
    "customers": ["nvidia"],
    "suppliers": ["asml"]
  },
  "topics": ["hbm", "capacity"],
  "sentiment": {
    "label": "positive",
    "score": 0.8,
    "keywords": ["擴產", "領先"]
  },
  "importance": {
    "score": 0.85,
    "reasons": ["涉及 HBM", "供應鏈上下游同時提及"]
  },
  "title": "Samsung 宣布 HBM4 產能擴張計畫",
  "content": "...",
  "sources": [
    {"url": "https://news.samsung.com/...", "type": "company_news", "fetched_at": "..."}
  ]
}
```

---

## 待完成

1. **其他公司爬蟲**
   - Micron - https://www.micron.com/about/newsroom
   - NVIDIA - https://nvidianews.nvidia.com/
   - ASML - Investor news

2. **GitHub Actions** - `.github/workflows/daily-ingest.yml`
   - 每日自動抓取股價 + 新聞
   - 執行標註 + 報告生成
   - 部署到 GitHub Pages

3. **前端整合**
   - 顯示每日報告（Top 5 新聞）
   - 顯示異常警示
   - 顯示 7 日趨勢
