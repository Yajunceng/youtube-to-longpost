"""融合 + 长文生成 —— 骨架(待接入 API key 验证)。

设计要点(来自设计文档实现要点 4/5):
- 数据结构:把全片组织成时间线 —— 一串 (时间戳, 字幕片段, 该窗口的帧描述)。
- 生成:整条时间线喂一次 LLM,套固定模板;若超上下文则两段式(先逐段要点,再统稿)。
- 输出规格(用户已定):一整篇【纯文本】长文,钩子开头、自然分段、结尾带原链接、
  【无 markdown 标记】(推特长文不渲染 markdown)。
- 超长:先确认 X 长文字符上限,超限时优先"压缩到上限内",不截断、不自动切 thread。
"""
from __future__ import annotations
from dataclasses import dataclass
from .transcript import Segment
from .vision import FrameDescription

# TODO:确认 X 长文字符上限后填入(开放问题 5,动手前必做)
X_LONGPOST_CHAR_LIMIT = None


@dataclass
class TimelineEntry:
    timestamp: float
    subtitle: str
    frame_description: str | None


def build_timeline(segments: list[Segment], descriptions: list[FrameDescription]) -> list[TimelineEntry]:
    """把字幕和帧描述按时间缝成一条时间线。已可实现(纯数据,无需 API)。"""
    entries: list[TimelineEntry] = []
    desc_by_ts = sorted(descriptions, key=lambda d: d.timestamp)
    di = 0
    for seg in segments:
        fd = None
        while di < len(desc_by_ts) and desc_by_ts[di].timestamp <= seg.end:
            fd = desc_by_ts[di].description
            di += 1
        entries.append(TimelineEntry(seg.start, seg.text, fd))
    return entries


LONGPOST_PROMPT = """你是一个帮我把视频内容改写成推特长文的助手。下面是一个视频的时间线,\
每条包含口播字幕和(若有)画面描述。请缝合成一篇【纯文本】长文:
- 开头第一句是吸引人的钩子
- 自然分段(段落间空行)
- 【不要】用任何 markdown 标记(不要 # ## ** - 等)
- 结尾附上原视频链接:{url}
- 忠于内容,画面里的操作步骤/数字要保留;读不清或不确定的不要编造
- 控制在 {limit} 字以内

时间线:
{timeline}
"""


def compose_longpost(timeline: list[TimelineEntry], video_url: str, client=None) -> str:
    """调 LLM 生成纯文本长文。

    TODO:接入 LLM,渲染 LONGPOST_PROMPT;超长走两段式统稿;
    生成后做无-markdown 校验(兜底剥离残留标记)。
    """
    raise NotImplementedError("长文生成:待接入 LLM API 验证")
