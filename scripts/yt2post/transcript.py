"""字幕通路 —— 已验证可用(2026-06-09 实测跑通)。

实测踩到的坑(写进设计文档 Open Questions / Next Steps):
- youtube-transcript-api 返回的片段顺序【不保证按时间排】。实测视频
  2uofIH81koo 的片段乱序(结尾的话排在最前)。必须按 start 排序再拼接,
  否则开头会变成结尾、整篇逻辑错乱。
- 真实时长用 max(start+duration) 算,不能信片段顺序的最后一条。
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Segment:
    """一条时间对齐的文字片段。字幕和 Whisper 转写都归一到这个结构。"""
    start: float        # 起始秒
    duration: float     # 时长秒
    text: str

    @property
    def end(self) -> float:
        return self.start + self.duration


def extract_video_id(url_or_id: str) -> str:
    """从各种 YouTube URL 形态里抠出 video id;已是 id 就原样返回。"""
    import re
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id):
        return url_or_id
    m = re.search(r"(?:v=|/shorts/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})", url_or_id)
    if not m:
        raise ValueError(f"无法从输入中解析出 YouTube video id: {url_or_id!r}")
    return m.group(1)


def list_tracks(video_id: str):
    """列出可用字幕轨道。返回 youtube-transcript-api 的轨道列表。"""
    from youtube_transcript_api import YouTubeTranscriptApi
    return YouTubeTranscriptApi().list(video_id)


def fetch_transcript(video_id: str, languages: list[str] | None = None) -> list[Segment]:
    """抓字幕并归一为按时间排序的 Segment 列表。

    无字幕会抛 youtube_transcript_api 的 TranscriptsDisabled / NoTranscriptFound,
    由调用方决定是否回退到 Whisper(见 transcribe.py)。
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    if languages:
        fetched = api.fetch(video_id, languages=languages)
    else:
        fetched = api.fetch(video_id)

    segs = [
        Segment(start=s.start, duration=s.duration, text=s.text.replace("\n", " ").strip())
        for s in fetched.snippets
    ]
    # 关键修复:必须按时间戳排序(实测片段会乱序)
    segs.sort(key=lambda s: s.start)
    return segs


def real_duration(segments: list[Segment]) -> float:
    """真实时长 = max(start+duration),不能信片段顺序。"""
    return max((s.end for s in segments), default=0.0)


def join_text(segments: list[Segment]) -> str:
    """拼成连续纯文本(已按时间排好序)。"""
    return " ".join(s.text for s in segments if s.text)
