# 开源爆款短视频制片人 · 爆导

把 GitHub 上新爆的开源项目，自动洗稿成可直接开拍的短视频分镜脚本。

## 类型

Agent 型（单个 AI 专家） · 行业分类：内容创作（06-ContentCreative）

## 自带的能力（5 个 Skill）

| Skill | 中文名 | 负责什么 |
|---|---|---|
| `github-trend-radar` | GitHub 爆款雷达 | 抓近 N 天新爆项目，双通道过滤 + 上镜评分 |
| `resonance-engine` | 核心共鸣洗稿引擎 | 三步洗稿：人群锚定 → 痛点反推 → 说人话渲染 |
| `opensource-video-director` | 开源爆款编导 | 三要素分镜表（时间节点/画面+视觉标注/口播） |
| `colloquial-polisher` | 口语化抛光师 | 去 AI 味，只改口播列，结构不变 |
| `github-viral-pipeline` | 生产线总控 | 串联以上四步 + 语速校验 + 落盘 |

## 使用示例

- 帮我抓最近 7 天爆火的开源项目，挑最适合大众的一个，写一份能直接开拍的短视频分镜脚本。
- 照这个 GitHub 项目链接，给我出一版完整的短视频分镜脚本。
- 把这份脚本的口播去一遍 AI 味，并做 4 字/秒语速校验。

## ⚠️ 换电脑 / 换目录后必做一件事

专家包里的 Skill 用 `{{WORKSPACE}}` / `{{SKILLS_DIR}}` / `{{PYTHON}}` 三个占位符代替了写死的路径，
导入后需要跑一次自愈脚本，把它们替换成这台机器的真实值：

```bash
# macOS / Linux
python3 sync.py --workspace /你的/工作区/路径

# Windows
python sync.py --workspace C:\你的\工作区\路径
```

不加 `--workspace` 就默认用专家包内置的 `workspace/`。
跑完会报告：Python 命令、Skills 目录、工作区、知识库是否就位、残留占位符数量。**残留必须是 0。**

## 数据流（决定产出风格，可整体替换）

工作区下这两个文件夹是"数据流"，换赛道只需换掉它们，5 个 Skill 一个字都不用改：

- `相关参考提示词/` — 洗稿公式、文案语感、标题库、钩子库
- `参考视频/` — 对标爆款视频，用于拆分镜骨架

空着也能跑，但产出会退化成通用分镜，不是这套打法的分镜。

## 建议配置 GITHUB_TOKEN

不配能跑，但限流 60 次/小时（按出口 IP 共享，容易打满）；配后 5000 次/小时，
且能开启 `--deep` 深度模式（读 README 判断有没有截图，打分更准）。

生成地址：https://github.com/settings/tokens （无需勾选任何 scope）

- macOS / Linux：`echo 'export GITHUB_TOKEN=ghp_你的Token' >> ~/.zshrc && source ~/.zshrc`
- Windows（PowerShell）：`[Environment]::SetEnvironmentVariable("GITHUB_TOKEN","ghp_你的Token","User")`

## 头像

头像在 `avatars/expert.png`（512×512，PNG）。可手动替换，要求：PNG/JPG、512×512、≤500KB。

## 安装

将专家包目录放到专家目录下：

```
~/.workbuddy/plugins/marketplaces/my-experts/plugins/github-viral-producer/
```

然后运行注册命令使其可见：

```bash
python3 scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
zip -r github-viral-producer.zip github-viral-producer/
```

> 注意：如果 `workspace/` 里放了你的提示词原文和参考视频，打包前先清空，别把它们分享出去。
