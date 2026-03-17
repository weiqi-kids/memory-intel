#!/bin/bash
# 系統健康檢查腳本
# 檢查 GitHub Actions、事件資料、股價資料的狀態

set -e

REPO="weiqi-kids/memory-intel"
SITE_URL="https://memory.intel.weiqi.kids"

echo "================================================"
echo "Memory Intel 健康檢查"
echo "檢查時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"
echo ""

# 1. 檢查 GitHub Actions
echo "=== GitHub Actions ==="
echo ""
gh run list -R "$REPO" --limit 5 --json status,conclusion,displayTitle,createdAt \
  --jq '.[] | "\(.conclusion // .status)\t\(.createdAt | split("T")[0])\t\(.displayTitle)"' \
  | while read line; do
    status=$(echo "$line" | cut -f1)
    if [ "$status" = "success" ]; then
      echo "✅ $line"
    elif [ "$status" = "failure" ]; then
      echo "❌ $line"
    else
      echo "⏳ $line"
    fi
  done
echo ""

# 2. 檢查事件資料
echo "=== 事件資料 ==="
curl -s "$SITE_URL/data/events.json" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    total = len(data)
    if total > 0:
        dates = [e.get('date', '') for e in data if e.get('date')]
        latest = max(dates) if dates else 'N/A'
        print(f'✅ 總筆數: {total}')
        print(f'   最新日期: {latest}')
    else:
        print('⚠️  沒有事件資料')
except Exception as e:
    print(f'❌ 解析失敗: {e}')
"
echo ""

# 3. 檢查股價資料
echo "=== 股價資料 ==="
curl -s "$SITE_URL/data/stocks.json" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    total_companies = len(data)
    print(f'✅ 公司數: {total_companies}')
    print('')

    # 按最新日期分組
    asia = []  # 亞洲股票
    us = []    # 美股

    for company, prices in data.items():
        if prices:
            latest = max(p['date'] for p in prices)
            count = len(prices)
            # 簡單判斷：台韓日股票代碼
            if company in ['samsung', 'skhynix', 'nanya', 'winbond', 'ase', 'powertech', 'ptc', 'tokyo_electron', 'sumco']:
                asia.append((company, latest, count))
            else:
                us.append((company, latest, count))

    if asia:
        asia_latest = max(d[1] for d in asia)
        print(f'   亞洲股票 ({len(asia)} 家): 最新 {asia_latest}')
    if us:
        us_latest = max(d[1] for d in us)
        print(f'   美股 ({len(us)} 家): 最新 {us_latest}')

except Exception as e:
    print(f'❌ 解析失敗: {e}')
"
echo ""

# 4. 檢查本地是否落後遠端
echo "=== 本地同步狀態 ==="
cd "$(dirname "$0")/.."
git fetch origin 2>/dev/null || true
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main 2>/dev/null || echo "unknown")

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "✅ 本地與遠端同步"
else
    echo "⚠️  本地落後遠端，請執行 git pull"
    echo "   本地: ${LOCAL:0:7}"
    echo "   遠端: ${REMOTE:0:7}"
fi
echo ""

echo "================================================"
echo "檢查完成"
echo "================================================"
