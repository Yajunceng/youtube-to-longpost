"""为每帧准备素材 —— skill 不调 API,把"看图"留给 agent(Hermes)。

架构决定(2026-06-09):skill 交给 Hermes 这类自带 vision 的 agent 用。
所以 skill 只干体力活:抽帧 + 给每帧配好对应时间窗口的字幕,打包成素材。
真正"看图理解"由 agent 用自己的多模态能力做(Hermes 的 vision_analyze 工具),
不需要 skill 再去接 Anthropic/OpenAI 的 API key —— 否则等于在有脑子的 agent 里
又雇第二个脑子,重复且多花一份钱。

设计要点(来自设计文档实现要点 1):
- 【对齐:固定非对称窗口】每帧配前 5 秒到后 15 秒字幕,让 agent 看图时同时拿到
  "讲者在这页前后说的话",避免把上页讲解配到这页图。
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .transcript import Segment
from .frames import Frame

WINDOW_BEFORE = 5.0    # 帧前留 5 秒字幕
WINDOW_AFTER = 15.0    # 帧后留 15 秒字幕(非对称:讲者常先翻页再讲)


@dataclass
class FrameMaterial:
    """交给 agent 的单帧素材:图在哪、什么时间、配套字幕是什么。"""
    image_path: str
    timestamp: float
    source: str             # "scene" | "interval"
    subtitle_window: str    # 该帧前5后15秒的字幕
    likely_redundant: bool = False  # 与前一张已保留帧近重复(脚本用 phash 预判,agent 可优先跳过)

    def to_dict(self) -> dict:
        return asdict(self)


def subtitle_window_for(frame: Frame, segments: list[Segment]) -> str:
    """取该帧固定非对称窗口内的字幕文本(前 5 后 15 秒)。"""
    lo = frame.timestamp - WINDOW_BEFORE
    hi = frame.timestamp + WINDOW_AFTER
    picked = [s.text for s in segments if s.end >= lo and s.start <= hi]
    return " ".join(t for t in picked if t)


# 预判"近重复"的 phash 距离阈值:与前一张已保留帧距离 <= 此值,标记 likely_redundant。
# 实测正常切换帧距离 >=18,这里取 10 作中间档:明显相似才标,避免误标掉有新增内容的帧。
REDUNDANT_HINT_THRESHOLD = 10


def _mark_redundancy(mats: list[FrameMaterial]) -> None:
    """用 phash 给每帧预判是否与前一张近重复,写进 likely_redundant。

    把"这帧值不值得看"的判断从 agent(每次要花一次 vision 调用去比)挪到脚本
    (本地 phash,免费)。注意:只给 interval 帧标 —— scene 帧是画面真切换,
    永远不标记为冗余,确保 agent 一定会看。
    """
    from .frames import _phash  # 复用已实现的 phash
    prev_hash = None
    for m in mats:
        try:
            h = _phash(m.image_path)
        except Exception:
            prev_hash = None
            continue
        if m.source == "interval" and prev_hash is not None and (prev_hash - h) <= REDUNDANT_HINT_THRESHOLD:
            m.likely_redundant = True
        else:
            # scene 帧、或与上一张差异够大的 interval 帧:更新基准
            prev_hash = h


def build_materials(frames: list[Frame], segments: list[Segment]) -> list[FrameMaterial]:
    """为每帧配字幕窗口,打包成给 agent 的素材列表(按时间排序,带冗余预判)。"""
    mats = [
        FrameMaterial(
            image_path=f.path,
            timestamp=f.timestamp,
            source=f.source,
            subtitle_window=subtitle_window_for(f, segments),
        )
        for f in frames
    ]
    mats.sort(key=lambda m: m.timestamp)
    _mark_redundancy(mats)
    return mats
