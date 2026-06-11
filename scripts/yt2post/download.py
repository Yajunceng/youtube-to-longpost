"""下载视频文件(抽帧用)—— 已验证(2026-06-09)。

抽帧需要视频画面,不是音频。用 yt-dlp 下中等画质即可(读画面不需要 4K)。
实测:`best[height<=480]` 下 480p,3 分钟约 5MB,足够多模态看清界面文字。
"""
from __future__ import annotations
import os


def download_video(url_or_id: str, out_path: str, max_height: int = 480,
                   clip_seconds: int | None = None) -> str:
    """下视频到 out_path(.mp4)。max_height 限制画质;clip_seconds 仅取前 N 秒(调试)。"""
    from yt_dlp import YoutubeDL
    base = out_path[:-4] if out_path.endswith(".mp4") else out_path
    opts = {
        "format": f"best[height<={max_height}]",
        "outtmpl": base + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
    }
    if clip_seconds:
        opts["download_ranges"] = lambda info, ydl: [{"start_time": 0, "end_time": clip_seconds}]
        opts["force_keyframes_at_cuts"] = True
    with YoutubeDL(opts) as ydl:
        ydl.download([url_or_id])
    mp4 = base + ".mp4"
    if not os.path.exists(mp4):
        # yt-dlp 可能产出别的扩展名,找一下
        for ext in (".mkv", ".webm"):
            if os.path.exists(base + ext):
                return base + ext
        raise RuntimeError(f"视频下载失败,未生成 {mp4}")
    return mp4
