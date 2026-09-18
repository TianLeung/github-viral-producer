---
name: github-viral-pipeline
description: |
  GitHub 开源爆款短视频生产线总控 v2。四阶段七步：加载本地知识库（提示词矩阵+参考视频骨架）→
  嗅探带界面的新晋热门项目 → 核心共鸣洗稿（逻辑平移+痛点提纯）→ 生成爆款骨架分镜 →
  去 AI 味润色 → 落盘 output/ 并汇报。
  触发信号：跑一遍爆款生产线 / 今天的开源选题 / 全自动生产 / 生成这周的视频脚本 /
  GitHub 爆款流水线 / run the pipeline / 定时抓取并出脚本。
  不适用：只抓数据不出脚本（→ github-trend-radar）、只润色已有稿子（→ colloquial-polisher）。
metadata:
  agent_created: true
  version: 2
  tags: pipeline, orchestration, github, short-video, automation
---

# GitHub 开源爆款短视频生产线 v2（GitHub Viral Pipeline）

## 产线拓扑（控制流固定，数据流可替换）

```
[定时触发]
    ↓
【阶段一 · 学习】Step 0  加载本地知识：./相关参考提示词/ + ./参考视频/ 的拆解缓存
    ↓
【阶段二 · 嗅探】Step 1  github-trend-radar（fetch_trending.py）→ 项目卡片
    ↓          （可选人机协作：推送候选，人工确认后继续）
【阶段三 · 创作】Step 2  resonance-engine        → 《选题提纯单》（三步洗稿+标题+钩子）
    ↓          Step 3  opensource-video-director → 填入爆款骨架，出三要素分镜表
    ↓          Step 4  colloquial-polisher       → 只润色口播文案列
    ↓
【阶段四 · 落盘】Step 5  output/YYYY-MM-DD-开源项目名-短视频脚本.md + 汇报
```

**换赛道迁移**：替换 `相关参考提示词/` 和 `参考视频/` 两个文件夹的内容即可（如改成 AI 绘画工具赛道），
控制流（本 SOP）不变。

## Step 0 · 加载本地知识（每次运行先做）

工作区：`{{WORKSPACE}}`

1. **提示词矩阵**：读 `.workbuddy/cache/prompts-md/` 下的 5 个缓存 md（缺失或源文件更新时重新提取，
   方法见 resonance-engine SKILL.md「本地知识库加载」）。
2. **爆款骨架**：读 `.workbuddy/cache/video-frames/骨架拆解.md`
   （源：`参考视频/*.mp4`，用 ffmpeg 每 4 秒抽帧拼网格图后视觉拆解；`参考视频/` 更新过就重拆）。

## Step 1 · 热点嗅探

```bash
cd "{{WORKSPACE}}"
{{PYTHON}} {{SKILLS_DIR}}/github-trend-radar/scripts/fetch_trending.py \
  --days 7 --min-stars 200 --limit 5 --deep --out output/radar-YYYY-MM-DD.md
```

- 0 条 → 依次放宽 `--days 14` → `--min-stars 50`；仍 0 则汇报"本周无达标项目"，不硬编。
- `403/429` → 提示配 `GITHUB_TOKEN`，不重试。
- **人机协作（可选）**：列出 Top3 一句话介绍，问用户确认哪个进入创作；用户不在场（自动化模式）则按下方裁决规则选。

> ⚠️ **裁决规则：上镜评分 ≠ 大众适配度**（2026-09-14 实测教训，勿回退）
>
> radar 的「上镜评分」只回答「**有没有可视化界面**」，**不回答**「**普通人用不用得上**」。
> 实测：PRINTFILM（完整中文 Web 后台 + 20+ 模板，最适合大众）只得 1 分；
> 而 Edge0（纯 CLI 推理框架、需 Mac M 芯片 + 23GB 模型）以 1668⭐ 排第一。
>
> 因此 **禁止直接取「Star 最高」或「评分最高」当选题**。自动化模式下按序裁决：
> 1. 先剔除「无界面且需专业环境」的（纯 CLI / SDK / 框架 / 论文 / Skill 类）；
> 2. 剩余里取「非程序员能用得上」的（有 Web/桌面界面 + 场景大众）；
> 3. 同档时再比 Star。
> 4. 拿不准就**列出 Top3 让用户选**，不要自己拍板。

