"""打包素材给 agent —— skill 不生成长文,产出"素材包"交给 Hermes 写。

架构决定(2026-06-09):skill 的最终产物【不是一篇长文】,而是一个素材包目录:
  package/
    transcript.txt          按时间排好的完整字幕
    frames/*.jpg            去重后的关键帧
    manifest.json           每帧的路径/时间戳/对应字幕窗口
    AGENT_INSTRUCTIONS.md   给 agent 的指令:逐张看图、结合字幕、写纯文本长文

Hermes 拿到包,用自己的 vision_analyze 逐张看帧,结合字幕窗口,写出长文。
skill 不调 LLM、不需 API key。

输出规格(用户已定,写进给 agent 的指令):一篇可直接发 X Premium 的长文,
【叙事+干货平衡】风格——讲故事的口吻、有钩子有观点、数字编号分节,但保留所有关键
干货(具体数字/专有名词/易错点);适量 emoji、结尾带原链接 + 3-5 个话题标签、
【不要 markdown 标记】。
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
2. 看帧:`frames/` 里的帧【尽量都看】,尤其 `source: scene`(画面切换)的帧必看。
   `source: interval` 且 `likely_redundant: true` 的帧若与前一张确实雷同可略过,
   但只要画面有新内容(新界面/新数字/新步骤)就要看。宁可多看,别漏干货。
   结合每帧的 `subtitle_window`(讲者在这一页前后说的话)理解画面——
   重点抓:操作步骤、界面元素、图表数字、代码/命令。这些是字幕里没有的干货。
3. 把"口播逻辑"和"画面里的关键信息",用【讲故事的口吻】缝成一篇连贯长文(见下方风格要求)。

## 输出要求(严格遵守)
直接产出一篇【能复制粘贴到 X(推特)就发的长文】,面向 X Premium 长文(单条上限 25000 字)。

【风格:叙事+干货平衡】这是最重要的一条。不要写成"背景→优点列表→工具清单→分步骤"的说明书,
要像一个懂行的人在跟朋友讲一件事的来龙去脉。具体:
- 开头用一个有张力的钩子或场景切入,先勾住人,不要一上来就介绍产品。
  好钩子示范:"想长期保一个海外手机号,现在越来越难了。" / "一个被基金会开除的程序员,3 个月写出了改变行业的东西。"
  反例(别这样):"本视频介绍如何申请 giffgaff eSIM。"
- 有"我带你看懂这件事"的视角和判断,而不是中立的步骤罗列。该下结论时下结论(哪种方案更值、坑在哪)。
- 用数字编号分节(1、2、3…)推进叙事,每节讲清一个"为什么/怎么样",而不是机械列步骤。
- 关键干货【必须保留】,别为了顺滑牺牲细节:具体数字、专有名词、易错点(如激活码前加大写 LPA、175 天保号提醒、+44 去掉开头 0 等),这些正是读者照做时最需要的。
- 把操作步骤【融进叙事】:不要写成"第一步…第二步…"的清单,而是讲"你会先…然后卡在…这时要…"。

【格式】
- 一整篇连贯长文,不是 thread、不是要点列表。
- 自然分段(段落间空行)。段落内可用少量 emoji 做重点标记或视觉分隔,别堆砌(全篇适量,服务可读性而非卖萌)。
- 结尾依次:① 原视频链接:{url} ② 另起一行放 3-5 个相关话题标签(形如 #海外手机卡 #eSIM,中英文均可,贴合主题、利于曝光)。
- 【不要】任何 markdown 标记:不要 # 标题、不要 **加粗**、不要 - 列表、不要 ` 代码符号。
  原因:X 不渲染 markdown,这些符号会原样显示成乱码。
  注意:emoji 和结尾的 #话题标签 是 X 原生语法、不是 markdown,允许使用。数字编号"1、2、"是正文不是 markdown,允许。
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
