"""打包素材给 agent —— skill 不生成长文,产出"素材包"交给 Hermes 写。

架构决定(2026-06-09):skill 的最终产物【不是一篇长文】,而是一个素材包目录:
  package/
    transcript.txt          按时间排好的完整字幕
    frames/*.jpg            去重后的关键帧
    manifest.json           每帧的路径/时间戳/对应字幕窗口
    AGENT_INSTRUCTIONS.md   给 agent 的指令:逐张看图、结合字幕、写纯文本长文

Hermes 拿到包,用自己的 vision_analyze 逐张看帧,结合字幕窗口,写出长文。
skill 不调 LLM、不需 API key。

输出规格(用户已定,写进给 agent 的指令):一整篇【纯文本】长文,
钩子开头、自然分段、结尾带原链接、【无 markdown 标记】。
"""
from __future__ import annotations
import json
import os
from .transcript import Segment, join_text
from .vision import FrameMaterial

# TODO:确认 X 长文字符上限后填入(开放问题 5)。None = 暂不限制,由 agent 自行把握。
X_LONGPOST_CHAR_LIMIT = None


AGENT_INSTRUCTIONS_TEMPLATE = """# 任务:把这个 YouTube 视频转成一篇推特长文

原视频:{url}
{limit_line}
## 你手上的素材
- `transcript.txt`:视频完整字幕(已按时间排好序)。
- `frames/`:从视频里抽出的关键帧(教程的关键操作/界面/数字多在画面上,字幕没有)。
- `manifest.json`:每张帧的时间戳 + 对应那一刻前后的字幕窗口(`subtitle_window`)+
  来源(`source`: scene=画面切换 / interval=定时补抽)+ `likely_redundant`(脚本用
  图像哈希预判该帧是否与前一张近重复)。

## 怎么做
1. 先通读 `transcript.txt`,掌握整体逻辑。
2. 智能选帧看图(别无脑全看):
   - `source: scene` 的帧全部细看(画面真切换,最可能有干货)。
   - `source: interval` 的帧:`likely_redundant: true` 可跳过,`false` 才细看。
   用你的看图能力看选中的帧,结合它对应的 `subtitle_window`(讲者在这一页前后说的话)
   理解画面在讲什么——重点抓:操作步骤、界面元素、图表数字、代码/命令。这些是字幕里没有的干货。
3. 把"口播逻辑"和"画面里的关键信息"缝成一篇连贯长文。

## 输出要求(严格遵守)
- 一整篇【纯文本】,不是 thread、不是要点列表。
- 第一句是吸引人的钩子。
- 自然分段(段落间空行)。
- 【不要】任何 markdown 标记(不要 # ## ** - ` 等符号)。
- 结尾附上原视频链接:{url}
- 忠于内容:画面里读不清或不确定的数字/文字,不要编造,宁可不写。
"""


def build_package(out_dir: str, video_url: str,
                  segments: list[Segment], materials: list[FrameMaterial]) -> str:
    """把字幕 + 帧素材打包成给 agent 的目录。返回包路径。"""
    os.makedirs(out_dir, exist_ok=True)

    # 1. 字幕全文
    with open(os.path.join(out_dir, "transcript.txt"), "w") as f:
        f.write(join_text(segments))

    # 2. manifest:帧路径 + 时间戳 + 字幕窗口
    manifest = {
        "video_url": video_url,
        "frame_count": len(materials),
        "frames": [m.to_dict() for m in materials],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 3. 给 agent 的指令
    limit_line = (
        f"\n字数上限:{X_LONGPOST_CHAR_LIMIT} 字以内。\n"
        if X_LONGPOST_CHAR_LIMIT else ""
    )
    instructions = AGENT_INSTRUCTIONS_TEMPLATE.format(url=video_url, limit_line=limit_line)
    with open(os.path.join(out_dir, "AGENT_INSTRUCTIONS.md"), "w") as f:
        f.write(instructions)

    return out_dir
