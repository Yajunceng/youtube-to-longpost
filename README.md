# youtube-to-longpost (Hermes Agent Skill)

把 YouTube 视频转成推特纯文本长文。**读画面**(教程的操作步骤/界面/数字在画面上,字幕没有),不只是字幕。

## 安装

本仓库整体就是一个 Hermes skill(`SKILL.md` 在仓库根)。两种装法:

**A. 从 GitHub 链接安装**(若你的 Hermes 支持从 Git URL 拉取 skill):
直接把本仓库地址交给 Hermes 安装:
```
https://github.com/Yajunceng/youtube-to-longpost
```

**B. 手动放进 skills 目录**:把整个仓库克隆/下载下来,放到 Hermes 的 `skills/` 下,目录名用 `youtube-to-longpost`:
```
skills/
└── youtube-to-longpost/     # = 本仓库根
    ├── SKILL.md
    └── scripts/
        ├── setup.sh
        ├── requirements.txt
        └── yt2post/         # 备料逻辑(下载/字幕/Whisper/抽帧/打包)
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

详见 `scripts/yt2post/` 各模块 docstring。关键决定:skill 只做"备料"(本地、免费、agent 干不了的体力活),"看图写文"留给 agent。
