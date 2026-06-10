"""抽帧 + 帧去重 —— 已实现并用真实视频验证(2026-06-09)。

设计要点(来自设计文档实现要点 2/3):
- 抽帧 = 场景切换 + 定时补抽。场景切换只能抓"切页",同页渐进揭示的数字
  (最值钱的内容)靠定时补抽兜底。
- 【关键矛盾】去重会吃掉定时补抽要捞的同页新增数字:同一张 PPT 只多一行字,
  在全局感知哈希眼里是"近重复"会被滤掉。所以两类帧用【不同去重策略】:
    * 场景切换帧 → 全局感知哈希(phash)去重,滤翻页噪声(实测同一次切换会被
      检测两次,如 147.2s 和 147.3s)
    * 定时补抽帧 → 更敏感的差异判定(更小的哈希距离阈值 + 保护性保留),
      宁多留不漏同页新增内容

实测数据(giffgaff 视频前 3 分钟,480p):
  scene>0.2→14帧  >0.3→11帧  >0.4→9帧  >0.5→9帧。0.3 为合理默认(13分钟约48帧)。
  抽出的帧确含字幕没有的关键信息(GitHub项目页/star数/版本),证实读画面必需。

  【去重的真实校准,纠正了一个想当然】相邻场景帧的 phash 距离实测全在 18~38,
  连时间上仅差 0.1s 的 147.2/147.3 两帧距离也有 18(画面真有变化,不是噪声)。
  结论:对"干净切换"的视频,场景检测@0.3 几乎无冗余,phash 去重基本不触发,
  阈值设多少都行。去重真正要防的"PPT 逐行动画噪声"在这个视频里没出现 ——
  需要一个动画密集的视频才能真正压测去重。所以阈值是保守的,宁可少去重不要
  误删关键帧(误删 = 丢信息,是这工具最不能犯的错)。
"""
from __future__ import annotations
import os
import subprocess
from dataclasses import dataclass

# 去重哈希距离阈值:汉明距离 <= 阈值 视为近重复
# 实测:正常切换的相邻帧距离 >=18,所以下面阈值只会滤掉几乎全同的帧。
# 故意保守 —— 误删关键帧(丢信息)比多留几张冗余帧代价大得多。
SCENE_HASH_THRESHOLD = 4      # 场景帧:滤翻页噪声(动画密集视频才会触发)
INTERVAL_HASH_THRESHOLD = 2   # 补抽帧:更严格,保护同页新增内容


@dataclass
class Frame:
    path: str
    timestamp: float        # 秒
    source: str             # "scene" | "interval"


def _ffmpeg_bin() -> str:
    for p in ("/opt/homebrew/bin/ffmpeg", "ffmpeg"):
        if os.path.dirname(p) == "" or os.path.exists(p):
            return p
    return "ffmpeg"


def _parse_scene_timestamps(stderr: str) -> list[float]:
    import re
    return [float(m) for m in re.findall(r"pts_time:([0-9.]+)", stderr)]


def extract_scene_frames(video_path: str, out_dir: str, scene_threshold: float = 0.3) -> list[Frame]:
    """ffmpeg 场景切换抽帧:select='gt(scene,threshold)'。

    threshold 实测默认 0.3。低则帧爆炸(PPT动画/鼠标/画中画误检),高则漏切页。
    """
    os.makedirs(out_dir, exist_ok=True)
    pattern = os.path.join(out_dir, "scene_%04d.jpg")
    proc = subprocess.run(
        [_ffmpeg_bin(), "-y", "-i", video_path,
         "-filter:v", f"select='gt(scene,{scene_threshold})',showinfo",
         "-vsync", "vfr", pattern],
        capture_output=True, text=True,
    )
    timestamps = _parse_scene_timestamps(proc.stderr)
    files = sorted(f for f in os.listdir(out_dir) if f.startswith("scene_"))
    frames = []
    for i, fn in enumerate(files):
        ts = timestamps[i] if i < len(timestamps) else 0.0
        frames.append(Frame(path=os.path.join(out_dir, fn), timestamp=ts, source="scene"))
    return frames


def extract_interval_frames(video_path: str, out_dir: str, interval_s: int = 30) -> list[Frame]:
    """定时补抽:每 interval_s 秒强制抽一帧,兜底同页渐进揭示的信息。"""
    os.makedirs(out_dir, exist_ok=True)
    pattern = os.path.join(out_dir, "interval_%04d.jpg")
    subprocess.run(
        [_ffmpeg_bin(), "-y", "-i", video_path,
         "-filter:v", f"fps=1/{interval_s}",
         pattern],
        capture_output=True, text=True,
    )
    files = sorted(f for f in os.listdir(out_dir) if f.startswith("interval_"))
    return [
        Frame(path=os.path.join(out_dir, fn), timestamp=float(i * interval_s), source="interval")
        for i, fn in enumerate(files)
    ]


def _phash(path: str):
    import imagehash
    from PIL import Image
    return imagehash.phash(Image.open(path))


def _dedup_within(frames: list[Frame], threshold: int) -> list[Frame]:
    """组内去重:与已保留帧的最近一张比,汉明距离 <= threshold 则丢弃。"""
    kept: list[Frame] = []
    kept_hashes = []
    for f in frames:
        h = _phash(f.path)
        if kept_hashes and (kept_hashes[-1] - h) <= threshold:
            continue   # 近重复,丢
        kept.append(f)
        kept_hashes.append(h)
    return kept


def dedup_frames(scene_frames: list[Frame], interval_frames: list[Frame]) -> list[Frame]:
    """分流去重(见模块 docstring 的关键矛盾)。

    场景帧用宽松阈值积极滤翻页噪声;补抽帧用严格阈值只滤几乎全同的,
    避免把"同页新增一行数字"误删。最后按时间戳合并排序。
    """
    scene_kept = _dedup_within(scene_frames, SCENE_HASH_THRESHOLD)
    interval_kept = _dedup_within(interval_frames, INTERVAL_HASH_THRESHOLD)
    merged = scene_kept + interval_kept
    merged.sort(key=lambda f: f.timestamp)
    return merged


def extract_all(video_path: str, out_dir: str,
                scene_threshold: float = 0.3, interval_s: int = 30) -> list[Frame]:
    """完整抽帧:场景切换 + 定时补抽 → 分流去重 → 按时间排序。"""
    scene = extract_scene_frames(video_path, out_dir, scene_threshold)
    interval = extract_interval_frames(video_path, out_dir, interval_s)
    return dedup_frames(scene, interval)
