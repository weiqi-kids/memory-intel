#!/bin/bash
# 本地開發伺服器
# Port 6229 = 1962/02/09 臺灣證券交易所開業首日
# 啟動前會自動同步遠端資料，避免本地落後

cd "$(dirname "$0")/.."

PORT=6229

echo "=== 同步遠端資料 ==="
git pull origin main 2>/dev/null || echo "（無法同步，使用本地資料）"

echo ""
echo "=== Memory Intel Dashboard ==="
echo "http://localhost:$PORT"
echo ""
echo "Port 6229 = 1962/02/09 臺灣證券交易所開業首日"
echo "按 Ctrl+C 停止"
echo ""

python3 -m http.server $PORT -d site
