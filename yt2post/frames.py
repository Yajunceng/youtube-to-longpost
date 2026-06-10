"""抽帧 + 帧去重 —— 骨架(设计已定,待真实视频验证参数)。

设计要点(来自设计文档实现要点 2/3):
- 抽帧 = 场景切换 + 定时补抽。场景切换只能抓"切页",同页渐进揭示的数字
  (最值钱的内容)靠定时补抽兜底。
- 【关键矛盾】去重会吃掉定时补抽要捞的同页新增数字:同一张 PPT 只多一行字,
  在全局感知哈希眼里是"近重复"会被滤掉。所以两类帧用【不同去重策略】:
    * 场景切换帧 → 全局感知哈希去重(滤翻页噪声)
    * 定时补抽帧 → 局部/敏感差异检测,宁多留不漏
- 阈值(scene 0.3、补抽间隔 N、哈希距离)都需真实视频实测,勿先验写死。
"""
from __future__ import annotations
import os
import subprocess
from dataclasses import dataclass


@dataclass
class Frame:
    path: str
    timestamp: float        # 秒
    source: str             # "scene" | "interval"


def extract_scene_frames(video_path: str, out_dir: str, scene_threshold: float = 0.3) -> list[Frame]:
    """ffmpeg 场景切换抽帧:select='gt(scene,threshold)'。

    TODO(待实测):threshold 调参。低则帧爆炸(PPT动画/鼠标误检),高则漏切页。
    """
    raise NotImplementedError("场景切换抽帧:待接入并用真实视频调 scene_threshold")


def extract_interval_frames(video_path: str, out_dir: str, interval_s: int = 30) -> list[Frame]:
    """定时补抽:每 interval_s 秒强制抽一帧,兜底同页渐进揭示的信息。

    TODO(待实测):interval_s 取值,是否真能抓到同页逐步出现的数字。
    """
    raise NotImplementedError("定时补抽:待接入并用真实视频调 interval_s")


def dedup_frames(scene_frames: list[Frame], interval_frames: list[Frame]) -> list[Frame]:
    """分流去重(见模块 docstring 的关键矛盾)。

    场景帧用全局感知哈希(imagehash.phash)滤近重复;
    定时补抽帧用更敏感的局部差异判定,避免把"同页新增一行数字"误删。
    TODO:实现两套阈值,用真实视频验证不会吃掉关键数字。
    """
    raise NotImplementedError("分流去重:待实现 + 验证不丢同页数字")
