---
name: github-trend-radar
description: |
  GitHub 爆款项目嗅探器。抓取「最近 N 天内新建、Star 快速上涨、且带可视化界面」的开源项目，
  过滤掉 SDK / library / framework / benchmark / awesome-list 这类"没画面、不好演示"的仓库，
  输出结构化 Markdown 卡片，作为「开源爆款编导」Skill 的输入。
  触发信号：抓 GitHub 新项目 / 找爆款开源 / 今天有什么火的项目 / 短视频选题 / 找能演示的开源工具 /
  GitHub trending / 开源雷达 / 找选题 / scrape github trending。
  不适用：找某个指定名字的仓库（直接用 gh 或网页搜）、要长期历史数据（本技能只看新建仓库）。
metadata:
  agent_created: true
  version: 1
  tags: github, scraping, content-ideation, automation
---

# GitHub 爆款雷达（GitHub Trend Radar）

## 一句话定位

只捞**能上镜**的新项目 —— 有 WebUI / Gradio / Streamlit / 桌面 GUI，打开就能录屏，短视频观众一眼看懂。

## 核心过滤逻辑

### 正向锁定（必须有界面）

| topic | 含义 | 为什么选它 |
|---|---|---|
| `webui` | 网页操作界面 | AI 开源项目最常见的可视化 Demo 形态 |
| `gradio` | Gradio 搭建的 Demo | 一个链接就能演示，录屏友好 |
| `streamlit` | Streamlit 应用 | 数据类项目的标配界面 |
| `gui` | 图形界面 | 排除纯命令行 |
| `desktop-app` | 桌面软件 | 有窗口可录屏 |
| `app` | 独立应用 | 兜底覆盖 |

### 反向剔除（不适合短视频）

- `NOT sdk` / `NOT library` / `NOT framework`：写给程序员调用的底层依赖，没有画面
- `NOT benchmark`：纯跑分仓库，无交互
- `-topic:awesome-list` `-topic:awesome` `-topic:books` `-topic:course` `-topic:tutorial` `-topic:interview`：只整理链接或只做学习资料的"神仙仓库"

### 时间与热度

- `created:>{7天前}`：只看新项目，抢首发红利
- `stars:>200`：证明一周内有爆发趋势，滤掉无人问津的个人 Demo
- `sort=stars&order=desc`：最火的排最前

## ⚠️ 三个必须知道的坑（已内置修复，勿删）

1. **操作符上限 5 个**：GitHub Search API 硬性限制单条 query 里 `AND/OR/NOT` 总数 ≤ 5，
   超出直接 `422 Validation Failed`。
   6 个 topic（5 个 OR）+ 4 个 NOT = 9 → 必然报错。
   **解法**：脚本按 topic 分批请求，每批 topic 数 = `5 - NOT数 + 1`，最后按 Star 合并去重。
2. **限流**：未鉴权 60 次/小时（且按出口 IP 计，共享网络极易被打满）；
   配置免费 Personal Token 后 5000 次/小时。**强烈建议配 Token。**
3. **🔥 新项目普遍没有 topic（最致命，实测确认）**：
   2026-09-14 实测数据 ——
   - `topic:webui created:>2026-09-01` → 23 条，Star 全是 **2~5**
   - `created:>2026-09-10 stars:>100` → 27 条，Star 高达 **646/630/607**，但 `topics` 全是 **空数组**

   **结论**：纯 topic 锁定会把真正的爆款 100% 漏掉，只捞到一堆没人用的玩具。
   所以默认走 **hybrid 双通道**：先用「新建 + 高 Star」捞池子，再用 **UI 启发式打分** 排序。

## 双通道检索（默认 hybrid）

| 通道 | 查询 | 作用 |
|---|---|---|
| **热度通道**（主） | `created:>{7天前} stars:>200 -topic:awesome-list ...` | 保证不漏掉爆款 |
| **topic 通道**（兜底） | `(topic:webui OR topic:gradio) created:>X stars:>Y NOT sdk ...` | 保证"一定有界面"的兜底 |

### UI 启发式打分（判断"能不能上镜"）

