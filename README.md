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

### 首次推送到 GitHub（只做一次）

```bash
python3 setup_github.py            # macOS / Linux
python  setup_github.py            # Windows
```

脚本会请你粘贴一次 Token（输入时不显示），然后自动完成：
验证 Token → 建仓库 → 推送 → 把 Token 写进 shell 配置 → 验证配额。

| 选项 | 作用 |
|---|---|
| `--repo 名字` | 改仓库名，默认 `github-viral-producer` |
| `--private` | 建私有仓库（默认公开，见下方说明） |
| `--skip-token-save` | 只推送，不写入 shell 配置 |

推送前会自动扫描，一旦发现 PDF / Pages / MP4 将被上传就**中止**，防止误传私有资产。

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

## ✅ 关于仓库可见性：现在可以放心 Public

仓库**已经不含任何私有资产**，所以 Public / Private 随你选。

| 内容 | 在哪 | 是否进 git |
|---|---|---|
| `相关参考提示词/`（5 个 PDF / Pages） | 只在你本机 | ❌ **已排除**（`.gitignore`） |
| `参考视频/`（2 个 mp4） | 只在你本机 | ❌ **已排除**（`.gitignore`） |
| `.workbuddy/cache/`（视频抽帧图等） | 只在你本机 | ❌ **已排除**（他人视频的衍生内容，有版权） |
| `skills/` `expert/` `bootstrap/`（方法论） | 仓库 | ✅ 可公开 |
| `output/`（成稿） | 仓库 | ✅ 你自己的内容 |

**私有资产怎么换机带走**：跑 `python3 pack_knowledge.py` 打包成
`dist/knowledge-kit-日期.zip`（约 4 MB，含提示词原文 + 参考视频），
走网盘 / 移动硬盘 / iCloud 单独拷贝，换机解压到工作区根目录即可。
加 `--icloud` 可直接复制一份到 iCloud Drive。

已扫描确认：仓库内 **0 个** PDF/Pages/MP4、**0 张**视频抽帧图、**0 处**本机绝对路径、
**0 个**真实密钥。（文档里出现的 `ghp_你的Token` 是示例占位，不是真密钥。）

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
├── pack_knowledge.py              打包私有知识库（PDF + 视频，不进 git）
└── .workbuddy/
    ├── cache/                     可重建缓存（提示词提取件、视频抽帧）
    └── memory/                    工作日志（不进 git）
```

### 三个脚本各自干什么

| 脚本 | 用在哪 | 做什么 |
|---|---|---|
| `install.py` | 换了新电脑，从 git 恢复 | 装 5 个技能到 `~/.workbuddy/skills/` + 写回本机路径 |
| `sync.py`（在专家包内） | 导入专家包后 | 把专家包自带技能的占位符写成这台机器的真实值 |
| `build_expert.py` | 改了 `skills/` 之后 | 从占位符版重建 `dist/*.zip` |
| `pack_knowledge.py` | 换机 / 备份时 | 把提示词原文 + 参考视频打包带走（不进 git） |

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

   Token 在 https://github.com/settings/tokens 生成：

   | 你要做什么 | 勾选什么 |
   |---|---|
   | 只让抓取脚本不限流 | **一个都不勾**（最安全，只读公开信息够用） |
   | 还要用 `setup_github.py` 推送代码 | 勾 **repo** |

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
| GITHUB_TOKEN | ❌ 未配（`setup_github.py` 会顺带配好） |
| git 身份 | ✅ TianLeung <tianleung65367@gmail.com> |
| 推送到 GitHub | ⏳ 待执行 `setup_github.py` |

---

## 内置的四条踩坑规则（改动 Skill 时勿删）

1. **纯 topic 锁定会 100% 漏掉爆款**：新仓库普遍没打标签，实测 `topic:webui` 捞到的全是 2~5 Star 玩具，
   而 600+ Star 的真爆款 topics 全是空数组 → 必须用 `hybrid` 双通道（热度捞池 + UI 打分排序）。
2. **GitHub Search API 操作符上限 5 个**：`AND/OR/NOT` 总数 > 5 直接 422 → 按 topic 分批请求再合并。
3. **上镜评分 ≠ 大众适配度**：评分只回答"有没有界面"，不回答"普通人用不用得上"。
   禁止直接取 Star 最高或评分最高当选题。
4. **无 UI 项目的爽点必须平移**：禁止按"打开界面→点这里"拍，改用
   Before/After 同屏对比 / 终端命令→产物闪现 / 产物特写慢扫。
