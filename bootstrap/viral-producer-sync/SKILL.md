---
name: viral-producer-sync
description: |
  开源爆款短视频生产线的「取回 / 更新」入口。从 GitHub 私有仓库把整套产线（5 个 Skill + 抓取脚本 + 知识库）拉回本机并安装，或把本机产线更新到最新版。
  触发词：装一下爆款生产线、取回生产线、同步生产线、更新生产线、从 GitHub 拉生产线、install viral producer、sync viral pipeline。
description_en: |
  Fetch or update the open-source viral short-video production pipeline from its GitHub repository: clones/pulls the private repo and runs the cross-platform installer to restore all skills, scripts and knowledge assets.
---

# 爆款生产线同步器

你是一条**恢复通道**。当用户在换的新电脑、重装系统、或产线被改坏时，用本 Skill 把整套产线从 GitHub 取回来。

整套产线包含：`github-trend-radar`（抓项目）、`resonance-engine`（洗稿）、`opensource-video-director`（分镜）、`colloquial-polisher`（去 AI 味）、`github-viral-pipeline`（总控），以及提示词库和参考视频。

---

## 第 0 步：读配置

先读本 Skill 同目录下的 `config.json`：

```json
{
  "repoUrl": "<你的仓库地址>",
  "branch": "main",
  "localDir": "<本机存放目录>"
}
```

**如果 `repoUrl` 还是占位符**（`<你的仓库地址>`），说明用户还没填。停下来问他两个问题，拿到后**把答案写回 `config.json`**（这样以后不用再问）：

1. 仓库地址是什么？
   - SSH（推荐，配好 key 后永久免密）：`git@github.com:用户名/仓库名.git`
   - HTTPS：`https://github.com/用户名/仓库名.git`
2. 想放在本机哪个目录？（Mac 例：`/Users/xxx/GitHub开源工具内容创作`；Windows 例：`C:\Users\xxx\GitHub开源工具内容创作`）

---

## 第 1 步：检查 git

```bash
git --version
```

- **没有 git** → 别硬来。给用户两条路：
  - Mac：`xcode-select --install`
  - Windows：去 https://git-scm.com 装，或改用**专家包 zip 导入**（不需要 git，见文末"备选通道"）

---

## 第 2 步：取代码

**目录已存在且有 `.git`** → 更新：
```bash
cd "<localDir>" && git pull
```

**目录不存在** → 克隆：
```bash
git clone -b <branch> <repoUrl> "<localDir>"
```

**私有仓库认证失败**（提示 `Permission denied` / `Authentication failed` / 要求输入密码）：

| 用的方式 | 怎么办 |
|---|---|
| SSH | 本机没配 SSH key。生成并加到 GitHub：`ssh-keygen -t ed25519` → 公钥粘到 GitHub Settings → SSH and GPG keys |
| HTTPS | 用 Personal Access Token 拼进 URL：`https://<TOKEN>@github.com/用户名/仓库名.git`。Token 在 https://github.com/settings/tokens 生成，勾 `repo` |

Token 申请地址要直接给用户，不要让他猜。

---

## 第 3 步：安装

```bash
cd "<localDir>"

python3 install.py     # macOS / Linux
python  install.py     # Windows
```

安装器会：识别系统 → 把 5 个技能装进 WorkBuddy 技能目录 → 把路径占位符替换为本机真实值 → 检查 Python / Token / 知识库。

---

## 第 4 步：验收（必须做，别跳过）

1. 看安装器输出：**技能 5 个、无 ERROR**。
2. 确认工作区里 `相关参考提示词/` 和 `参考视频/` 有内容（空的话产出会退化成通用分镜）。
3. 实跑一次抓取决脚本，确认链路活着：
   ```bash
   python3 <技能目录>/github-trend-radar/scripts/fetch_trending.py --days 7 --min-stars 200 --limit 3 --mode hybrid
   ```
   （技能目录：Mac/Linux 是 `~/.workbuddy/skills`，Windows 是 `C:\Users\xxx\.workbuddy\skills`）

---

## 第 5 步：报告

简洁汇报：装了哪 5 个技能、装在哪个目录、工作区在哪、知识库是否就位、Token 是否配置、抓取实测是否通过。
如有缺失项，明确说要补什么、怎么补。

---

## 备选通道：专家包 zip（不需要 git）

如果用户没有 git、或只想最快用上，走这条：

1. 从 GitHub 仓库的 Releases 下载 `github-viral-producer.zip`
2. 在 WorkBuddy「专家中心 → 我的专家」导入该 zip
3. 导入后跑一次专家包里的 `sync.py`（把路径占位符写成这台机器的真实值）
4. 把提示词原文和参考视频放进工作区

**两条通道的关系**：专家包是"成品快照"，导入即可用；git 仓库是"源"，能拿到最新改动、能回滚。日常用专家包，改坏了或要升级时用本 Skill 拉 git。

---

## 注意

- 本 Skill 是**种子**：换电脑时你只需把这一个文件夹放进 WorkBuddy 技能目录，其余全套由它自己拉回来。
- 别把提示词 PDF 和参考视频传进公开仓库——必须是私有仓库。
- `GITHUB_TOKEN` 不随仓库走，换机要重配。
- Automation 定时任务也不随仓库走，换机要在 WorkBuddy UI 重建。
