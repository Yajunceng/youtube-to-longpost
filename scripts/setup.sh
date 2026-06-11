#!/usr/bin/env bash
# 一次性环境准备:装 Python 依赖 + 检查 ffmpeg。
# 由 SKILL.md 指挥 agent 在首次使用时运行。
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[setup] 安装 Python 依赖…"
python3 -m pip install --quiet -r "$DIR/requirements.txt"

echo "[setup] 检查 ffmpeg…"
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[setup] ⚠️ 未找到 ffmpeg。macOS 请运行: brew install ffmpeg"
  echo "[setup]    (抽帧和 Whisper 转写都依赖它)"
  exit 1
fi

echo "[setup] 预下载 Whisper 模型(避免首次使用时等待)…"
python3 -c "import sys; sys.path.insert(0,'$DIR'); from yt2post.transcribe import prefetch_model; prefetch_model()" || \
  echo "[setup] (Whisper 模型预下载跳过,无字幕视频首次使用时会自动下载)"

echo "[setup] ✅ 环境就绪"
