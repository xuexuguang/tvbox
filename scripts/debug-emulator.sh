#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
TVBOX_LOCAL_BASE_URL=http://10.0.2.2:8765 python3 scripts/update.py
printf '%s\n' '模拟器多仓订阅地址' 'http://10.0.2.2:8765/%E5%A4%9A%E4%BB%93%E8%AE%A2%E9%98%85.json'
exec python3 -m http.server 8765 --bind 127.0.0.1 --directory output-local
