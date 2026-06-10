"""音频转写通路(无字幕回退)—— 已验证可用(2026-06-09 实测跑通)。

实测数据(写进设计文档):
- 慢的是【一次性模型下载】(small 模型首次加载含下载 ~502s),不是每次转写。
  实测转写 60s 音频仅 7s。所以应在 setup 阶段预下载模型,把这段从每次使用中剔除。
- Whisper 会"自信地转错"专有名词:实测 Anthropic→Anthopica、游刃有余→游热流云、
  文档→文导。技术类视频建议用 initial_prompt 喂术语表纠偏 + 人工核对。
- 环境:yt-dlp(pip) + ffmpeg(brew 8.1.1) + faster-whisper(pip) 端到端跑通。
"""
from __future__ import annotations
import os
import subprocess
from .transcript import Segment

DEFAULT_MODEL = "small"   # 速度/准确度平衡;技术长视频可换 medium
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")


def download_audio(url_or_id: str, out_path: str, clip_seconds: int | None = None) -> str:
    """用 yt-dlp 下音频并转 mp3。clip_seconds 仅取前 N 秒(调试/验证用)。

    实测:yt-dlp 会警告无 JS runtime,但仍能下到音频(format 251)。
    """
    from yt_dlp import YoutubeDL
    base = out_path[:-4] if out_path.endswith(".mp3") else out_path
    pp_args = {}
    if clip_seconds:
        pp_args = {"FFmpegExtractAudio": ["-t", str(clip_seconds)]}
    opts = {
        "format": "bestaudio",
        "outtmpl": base + ".%(ext)s",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
        "postprocessor_args": pp_args,
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(opts) as ydl:
        ydl.download([url_or_id])
    mp3 = base + ".mp3"
    if not os.path.exists(mp3):
        raise RuntimeError(f"音频提取失败,未生成 {mp3}")
    return mp3


def transcribe_audio(
    audio_path: str,
    language: str = "zh",
    model_size: str = DEFAULT_MODEL,
    terms_prompt: str | None = None,
) -> list[Segment]:
    """faster-whisper 转写,归一为 Segment 列表。

    terms_prompt: 术语表,喂给 initial_prompt 纠正专有名词
        (如 "Codex, Anthropic, OpenAI, Claude Code")。
    """
    from faster_whisper import WhisperModel
    os.makedirs(MODELS_DIR, exist_ok=True)
    model = WhisperModel(
        model_size, device="cpu", compute_type="int8", download_root=MODELS_DIR
    )
    segments, _info = model.transcribe(
        audio_path,
        language=language,
        beam_size=1,
        initial_prompt=terms_prompt,
    )
    return [
        Segment(start=s.start, duration=max(s.end - s.start, 0.0), text=s.text.strip())
        for s in segments
    ]


def prefetch_model(model_size: str = DEFAULT_MODEL) -> None:
    """在 setup 阶段预下载模型(把首次 ~8 分钟的下载从用户使用路径剔除)。"""
    from faster_whisper import WhisperModel
    os.makedirs(MODELS_DIR, exist_ok=True)
    WhisperModel(model_size, device="cpu", compute_type="int8", download_root=MODELS_DIR)
