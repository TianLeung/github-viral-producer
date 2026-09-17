# GitHub 开源爆款短视频生产线 v2

把「GitHub 上新爆的开源项目」自动变成「可直接开拍的短视频分镜脚本」。
已实跑 4 个真实项目：Mac-Duo、truanayangi、PRINTFILM、gongwen-gbt9704-skill。

**✅ 支持 macOS / Windows 双平台**：`install.py` 会自动识别系统、找到 WorkBuddy 技能目录、
把 `python3`/路径/盘符等平台差异一次写对。换电脑只需 clone + 跑一条命令。

**✅ 已打包成 WorkBuddy 专家「爆导」**：也可以不 clone，直接导入
`dist/github-viral-producer.zip`，专家自带全部 5 个技能。详见下方「换电脑的两条路」。

---

## 换电脑的两条路（选一条）

### 路径 A：导入专家包（推荐，最快，不需要 git）

1. 下载 `dist/github-viral-producer.zip`
2. WorkBuddy → 专家中心 → 我的专家 → **导入**这个 zip
3. 让 AI 跑一次专家包里的 `sync.py`（把路径占位符写成这台机器的真实值）
   ```bash
   python3 sync.py --workspace /你的/工作区    # macOS / Linux
   python  sync.py --workspace C:\你的\工作区  # Windows
   ```
4. 把提示词原文和参考视频放进工作区的 `相关参考提示词/`、`参考视频/`

专家自带全部 5 个技能，导入即用。**专家包是"成品快照"**。

### 路径 B：从 GitHub 拉（要最新版 / 要改代码 / 要回滚时）

```bash
git clone <你的私有仓库> <任意目录>
cd <该目录>
python3 install.py      # macOS / Linux
python  install.py      # Windows
```

或者在 WorkBuddy 里装一个种子技能 `bootstrap/viral-producer-sync/`，
之后说一句「同步一下生产线」它就会自动 clone / pull + 安装。

**git 仓库是"源"**：能拿到最新改动、能回滚（Skill 已改过 4 次）。

> 两条路的关系：日常用 A，改坏了或要升级用 B。

---

## 🔴 上传前必读：这个仓库必须设为 Private

| 内容 | 敏感性 |
|---|---|
| `相关参考提示词/`（5 个 PDF / Pages） | **付费或私有知识资产，禁止公开** |
| `参考视频/`（2 个 mp4） | **他人爆款视频，有版权，禁止公开** |
| `skills/`（5 个技能） | 纯方法论，可公开 |
| `output/`（成稿） | 自有内容，自选 |

创建仓库时务必选 **Private**。

---

## 目录结构（控制流 / 数据流分离）

```
.
├── skills/                     ← 控制流：固定流程，不随赛道变
│   ├── github-trend-radar/        数据源（含 scripts/fetch_trending.py）
│   ├── resonance-engine/          核心共鸣洗稿引擎（三步洗稿 + 逻辑平移）
│   ├── opensource-video-director/ 开源爆款编导（出三要素分镜表）
│   ├── colloquial-polisher/       口语化抛光师（只润色口播列）
│   └── github-viral-pipeline/     编排总控
├── expert/                     ← 专家包源码「占位符版」，用于重建 zip
│   └── github-viral-producer/     含 plugin.json / agents / avatars / sync.py
├── bootstrap/                  ← 种子技能：换机时装这一个，自动拉回全套
│   └── viral-producer-sync/
├── dist/                       ← 构建产物：可直接导入的专家包 zip
│   └── github-viral-producer.zip
├── 相关参考提示词/              ← 数据流：换赛道时替换这里
├── 参考视频/                    ← 数据流：换赛道时替换这里
├── output/                        成稿（YYYY-MM-DD-项目名-短视频脚本.md）
├── 自动化配置清单.md              WorkBuddy Automation 的 UI 配置步骤
├── install.py                     跨平台安装器（单一实现）
├── install.sh                     薄封装，仅 macOS / Linux
├── build_expert.py                重建专家包 zip
└── .workbuddy/
    ├── cache/                     可重建缓存（提示词提取件、视频抽帧）
    └── memory/                    工作日志
```

### 三个脚本各自干什么

| 脚本 | 用在哪 | 做什么 |
|---|---|---|
| `install.py` | 换了新电脑，从 git 恢复 | 装 5 个技能到 `~/.workbuddy/skills/` + 写回本机路径 |
| `sync.py`（在专家包内） | 导入专家包后 | 把专家包自带技能的占位符写成这台机器的真实值 |
| `build_expert.py` | 改了 `skills/` 之后 | 从占位符版重建 `dist/*.zip` |

