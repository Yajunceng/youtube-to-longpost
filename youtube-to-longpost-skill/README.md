# youtube-to-longpost (Hermes Agent Skill)

把 YouTube 视频转成推特纯文本长文。**读画面**(教程的操作步骤/界面/数字在画面上,字幕没有),不只是字幕。

## 安装

把整个 `youtube-to-longpost-skill/` 目录放进 Hermes 的 `skills/` 下(可按分类归入子目录,如 `skills/content/`):

```
skills/
└── youtube-to-longpost/
    ├── SKILL.md
    └── scripts/
        ├── setup.sh
        ├── requirements.txt
        └── yt2post/        # 备料逻辑(下载/字幕/Whisper/抽帧/打包)
```

首次使用前,让 agent 跑一次环境准备:

```
bash ${HERMES_SKILL_DIR}/scripts/setup.sh
```

需要系统装好 `ffmpeg`(macOS: `brew install ffmpeg`)。

## 用法

对 Hermes 说:"用 youtube-to-longpost 把这个视频转成推特长文:<URL>"

Agent 会:
1. 跑备料脚本生成素材包(字幕 + 关键帧 + 每帧字幕窗口)
2. 用自己的 `vision_analyze` 逐帧看图
3. 结合字幕写出纯文本长文

**不需要外部 API key** —— 看图用 agent 自带的多模态能力。

## 设计

详见仓库根的设计文档与 `yt2post/` 各模块 docstring。关键决定:skill 只做"备料"(本地、免费、agent 干不了的体力活),"看图写文"留给 agent。
