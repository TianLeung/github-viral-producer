---
name: viral-producer-sync
description: |
  开源爆款短视频生产线的远程取回与执行入口。一句话从 GitHub 仓库下载整套产线（5 个 Skill + 抓取脚本）并安装到本机，然后直接执行：抓项目 → 洗稿 → 出分镜 → 去 AI 味 → 落盘。
  触发词：装一下爆款生产线、取回生产线、同步生产线、更新生产线、从 GitHub 拉生产线、跑一遍爆款生产线、install viral producer、sync viral pipeline。
description_en: |
  Remote installer and runner for the open-source viral short-video pipeline. Downloads the whole pipeline (5 skills + scraper) from GitHub, installs it locally, then executes: fetch trending repos → resonance rewriting → storyboard → de-AI polishing → save to disk.
---

# 爆款生产线 · 远程取回与执行

你是一个**一键通道**：装到任意一台新电脑后，用户说一句话，你就能把整套产线从 GitHub 拉回来、装好、并直接跑出成稿。

整套产线包含 5 个 Skill：`github-trend-radar`（抓项目）、`resonance-engine`（共鸣洗稿）、
`opensource-video-director`（三要素分镜）、`colloquial-polisher`（去 AI 味）、
`github-viral-pipeline`（总控编排）。

---

## 第 0 步：确认配置

读同目录 `config.json`。默认已预置：

```json
{"owner": "TianLeung", "repo": "github-viral-producer", "branch": "main"}
```

- 字段齐全 → 直接进第 1 步，**不要问用户**
- `owner` / `repo` 仍是占位符（含 `<`）→ 才问用户仓库地址，拿到后写回 `config.json`

**重要**：公开仓库下载**不需要任何 Token 或 git**。不要主动索要 Token，除非下载时报 401/403。

---

## 第 1 步：下载并安装（一条命令）

```bash
python3 bootstrap.py        # macOS / Linux
python  bootstrap.py        # Windows
```

`bootstrap.py` 会依次做完：下载 zip → 解压（自动摊平 GitHub 加的顶层目录）→ 跑 `install.py`
→ 实跑一次抓取验收 → 汇报结果。

**可选参数**：

| 参数 | 用在哪 |
|---|---|
| `--dir <路径>` | 指定装到哪（默认用户主目录下同名文件夹） |
| `--token ghp_xxx` | **仅私有仓库**需要 |
| `--force` | 目录已存在时强制重装 |
| `--check` | 只检查现状，不下载 |

**它不依赖 git**，纯 HTTP + Python 标准库，所以 Windows 上没装 git 也能用。

### 出错了怎么办

| 现象 | 原因与处理 |
|---|---|
| `404` | 仓库名或分支不对。确认 `github.com/<owner>/<repo>` 存在；默认分支不是 `main` 就在 config.json 改 `branch` |
| `401` / `403` | 私有仓库。加 `--token`，Token 在 github.com/settings/tokens 生成（勾 repo） |
| 网络超时 | 国内直连可能不稳。挂代理后重试，或改走「备选通道」（见文末） |
| 提示"不是 zip" | 下载到了错误页面。检查仓库地址拼写 |

---

## 第 2 步：执行产线（这是你的活，脚本做不了）

安装完成 ≠ 任务完成。**`bootstrap.py` 只负责把工具装好，创作部分必须由你接手。**

按 `github-viral-pipeline` 的四阶段七步执行：

1. **加载本地知识**：读工作区里 `相关参考提示词/`（洗稿规范和标题钩子库）与
   `参考视频/`（爆款骨架）。若这两个文件夹是空的，明确告诉用户：
   洗稿质量会退化，需要把提示词原文和参考视频放进来。
2. **嗅探**：跑抓取脚本拿候选项目
   ```bash
   python3 <技能目录>/github-trend-radar/scripts/fetch_trending.py \
     --days 7 --min-stars 200 --limit 8 --mode hybrid
   ```
3. **选题裁决**（顺序不能变）：先剔无界面 → 再挑大众向 → 最后才比 Star。
   禁止直接取 Star 最高的当选题。
4. **洗稿**：调 `resonance-engine`，先做本地化障碍检测（语言/区域、运行门槛、数据可达性），
   命中任一条就切到「反常识魔改流」。
5. **分镜**：调 `opensource-video-director`，出三要素表（时间节点 / 画面与视觉标注 / 口播文案）。
   无 UI 项目必须把爽点平移为 Before/After 同屏对比。
6. **抛光**：调 `colloquial-polisher`，只改口播文案列，表格结构零改动。
7. **落盘**：写到工作区 `output/YYYY-MM-DD-项目名-短视频脚本.md`。

**语速校验必须用脚本跑**，不要手算（手算已被验证会出错，曾把 205 字算成 221 字）：

```bash
python3 - <<'PY'
import re
p='output/你的成稿.md'
rows=[l for l in open(p,encoding='utf-8').read().split('\n') if l.startswith('| **') and re.search(r'\d+-\d+s',l)]
tc=ts=bad=0
for l in rows:
    c=[x.strip() for x in l.strip('|').split('|')]
    r=re.search(r'(\d+)-(\d+)s',c[1]); d=int(r.group(2))-int(r.group(1))
    n=len(re.findall(r'[\u4e00-\u9fff]',c[4]))+len(re.findall(r'[A-Za-z]+|\d+',c[4]))
    tc+=n; ts+=d
    if n>d*4: bad+=1; print('超速:',c[0],d,'s',n,'字')
print('镜数 %d｜时长 %ds｜口播 %d字｜均速 %.1f 字/秒｜超速 %d'%(len(rows),ts,tc,tc/ts,bad))
PY
```

---

## 第 3 步：汇报

简洁给出：装了哪 5 个技能、工作区在哪、本轮选题及淘汰理由、成稿路径、
标题与钩子推荐、语速校验结果。有缺失项（知识库空、Token 未配）要明确说怎么补。

---

## 备选通道：专家包 zip（完全不联网也能装）

如果网络不通，或用户手上有 zip：

1. 从仓库的 Releases 下载 `github-viral-producer.zip`
2. WorkBuddy → 专家中心 → 我的专家 → 导入该 zip（专家自带全部 5 个技能）
3. 跑一次专家包里的 `sync.py --workspace <工作区>` 写回路径

**两条通道的关系**：本 Skill 走网络自动拉取，永远拿到最新版；
专家包是离线快照，导入即用。日常用本 Skill，断网或图省事用专家包。

---

## 注意

- 本 Skill 是**种子**：新电脑只需这一个文件夹，其余全套由它自己拉回来。
- 仓库是**公开**的，下载免认证 —— 因为私有资产（提示词原文、参考视频）已剥离，不进 git。
  它们走 `pack_knowledge.py` 打包 + 网盘单独带走。
- `GITHUB_TOKEN` 不随仓库走，换机要重配（不配也能跑，只是限流 60 次/小时）。
- WorkBuddy 的 Automation 定时任务也不随仓库走，换机要在 UI 重建。
