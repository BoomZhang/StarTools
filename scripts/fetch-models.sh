#!/usr/bin/env bash
# 下载语音识别所需的 Whisper base 模型（约 145MB）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_DIR="$ROOT_DIR/backend/models/whisper/base"
BASE_URL="https://hf-mirror.com/Systran/faster-whisper-base/resolve/main"

mkdir -p "$MODEL_DIR"
for file in config.json tokenizer.json vocabulary.txt model.bin; do
  target="$MODEL_DIR/$file"
  if [[ -s "$target" ]]; then
    echo "[models] 已存在：$file"
    continue
  fi
  echo "[models] 下载 $file ..."
  curl -sSL --retry 3 --max-time 900 -A 'Mozilla/5.0' -o "$target" "$BASE_URL/$file"
done

echo "[models] Whisper base 模型已准备：$MODEL_DIR"
