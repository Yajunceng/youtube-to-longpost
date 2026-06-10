---
name: youtube-to-longpost
description: 把 YouTube 视频(尤其教程/讲解类)转成一篇适合发推特的纯文本长文,读画面里的关键信息而不只是字幕
version: 1.0.0
author: cengyajun
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [YouTube, Video, Transcription, Content, Twitter, Vision, Summary]
    requires_tools: [vision_analyze, terminal]
    config:
      - key: youtube_to_longpost.scene_threshold
        description: "场景切换抽帧阈值,低则帧多(成本高)高则可能漏切页"
        default: "0.3"
        prompt: "抽帧场景阈值(默认 0.3)"
      - key: youtube_to_longpost.interval
        description: "定时补抽间隔秒,兜底同页渐进揭示的信息"
        default: "30"
        prompt: "定时补抽间隔秒(默认 30)"
      - key: youtube_to_longpost.char_limit
        description: "长文字数上限。X Premium 长文上限 25000,免费账号仅 280。默认 8000"
        default: "8000"
        prompt: "长文字数上限(默认 8000,适配 X Premium)"
---

# YouTube 视频 → 推特纯文本长文

把一个 YouTube 视频转成一篇可以直接发推特的纯文本长文草稿。核心价值:**教程/讲解类视频的关键信息(操作步骤、界面、图表数字、代码命令)大多在画面上,字幕里没有**。这个 skill 让你既读口播又读画面,缝成一篇完整长文。

## 分工(重要)

这个 skill 把工作分成两半:

- **备料脚本(Python,本地跑,免费)**:下视频、抓字幕(无字幕自动用 Whisper 转写)、抽关键帧、去重、给每帧配好对应时间的字幕窗口,打包成一个素材包目录。
- **你(agent,用自己的 vision 能力)**:看素材包里的关键帧,结合每帧的字幕窗口,写出最终长文。**不需要任何外部 API key** —— 看图用你自己的 `vision_analyze`。

## When to Use

当用户给你一个 YouTube 链接,并希望:
- 把视频内容改写成推特长文/帖子
- 提取教程视频里的操作步骤(这些在画面上,光看字幕会漏)
- 把讲解/数据演示类视频总结成文字,且要包含画面里的图表数字

## Procedure

### 第 0 步(仅首次):准备环境

```
bash ${HERMES_SKILL_DIR}/scripts/setup.sh
```

装 Python 依赖并检查 ffmpeg。若提示缺 ffmpeg,在 macOS 上运行 `brew install ffmpeg` 后重试。

### 第 1 步:跑备料脚本,生成素材包

```
cd ${HERMES_SKILL_DIR}/scripts && python3 -m yt2post.cli "<视频URL>"
```

可选参数:
- `--lang zh-CN --lang en`:字幕语言优先级
- `--terms "Codex, Anthropic, Claude Code"`:无字幕走 Whisper 时,喂术语表纠正专有名词(Whisper 会把 Anthropic 转成 Anthopica,务必对技术视频用此参数)
- `--scene-threshold 0.3` / `--interval 30`:抽帧调参

脚本结束会打印素材包路径,形如:`output/<视频id>_package/`,内含:
- `transcript.txt` —— 按时间排好序的完整字幕
- `frames/` —— 去重后的关键帧图片
- `manifest.json` —— 每帧的 `image_path` / `timestamp` / `subtitle_window`(该帧前后的字幕)
- `AGENT_INSTRUCTIONS.md` —— 写长文的详细要求

### 第 2 步:读素材包

1. 读 `manifest.json` 拿到帧列表和每帧的字幕窗口。
2. 读 `transcript.txt` 掌握整体逻辑。
3. 读 `AGENT_INSTRUCTIONS.md` 确认输出要求。

### 第 3 步:智能选帧看图(用你的 vision 能力)

**不要无脑对 70+ 帧全部调一次 `vision_analyze`** —— 长视频可能上百帧,每帧一次调用,成本和时间都很高,而其中很多帧是讲者还停在同一页、没有新画面信息的"水帧"。