> ⚠️ 别直接打包 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/` 里那份——
> 它已被 `sync.py` 写死本机路径，换台电脑全错。必须走 `build_expert.py` 重建。

**换赛道（比如从开源工具改成 AI 绘画）**：只替换 `相关参考提示词/` 和 `参考视频/`，
删掉 `.workbuddy/cache/` 让它重新提取，5 个 Skill 一个字都不用改。

---

## 换电脑恢复（macOS / Windows 通用，3 步）

```bash
# 第 1 步：把私有仓库拉到任意目录
git clone <你的私有仓库> <任意目录>
cd <该目录>

# 第 2 步：装（二选一，效果完全一样）
python3 install.py      # macOS / Linux（Windows 一般是 python install.py）
./install.sh            # 仅 macOS / Linux，是 install.py 的薄封装

# Windows 专用
python install.py
```

`install.py` 是**跨平台单一实现**，会自动：

1. 识别 Windows / macOS / Linux，找到 WorkBuddy 的技能目录
   （优先读 `WORKBUDDY_CONFIG_DIR` 环境变量，未设置则用 `~/.workbuddy/skills`）
2. 把 5 个技能装进去
3. 把三个占位符替换成**本机真实值**：

| 占位符 | 替换成 | 为什么需要 |
|---|---|---|
| `{{WORKSPACE}}` | 当前仓库的绝对路径 | 换机后路径变了 |
| `{{SKILLS_DIR}}` | 本机技能目录（Windows 带盘符） | 避免 Windows 上 `~/` 解析出错 |
| `{{PYTHON}}` | `python3` / `python` / `py` | Windows 通常没有 `python3` |

4. 给抓取脚本加执行权限（Windows 跳过）、检查 Token 与数据流是否齐全

> **Windows 用户注意**：仓库里的 `install.sh` 是 bash 脚本，在 Windows 上**跑不了**，
> 请一律用 `python install.py`。抓取脚本 `fetch_trending.py` 只用 Python 标准库，本身跨平台。

**换机后还要手动做两件事**（不会随仓库迁移）：

1. 重配 `GITHUB_TOKEN`

   **macOS / Linux**
   ```bash
   echo 'export GITHUB_TOKEN=ghp_你的Token' >> ~/.zshrc && source ~/.zshrc
   ```

   **Windows（PowerShell）**
   ```powershell
   [Environment]::SetEnvironmentVariable('GITHUB_TOKEN','ghp_你的Token','User')
   ```
   配置后需**重启 WorkBuddy** 才会读到。

   Token 在 https://github.com/settings/tokens 生成，**无需勾选任何 scope**。
   不配也能跑，但限流 60 次/小时（按出口 IP 共享，容易打满），配后 5000 次/小时。

2. 在 WorkBuddy UI 重建 Automation 定时任务
   照 `自动化配置清单.md` 点，约 2 分钟。推荐每周一三五 10:00（cron `0 10 * * 1,3,5`）。

---

## 使用

在 WorkBuddy 里直接说：

- 「跑一遍爆款生产线」——抓最新热门 → 洗稿 → 出分镜 → 落盘
- 「处理某某项目」——指定项目跳过嗅探，直接创作

---

## 当前状态（2026-09-17）

| | 状态 |
|---|---|
| 5 个技能 + 抓取脚本 | ✅ 已跑通 |
| 洗稿 → 分镜 → 抛光 → 落盘 | ✅ 4 个真实项目验证 |
| 语速校验（4 字/秒） | ✅ 已脚本化 |
| 定时任务 Automation | ❌ 未建（需在 WorkBuddy UI 手动建，见配置清单） |
| 推送到微信 / 飞书 | ❌ 未接，目前只落盘本地 md |
| GITHUB_TOKEN | ❌ 未配 |

---

## 内置的四条踩坑规则（改动 Skill 时勿删）

1. **纯 topic 锁定会 100% 漏掉爆款**：新仓库普遍没打标签，实测 `topic:webui` 捞到的全是 2~5 Star 玩具，
   而 600+ Star 的真爆款 topics 全是空数组 → 必须用 `hybrid` 双通道（热度捞池 + UI 打分排序）。
2. **GitHub Search API 操作符上限 5 个**：`AND/OR/NOT` 总数 > 5 直接 422 → 按 topic 分批请求再合并。
3. **上镜评分 ≠ 大众适配度**：评分只回答"有没有界面"，不回答"普通人用不用得上"。
   禁止直接取 Star 最高或评分最高当选题。
4. **无 UI 项目的爽点必须平移**：禁止按"打开界面→点这里"拍，改用
   Before/After 同屏对比 / 终端命令→产物闪现 / 产物特写慢扫。
