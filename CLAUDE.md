# Memory Intel - 記憶體供應鏈情報追蹤

## 專案狀態：🟢 維護模式 (2026-03-15)

專案已完成開發，進入自動化維護階段。GitHub Actions 每日自動執行抓取、標註、報告生成流程。

### 系統架構

| 模組 | 說明 | 狀態 |
|------|------|------|
| **股價抓取** | 18 檔股票，Yahoo Finance | ✅ 自動化 |
| **新聞爬蟲** | 20 個爬蟲，涵蓋 19 家公司 | ✅ 自動化 |
| **規則引擎** | 關鍵字匹配、情緒分析、重要性評分、異常偵測 | ✅ 完成 |
| **報告生成** | 每日報告、7 日報告 | ✅ 自動化 |
| **前端** | D3.js Dashboard、供應鏈圖、事件時間軸 | ✅ 完成 |
| **CI/CD** | daily-ingest.yml + deploy-pages.yml | ✅ 運行中 |

### Skills（`.claude/skills/`）

| Skill | 觸發場景 | 對應畫面 |
|-------|---------|---------|
| 每日檢查 | 「今天狀態」「daily check」 | 摘要面板 |
| 修復爬蟲 | 「fetcher 壞了」「抓不到新聞」 | 事件時間軸 |
| 關鍵字調整 | 「gate2 擋太多」 | 摘要面板 filter_audit |
| 新增公司 | 「加入 XX 公司」 | 供應鏈圖 |
| 新增畫面功能 | 「Dashboard 加 XX」 | 股價面板 |
| 執行抓取 | 「手動跑一次」 | 全畫面更新 |
| 產出報告 | 「產出報告」 | 摘要面板（AI 分析） |
| 畫面規範 | 修改 index.html 前 | 全畫面配色/字體 |

### 維護檢查清單

```bash
# 一鍵健康檢查（檢查 Actions、事件、股價、本地同步狀態）
./scripts/health_check.sh

# 或手動檢查個別項目：
gh run list --limit 5                          # GitHub Actions 狀態
ls -la data/events/$(date +%Y-%m-%d).jsonl     # 今日事件
jq length site/data/events.json                # 前端事件數量
```

---

## 產出報告（Claude CLI）

當用戶說「產出報告」時，執行以下流程：

### 1. 拉取最新資料
```bash
git pull origin main
```

### 2. 讀取事件資料
- 讀取近 7 天的 `data/events/{date}.jsonl`
- 識別重要事件、主題趨勢、供應鏈動態

### 3. 抓取財務數據
用 yfinance 抓取追蹤公司的季度 Accounts Receivable 和 Inventory：
```python
source .venv/bin/activate
python3 -c "
import yfinance as yf
tickers = ['005930.KS','000660.KS','MU','2408.TW','2344.TW','NVDA','AMD','AAPL']
for t in tickers:
    bs = yf.Ticker(t).quarterly_balance_sheet
    # 取 'Accounts Receivable' 和 'Inventory' 的最近 2 季
"
```

### 4. 產出分析並寫入 JSON
讀取現有的 Actions 報告 JSON，追加 `llm_analysis` 和 `financials` 欄位：

**Daily Report** (`site/data/reports/daily/{date}.json`)：
```json
{
  "...existing fields preserved...",
  "llm_analysis": {
    "summary": "2-3 句市場摘要",
    "signals": [
      { "text": "訊號描述", "level": "red|yellow|green" }
    ]
  },
  "financials": {
    "quarter": "2025-Q4",
    "data": [
      {
        "company": "micron", "name": "Micron",
        "ar": 15389000000, "ar_qoq": "+92%",
        "inventory": 8267000000, "inv_qoq": "+1%",
        "alert": true, "currency": "USD"
      }
    ]
  },
  "generated_by": "claude-cli"
}
```

**7d Report** (`site/data/reports/7d/{date}.json`)：
```json
{
  "...existing fields preserved...",
  "llm_analysis": {
    "summary": "3-4 句週度摘要",
    "watchlist": [
      { "company": "Samsung", "reason": "觀察原因" }
    ]
  },
  "generated_by": "claude-cli"
}
```

### 5. Commit 並 Push
```bash
git add site/data/reports/
git commit -m "Weekly report: {date}"
git push
```

### 注意事項
- 保留既有 JSON 欄位（`top_events`、`anomalies`、`daily_breakdown` 等），只追加新欄位
- `financials.data` 中 `alert: true` 表示 AR 或庫存 QoQ 變化超過 ±20%
- `signals[].level`：`red` = 需關注、`yellow` = 持續觀察、`green` = 正面訊號

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

## 故障排除

### 常見問題

1. **GitHub Actions 失敗**
   - 檢查 `gh run view <run-id> --log-failed`
   - 常見原因：網站結構變更、API 限制

2. **爬蟲抓不到資料**
   - 檢查目標網站是否改版
   - 更新 `fetchers/` 對應的爬蟲

3. **前端資料未更新**
   - 確認 `sync_to_frontend.py` 有執行
   - 檢查 `site/data/events.json` 時間戳

### 手動執行流程

```bash
source .venv/bin/activate
python scripts/fetch_news.py           # 抓取新聞
python scripts/enrich_event.py         # 標註事件
python scripts/generate_metrics.py     # 計算指標
python scripts/generate_7d_report.py   # 7 日報告
python scripts/sync_to_frontend.py     # 同步前端
```


---

## 每日例行（進入此 repo 時自動提醒）

當你讀取此 CLAUDE.md 時，主動執行以下檢查並提醒用戶：

### 自動檢查清單

1. **同步最新** — `git pull origin main`
2. **今日 Actions 狀態** — `gh run list --limit 1`
3. **今日事件數** — `wc -l data/events/$(date +%Y-%m-%d).jsonl`
4. **關鍵字審計** — 讀取 `site/data/reports/daily/$(date +%Y-%m-%d).json` 的 `filter_audit` 欄位

### 提醒格式

```
📋 每日狀態
- Actions: ✅/❌
- 今日事件: N 筆
- 關鍵字審計: ✅ 通過 / ⚠️ gate2 擋住率 XX%，建議檢視
```

若 `filter_audit.alert` 為 true 或 `gate2_block_rate > 30%`，提醒用戶：「有關鍵字需要調整，要執行關鍵字審計嗎？」

### 關鍵字審計流程（用戶確認後執行）

1. 檢視 `filter_audit.gate2_samples` 中被擋住的文章標題
2. 判斷每篇是否與本追蹤產業相關
3. 相關的文章 → 找出缺少的關鍵字，建議新增到 `configs/topics.yml`
4. 呈現結果：

```
## 關鍵字審計結果

通過率：XX% | Gate 2 擋住率：XX%

### 被擋住但應通過的文章
| 標題 | 缺少的關鍵字 | 建議加入的主題 |
|------|-------------|--------------|

### 建議新增關鍵字
topics.yml → {topic_id} → keywords 新增：
- keyword1
- keyword2
```

5. 用戶確認後更新 `configs/topics.yml`，commit + push

