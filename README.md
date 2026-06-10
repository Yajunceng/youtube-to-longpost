# yt2post — YouTube 视频 → 推特纯文本长文

把一个 YouTube 视频(尤其是教程/讲解类)转成一篇适合发推特的**纯文本长文**草稿,自己再改。

> 设计文档(含实测数据与决策记录):
> `~/.gstack/projects/garrytan-gstack/cengyajun-unknown-design-20260609-180533.md`

## 现状

| 模块 | 状态 |
|---|---|
| 字幕抓取(`transcript.py`) | ✅ 已验证跑通(含按时间戳排序修复) |
| 无字幕→Whisper 转写(`transcribe.py`) | ✅ 已验证跑通(faster-whisper) |
| 抽帧 + 去重(`frames.py`) | ✅ 已实现并用真实视频验证(scene@0.3 + 定时补抽 + 分流去重) |
| 配字幕窗口(`vision.py`) | ✅ 已实现(为每帧配前5后15秒字幕,不调 API) |
| 打包给 agent(`compose.py`) | ✅ 已实现(输出素材包,交 Hermes 写长文) |

## 安装

```bash
cd ~/youtube-to-longpost
python3 -m pip install -r requirements.txt
# 系统依赖:ffmpeg（macOS）
brew install ffmpeg
# 可选:预下载 Whisper 模型，避免首次使用等 8 分钟
python3 -c "from yt2post.transcribe import prefetch_model; prefetch_model()"
```

## 现在能用的

```bash
# 抓字幕（无字幕自动回退 Whisper），输出排好序的纯文本文字记录
python3 -m yt2post.cli "https://www.youtube.com/watch?v=VIDEO_ID" --transcript-only

# 指定字幕语言优先级
python3 -m yt2post.cli "<url>" --transcript-only --lang zh-CN --lang en

# 无字幕视频，给术语表纠正 Whisper 专有名词
python3 -m yt2post.cli "<url>" --transcript-only --terms "Codex, Anthropic, Claude Code"
```

## 实测教训（已写进代码注释）

1. **字幕片段会乱序**——必须按 `start` 排序，否则开头变结尾。
2. **Whisper 慢的是首次下模型(~8min)，不是每次转写**(60s 音频转 7s)。用 `prefetch_model` 预下。
3. **Whisper 会自信地转错专有名词**(Anthropic→Anthopica)——用 `--terms` 喂术语表，且需人工核对。
4. **教程视频价值多在画面**——纯字幕只够概览，读画面是这工具的核心(待实现)。

## 下一步

见设计文档 Next Steps：确认 X 字符上限 → 抽帧调参 → 接多模态 → 融合生成。