## Step 2 · 核心共鸣洗稿

加载 `resonance-engine`，传入项目卡片 → 产出《选题提纯单》（人群锚定 / 惨VS爽痛点 / 三维度选题 / 标题 / 钩子 / 200-300字口播）。

## Step 3 · 爆款骨架分镜

加载 `opensource-video-director`，传入 `project_info` + `topic_brief`（Step 2 产出）→
按八要素骨架生成三要素分镜表（时间节点 / 画面截图与视觉标注 / 口播文案）。

## Step 4 · 去 AI 味

加载 `colloquial-polisher`，整表传入，只改口播文案列。

## Step 5 · 落盘与汇报

```bash
# 命名格式（固定）
output/YYYY-MM-DD-开源项目名-短视频脚本.md
```

成稿结构（从上到下）：视频名片（标题3-5个+封面标题+标签） → 钩子3条 → 分镜表 → 选题提纯单附录。

汇报格式（简洁）：

```
本次命中 N 个项目，主选题：xxx（⭐ 1.2k，上镜评分 7）
- 推荐标题：xxx
- 成稿路径：output/2026-09-14-Mac-Duo-短视频脚本.md
- 备选选题：A / B
```

## 自动化（Automation）任务提示词（自包含，直接复制）

```
执行 GitHub 开源爆款短视频生产线 v2：
1. 读取 {{WORKSPACE}}/
   .workbuddy/cache/ 下的提示词缓存与爆款骨架拆解
2. 运行 {{SKILLS_DIR}}/github-trend-radar/scripts/fetch_trending.py
   --days 7 --min-stars 200 --limit 5 --deep --out output/radar.md
3. 用「核心共鸣洗稿引擎」(resonance-engine) 做三步洗稿过滤，产出选题提纯单
4. 用「开源爆款编导」(opensource-video-director) 按爆款骨架生成分镜表
5. 用「口语化抛光师」(colloquial-polisher) 只润色口播文案列
6. 成稿保存为 output/YYYY-MM-DD-开源项目名-短视频脚本.md，并汇报标题与备选选题
```

## 依赖清单

| 组件 | 路径 | 作用 |
|---|---|---|
| 抓取脚本 | `{{SKILLS_DIR}}/github-trend-radar/scripts/fetch_trending.py` | 数据源 |
| 洗稿引擎 | `{{SKILLS_DIR}}/resonance-engine/SKILL.md` | 选题提纯 |
| 爆款编导 | `{{SKILLS_DIR}}/opensource-video-director/SKILL.md` | 分镜 |
| 抛光师 | `{{SKILLS_DIR}}/colloquial-polisher/SKILL.md` | 润色 |
| 提示词缓存 | `<工作区>/.workbuddy/cache/prompts-md/*.md` | 知识库 |
| 骨架缓存 | `<工作区>/.workbuddy/cache/video-frames/骨架拆解.md` | 分镜模板 |
| 产出目录 | `<工作区>/output/` | 落盘 |

## 已知约束

- **Token 必配**：未配 `GITHUB_TOKEN` 限流 60 次/小时且按出口 IP 共享。
- **操作符上限**：单条 query AND/OR/NOT ≤ 5，脚本已分批规避。
- **默认单选题**：一次只给 Top1 写完整脚本；自动化模式下取"Star 最高且上镜评分 ≥ 4"者。
- **视频拆解工具**：ffmpeg 走 `imageio_ffmpeg.get_ffmpeg_exe()`（venv 内，无需 brew）。
