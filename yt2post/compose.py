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

# X(推特)平台字符上限(2026-06 查证,来源:X 维基/帮助页):
#   - 免费账号:280 字符(发不了真正的长文)
#   - X Premium 长文:25,000 字符(2023 年是 4,000,后提升;X 会不定期调整)
# 默认取一个对长文安全、不贴最高档的值;X 调整上限或换账号档位时,
# 通过 skill config `youtube_to_longpost.char_limit` 覆盖即可,不必改代码。
X_LONGPOST_CHAR_LIMIT_FREE = 280
X_LONGPOST_CHAR_LIMIT_PREMIUM = 25000
# 默认值:发长文意味着用 Premium。取 8000 为保守默认 —— 远低于 25000 上限留出余量,
# 又足够写完一篇有画面细节的教程长文(实测 giffgaff 字幕全文才 ~4200 字,
# 加画面信息后通常也在 8000 内)。可被 --char-limit / config 覆盖。
X_LONGPOST_CHAR_LIMIT = 8000


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
                  segments: list[Segment], materials: list[FrameMaterial],
                  char_limit: int | None = X_LONGPOST_CHAR_LIMIT) -> str:
    """把字幕 + 帧素材打包成给 agent 的目录。返回包路径。

    char_limit: 长文字数上限(默认 8000,适配 X Premium)。None = 不限制。
    """
    os.makedirs(out_dir, exist_ok=True)

    # 1. 字幕全文
    with open(os.path.join(out_dir, "transcript.txt"), "w") as f:
        f.write(join_text(segments))

    # 2. manifest:帧路径 + 时间戳 + 字幕窗口
    manifest = {
        "video_url": video_url,
        "frame_count": len(materials),
        "char_limit": char_limit,
        "frames": [m.to_dict() for m in materials],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 3. 给 agent 的指令
    limit_line = (
        f"\n字数上限:{char_limit} 字以内(超出则压缩,不要截断、不要切成 thread)。\n"
        if char_limit else ""
    )
    instructions = AGENT_INSTRUCTIONS_TEMPLATE.format(url=video_url, limit_line=limit_line)
    with open(os.path.join(out_dir, "AGENT_INSTRUCTIONS.md"), "w") as f:
        f.write(instructions)

    return out_dir
