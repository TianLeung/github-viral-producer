#!/usr/bin/env bash
# ============================================================
# GitHub 开源爆款短视频生产线 v2 —— 安装入口（macOS / Linux）
# Windows 用户请直接运行：python install.py
#
# 本脚本只是薄封装，实际逻辑全在 install.py（跨平台，单一实现）。
# ============================================================
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if command -v python3 >/dev/null 2>&1; then
  exec python3 install.py
elif command -v python >/dev/null 2>&1; then
  exec python install.py
else
  echo "[ERROR] 未检测到 Python，请先安装 Python 3.8+。" >&2
  exit 1
fi