按帧的 `source` 字段分层处理(这个判断**只看画面变化,不看字幕**——因为本 skill 的前提就是"画面有字幕没有的信息",用字幕判断该不该看会漏掉干货):

1. **`source: "scene"` 帧(画面真切换了)→ 全部细看。** 这些是新页面/新界面/新弹窗,最可能有字幕没有的干货(GitHub 项目页、设置界面、图表、命令行)。逐张 `vision_analyze`。
2. **`source: "interval"` 帧(每 N 秒强制补抽)→ 看 `likely_redundant` 标记决定。** 备料脚本已用图像哈希预判它和前一张已保留帧像不像:
   - `likely_redundant: true` → 大概率讲者还停在同一页,**可直接跳过**,不必调 vision。
   - `likely_redundant: false` → 画面有变化,细看,提取信息。
3. 看图时结合该帧的 `subtitle_window` 理解上下文。重点抓:**操作步骤、界面元素按钮、图表数字、代码/命令**。

读不清或不确定的数字/文字,**不要编造,宁可不写**(画面 OCR 和字幕转写都可能出错)。

> 选帧只是省"重复帧"的钱,**绝不能为省钱跳过 scene 帧或有新内容的帧**——漏看一张关键界面,等于丢掉这个 skill 的核心价值。省成本和不丢信息冲突时,优先不丢信息。

### 第 4 步:写长文

把口播逻辑和画面关键信息缝成一篇连贯长文,严格按 `AGENT_INSTRUCTIONS.md`:
- 一整篇**纯文本**(不是 thread、不是要点列表)
- 第一句是吸引人的钩子
- 自然分段(段落间空行)
- **不要任何 markdown 标记**(不要 # ## ** - ` 等)
- 结尾附原视频链接

## Quick Reference

| 操作 | 命令 |
|---|---|
| 首次装环境 | `bash ${HERMES_SKILL_DIR}/scripts/setup.sh` |
| 生成素材包 | `cd ${HERMES_SKILL_DIR}/scripts && python3 -m yt2post.cli "<URL>"` |
| 只要文字记录 | 加 `--transcript-only` |
| 无字幕技术视频 | 加 `--terms "术语1, 术语2"` |
| 改长文字数上限 | 加 `--char-limit 8000`(X Premium 长文上限 25000,免费账号 280) |

## Pitfalls

- **无字幕视频很常见**:脚本会自动回退 Whisper 转写(首次会下载模型,约几分钟,之后很快)。对技术视频务必用 `--terms` 喂术语表,否则专有名词会转错且读着通顺、难发现。
- **帧数 = 你的看图次数,但别全看**:13 分钟视频约 70 帧,长视频可能上百帧。按第 3 步的分层策略:scene 帧全看,interval 帧粗筛跳过重复的——实测 70 帧里有相当一部分 interval 帧是讲者还在同一页,可跳过。这能把看图次数砍掉不少而几乎不丢信息。源头上也可调高 `--scene-threshold` 或调大 `--interval` 减少帧数(但可能漏切页,慎用)。
- **画面信息会"自信地错"**:多模态读图表数字、字幕转写专有名词,都可能给出读着对实则错的内容。涉及关键数字时标注不确定,别硬编。
- **字幕片段顺序**:脚本已内部按时间戳排序(YouTube 返回的片段可能乱序),你拿到的 transcript.txt 已是正确顺序。

## Verification

- 备料脚本结束应打印 `[完成] 素材包: .../<id>_package`,且该目录下有 `transcript.txt`、`manifest.json`、`AGENT_INSTRUCTIONS.md` 和非空的 `frames/`。
- 最终长文应:无 markdown 符号、含画面里的具体操作/数字(不只是口播能得到的概览)、结尾有原链接。
- 自检:长文里每个具体数字/步骤,是否都能在某一帧或字幕里找到出处?找不到的删掉,别编。
