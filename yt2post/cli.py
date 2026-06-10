"""命令行入口。

已可跑:
  python -m yt2post.cli "<url>" --transcript-only
    → 抓字幕(无字幕回退 Whisper),输出排好序的纯文本文字记录。

待接入 API key 后可跑完整流程(抽帧→读画面→长文)。
"""
from __future__ import annotations
import argparse
import os
import sys

from . import transcript as T
from . import transcribe as W

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


def get_segments(url_or_id: str, languages: list[str] | None, terms: str | None):
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
    p = argparse.ArgumentParser(prog="yt2post", description="YouTube 视频 → 推特纯文本长文")
    p.add_argument("url", help="YouTube 链接或 video id")
    p.add_argument("--lang", action="append", help="字幕语言优先级,可多次(如 --lang zh-CN --lang en)")
    p.add_argument("--terms", help="术语表,纠正 Whisper 专有名词(如 'Codex, Anthropic, Claude Code')")
    p.add_argument("--transcript-only", action="store_true", help="只输出文字记录,不读画面、不生成长文")
    args = p.parse_args(argv)

    segs, source = get_segments(args.url, args.lang, args.terms)
    dur = T.real_duration(segs)
    text = T.join_text(segs)
    print(f"[来源] {source}  片段 {len(segs)} 条  时长 {int(dur//60)}分{int(dur%60)}秒  共 {len(text)} 字",
          file=sys.stderr)

    if args.transcript_only:
        print(text)
        return 0

    print("\n[未实现] 读画面 + 长文生成需要先配置多模态 API key。"
          "\n当前可用:--transcript-only 输出文字记录。"
          "\n后续步骤见设计文档 Next Steps(抽帧→读画面→融合)。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
