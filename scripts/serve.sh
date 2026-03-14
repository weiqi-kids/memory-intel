#!/bin/bash
# 本地開發伺服器
# Port 6229 = 1962/02/09 臺灣證券交易所開業首日

PORT=6229
DIR="$(dirname "$0")/../site"

echo "Memory Intel Dashboard"
echo "http://localhost:$PORT"
echo ""
echo "Port 6229 = 1962/02/09 臺灣證券交易所開業首日"
echo "Press Ctrl+C to stop"
echo ""

cd "$DIR" && python3 -m http.server $PORT
