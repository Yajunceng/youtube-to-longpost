"""命令行入口。

skill 的最终产物是一个【素材包目录】,交给 Hermes 这类自带 vision 的 agent:
  python -m yt2post.cli "<url>"
    → 抓字幕(无字幕回退 Whisper)+ 下视频抽帧 + 分流去重 + 配字幕窗口
    → 输出 output/<id>_package/ (transcript.txt + frames/ + manifest.json + AGENT_INSTRUCTIONS.md)

agent 拿到包,用自己的多模态能力逐张看帧、结合字幕,写出纯文本长文。skill 不调 API。

也支持只要文字记录:
  python -m yt2post.cli "<url>" --transcript-only
"""
from __future__ import annotations
import argparse
import os
import shutil
import sys

from . import transcript as T
from . import transcribe as W
from . import download as D
from . import frames as F
from . import vision as V
from . import compose as C

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


def get_segments(url_or_id: str, languages, terms):
    """先试字幕,无字幕回退 Whisper。返回 (segments, source)。"""
    vid = T.extract_video_id(url_or_id)
    try:
        segs = T.fetch_transcript(vid, languages=languages)
        if segs:
            return segs, "subtitle"
    except Exception as e:
        print(f"[字幕] 不可用({type(e).__name__}),回退 Whisper 转写…", file=sys.stderr)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    audio = os.path.join(OUTPUT_DIR, f"{vid}.mp3")
    print("[whisper] 下载音频…", file=sys.stderr)
    W.download_audio(url_or_id, audio)
    print("[whisper] 转写中(首次会下载模型,请耐心)…", file=sys.stderr)
    segs = W.transcribe_audio(audio, terms_prompt=terms)
    return segs, "whisper"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="yt2post", description="YouTube 视频 → 给 agent 的长文素材包")
    p.add_argument("url", help="YouTube 链接或 video id")
    p.add_argument("--lang", action="append", help="字幕语言优先级,可多次")
    p.add_argument("--terms", help="术语表,纠正 Whisper 专有名词")
    p.add_argument("--transcript-only", action="store_true", help="只输出文字记录,不抽帧不打包")
    p.add_argument("--scene-threshold", type=float, default=0.3, help="场景切换阈值(默认 0.3)")
    p.add_argument("--interval", type=int, default=30, help="定时补抽间隔秒(默认 30)")
    p.add_argument("--max-height", type=int, default=480, help="下载视频最大高度(默认 480)")
    args = p.parse_args(argv)

    vid = T.extract_video_id(args.url)
    segs, source = get_segments(args.url, args.lang, args.terms)
    dur = T.real_duration(segs)
    print(f"[字幕] 来源 {source}  片段 {len(segs)} 条  时长 {int(dur//60)}分{int(dur%60)}秒",
          file=sys.stderr)

    if args.transcript_only:
        print(T.join_text(segs))
        return 0

    # 下视频 → 抽帧 → 去重
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    video_path = os.path.join(OUTPUT_DIR, f"{vid}.mp4")
    print("[视频] 下载中…", file=sys.stderr)
    video_path = D.download_video(args.url, video_path, max_height=args.max_height)

    frames_dir = os.path.join(OUTPUT_DIR, f"{vid}_frames")
    if os.path.isdir(frames_dir):
        shutil.rmtree(frames_dir)
    print("[抽帧] 场景切换 + 定时补抽 + 去重…", file=sys.stderr)
    frames = F.extract_all(video_path, frames_dir,
                           scene_threshold=args.scene_threshold, interval_s=args.interval)
    print(f"[抽帧] 去重后 {len(frames)} 帧", file=sys.stderr)

    # 配字幕窗口 → 打包
    materials = V.build_materials(frames, segs)
    pkg_dir = os.path.join(OUTPUT_DIR, f"{vid}_package")
    if os.path.isdir(pkg_dir):
        shutil.rmtree(pkg_dir)
    pkg_frames = os.path.join(pkg_dir, "frames")
    os.makedirs(pkg_frames, exist_ok=True)
    # 把去重后的帧复制进包,并把 manifest 里的路径改成包内相对路径
    for m in materials:
        dst = os.path.join(pkg_frames, os.path.basename(m.image_path))
        shutil.copy(m.image_path, dst)
        m.image_path = os.path.join("frames", os.path.basename(m.image_path))

    C.build_package(pkg_dir, args.url, segs, materials)
    print(f"\n[完成] 素材包: {pkg_dir}", file=sys.stderr)
    print(f"  - transcript.txt / manifest.json / AGENT_INSTRUCTIONS.md / frames({len(materials)})",
          file=sys.stderr)
    print(f"\n把这个目录交给 Hermes,它会按 AGENT_INSTRUCTIONS.md 看图写长文。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