| 信号 | 分值 |
|---|---|
| topic 命中 webui/gui/desktop-app/app/gradio/streamlit/menubar-app/electron/tauri 等 | +3/个（上限 +6） |
| 项目名含 webui/-ui/gui/desktop/studio/dashboard/viewer 等 | +2 |
| 简介含 界面/可视化/桌面/客户端/菜单栏/一键部署/run locally 等 | +2/个（上限 +4） |
| 有演示主页 homepage | +1 |
| 语言为 TypeScript/JavaScript/Vue/C#/Swift/Kotlin/Dart | +1 |
| README 含截图或动图（`--deep` 模式） | +2、提到 Demo 再 +1 |
| 命中 sdk/library/framework/benchmark/awesome/论文/面试题 等 | **−5** |

## 使用方法

```bash
# 默认（推荐）：双通道 + UI 打分，近 7 天、stars>200、取 5 个
{{PYTHON}} {{SKILLS_DIR}}/github-trend-radar/scripts/fetch_trending.py

# 深度模式：额外读 README 判断有无截图/Demo，打分更准（每项目多 1 次请求）
{{PYTHON}} scripts/fetch_trending.py --deep

# 只按 topic 锁定（原始方案，会漏掉没打标签的爆款，仅作对照）
{{PYTHON}} scripts/fetch_trending.py --mode topic

# 自定义参数
{{PYTHON}} scripts/fetch_trending.py --days 7 --min-stars 500 --limit 10 --mode hybrid --deep

# 只看查询式，不请求（调试用）
{{PYTHON}} scripts/fetch_trending.py --query-only

# 落盘 + 输出 JSON（给下游程序用）
{{PYTHON}} scripts/fetch_trending.py --out output/radar.md --json
```

### 参数表

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--mode` | `hybrid` | `hybrid`（推荐，热度+UI打分）/ `topic`（纯标签锁定）/ `hot`（纯热度） |
| `--days` | 7 | 时间窗口 |
| `--min-stars` | 200 | Star 下限 |
| `--limit` | 5 | 返回条数 |
| `--min-ui-score` | 2 | 上镜评分门槛（hybrid 生效） |
| `--deep` | 关 | 拉 README 判断截图/Demo，更准但更耗额度 |
| `--topics` | webui,gradio,streamlit,gui,desktop-app,app | 正向锁定（topic 通道用） |
| `--exclude-words` | sdk,library,framework,benchmark | NOT 排除（每个占 1 个操作符名额） |
| `--exclude-topics` | awesome-list,awesome,books,course,tutorial,interview | `-topic:` 排除（不占名额） |
| `--out` | 无 | 落盘路径 |
| `--json` | 关 | 输出原始 JSON |

### Token 配置（按当前系统选一种）

**macOS / Linux**（写入 shell 配置，永久生效）：

```bash
echo 'export GITHUB_TOKEN=ghp_你的Token' >> ~/.zshrc && source ~/.zshrc
```

**Windows**（PowerShell，写入用户环境变量，永久生效）：

```powershell
[Environment]::SetEnvironmentVariable('GITHUB_TOKEN','ghp_你的Token','User')
```

**临时生效（任意系统，仅当前会话）**：

```bash
# macOS / Linux
export GITHUB_TOKEN=ghp_你的Token
```

```powershell
# Windows PowerShell
$env:GITHUB_TOKEN='ghp_你的Token'
```

> Windows 上配置完用户环境变量后需**重启 WorkBuddy**才会读到。

Token 申请：https://github.com/settings/tokens → Generate new token (classic) → **不需要勾选任何 scope** 即可使用搜索 API。

## 输出格式（喂给「开源爆款编导」）

每个项目输出一张卡片：项目名称 / 仓库全名 / 项目地址 / 演示主页 / 一句话介绍 / 实时 Star / 主题标签 / 主要语言 / 创建时间。

## 三级降级策略（保证永远有产出）

1. 严格模式：topic 锁定 + NOT 排除
2. 严格模式 0 结果 → 去掉 NOT 关键词
3. 仍 0 结果 → Star 门槛减半

触发 `403/429` 直接停止并提示配 Token，不做无意义重试。

## 自检（输出前必做 3 行）

1. 结果里有没有明显是 SDK / 库的仓库混进来？有 → 补 `-topic:` 或 `--exclude-words`
2. Star 数和时间窗口是否匹配"近期爆发"？不是 → 调 `--days` / `--min-stars`
3. 返回 0 条时，是先放宽了降级还是真的没有？→ 看输出里的「检索级别」字段
