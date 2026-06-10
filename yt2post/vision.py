"""多模态读画面 —— 骨架(待接入 API key 验证)。

设计要点(来自设计文档实现要点 1/4):
- 【对齐:首版用固定非对称窗口,不做动态对齐】每个关键帧配前 5 秒到后 15 秒的
  字幕窗口,让多模态同时看到"这张图"和"讲者在这页前后说的话",避免把上页
  讲解配到这页图。动态检测时间差是研究级难题,首版不做。
- 实测警示:多模态读图表数字会"自信地编造"(和 Whisper 转错专有名词同源),
  所以有"编造率核对"验收标准。prompt 里要求 AI 对读不清的数字明确标注不确定,
  而不是猜一个。
"""
from __future__ import annotations
from dataclasses import dataclass
from .transcript import Segment
from .frames import Frame

WINDOW_BEFORE = 5.0    # 帧前留 5 秒字幕
WINDOW_AFTER = 15.0    # 帧后留 15 秒字幕(非对称:讲者常先翻页再讲)


@dataclass
class FrameDescription:
    timestamp: float
    description: str
    subtitle_window: str


def subtitle_window_for(frame: Frame, segments: list[Segment]) -> str:
    """取该帧固定非对称窗口内的字幕文本(前 5 后 15 秒)。已可实现,无需 API。"""
    lo = frame.timestamp - WINDOW_BEFORE
    hi = frame.timestamp + WINDOW_AFTER
    picked = [s.text for s in segments if s.end >= lo and s.start <= hi]
    return " ".join(t for t in picked if t)


def describe_frame(frame: Frame, segments: list[Segment], client=None) -> FrameDescription:
    """调多模态描述单帧画面 + 其字幕窗口。

    TODO:接入 anthropic / openai 多模态。prompt 要点:
      - 同时给图和 subtitle_window,要求结合上下文描述画面关键信息
      - 读不清的数字/文字明确标"不确定",禁止猜测(降低编造率)
      - 重点抓:操作步骤、界面元素、图表数字、代码/命令
    """
    raise NotImplementedError("多模态读画面:待接入 API key 验证")
