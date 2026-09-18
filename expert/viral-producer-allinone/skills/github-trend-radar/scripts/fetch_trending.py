#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 爆款项目嗅探器 —— 只捞「有界面、能演示、适合短视频展示」的新项目。

设计要点：
  1. 用 topic 正向锁定带 UI 的项目（webui / gradio / streamlit / gui / desktop-app / app）
  2. 用 NOT / -topic 反向剔除 SDK、library、framework、benchmark、awesome-list
  3. 三级降级：严格查询无结果时，自动逐层放宽，保证永远有产出
  4. Token 可选：有 GITHUB_TOKEN 走 5000 次/小时，没有则 60 次/小时

用法：
  {{PYTHON}} fetch_trending.py                          # 默认：近 7 天、stars>200、取 5 个
  {{PYTHON}} fetch_trending.py --days 7 --min-stars 500 --limit 10
  {{PYTHON}} fetch_trending.py --json                  # 输出原始 JSON
  {{PYTHON}} fetch_trending.py --out output/radar.md   # 同时落盘
  GITHUB_TOKEN=ghp_xxx {{PYTHON}} fetch_trending.py

输出（Markdown 卡片）可直接作为「开源爆款编导」Skill 的输入。
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

API_URL = "https://api.github.com/search/repositories"

DEFAULT_TOPICS = ["webui", "gradio", "streamlit", "gui", "desktop-app", "app"]
DEFAULT_EXCLUDE_WORDS = ["sdk", "library", "framework", "benchmark"]
DEFAULT_EXCLUDE_TOPICS = ["awesome-list", "awesome", "books", "course", "tutorial", "interview"]
DEFAULT_LICENSE_HINT = None


# GitHub Search API 硬限制（踩过的坑，勿删）：
#   1. 单条 query 里 AND / OR / NOT 操作符总数不得超过 5 个，否则 422
#      "More than five AND / OR / NOT operators were used."
#      -> 6 个 topic(5 OR) + 4 个 NOT(4) = 9 个，必然报错
#      -> 解法：按 topic 分批请求，每批 topic 数 = MAX_OPERATORS - NOT 数 + 1，最后合并去重
#   2. q 参数总长度 <= 256 字符
#   3. "-topic:xxx" 这种否定限定符不占用操作符名额，可以放心多加
MAX_OPERATORS = 5
MAX_QUERY_LEN = 250

# ---- UI 启发式打分词典（hybrid 模式用）----
# 背景：新仓库普遍还没打 topic（实测近 7 天 600+ Star 的项目 topics 全是空数组），
# 纯 topic 锁定会把真正的爆款全漏掉。所以改用「热度通道先捞池子 + UI 启发式打分排序」。
UI_TOPIC_HINTS = {"webui", "gui", "desktop-app", "app", "gradio", "streamlit", "dashboard",
                  "electron", "tauri", "flutter", "qt", "chrome-extension",
                  "browser-extension", "vscode-extension", "studio", "editor",
                  "viewer", "player", "tool", "client", "no-code",
                  "menubar-app", "menubarapp", "macos-app", "statusbar", "tray",
                  "launcher", "wallpaper", "desktop-pet", "widget", "overlay",
                  "productivity", "self-hosted", "screenshot", "screen-recording"}
UI_NAME_HINTS = ["webui", "-ui", "gui", "desktop", "studio", "dashboard", "app", "client",
                 "viewer", "editor", "player", "panel", "console", "box", "desk"]
UI_DESC_HINTS = ["webui", "web ui", "gui", "dashboard", "desktop", "browser", "no-code",
                 "self-host", "selfhost", "可视化", "界面", "客户端", "桌面", "图形界面",
                 "拖拽", "控制面板", "一键部署", "本地部署", "开箱即用", "studio", "playground",
                 "menubar", "menu bar", "菜单栏", "托盘", "壁纸", "桌面宠物", "桌宠",
                 "录屏", "截图", "本地运行", "run locally", "no login", "无需登录",
                 "one click", "一键", "可视化界面", "操作界面", "控制台", "面板",
                 # 中文项目常见界面词（2026-09-14 补：PRINTFILM 类中文 Web 平台此前只得 1 分）
                 "工作台", "模板", "管理后台", "后台管理", "注册", "登录", "账号",
                 "仪表盘", "画布", "资产库", "创作平台", "创作工具", "网页版",
                 "中文界面", "中英", "操作手册", "用户端", "视觉风格", "前端界面",
                 "template", "admin", "login", "signup", "workspace", "canvas",
                 "web app", "webapp", "frontend", "no-code platform"]
ANTI_HINTS = ["sdk", "library", "framework", "benchmark", "awesome", "paper", "论文",
              "tutorial", "course", "interview", "dataset", "checkpoint", "算法",
              "面试题", "八股", "courseware"]
UI_LANG_HINTS = {"TypeScript", "JavaScript", "Vue", "C#", "Swift", "Kotlin", "Dart", "Svelte"}


def since_date(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def split_topics(topics, not_count):
    """按操作符名额把 topic 切成若干批，保证每批 (len-1) OR + not_count <= 5。"""
    size = MAX_OPERATORS - not_count + 1
    size = max(1, min(size, len(topics)))
    return [topics[i:i + size] for i in range(0, len(topics), size)]


def trim_query(q):
    """超长时从尾部裁掉 -topic 限定符，保证 <= 250 字符。"""
    while len(q) > MAX_QUERY_LEN and " -topic:" in q:
        q = q[:q.rindex(" -topic:")]
    return q


def build_query(topics, since, min_stars, exclude_words, exclude_topics,
                use_not_operator=True, extra=None):
    """组装 GitHub Search 查询语句。
    use_not_operator=True  -> 用 NOT xxx（更贴近官方文档表述）
    use_not_operator=False -> 用 -xxx（兼容性更强）
    """
    parts = []
    if topics:
        parts.append("(" + " OR ".join("topic:%s" % t for t in topics) + ")")
    parts.append("created:>%s" % since)
    parts.append("stars:>%d" % min_stars)
    for w in exclude_words:
        parts.append(("NOT %s" % w) if use_not_operator else ("-%s" % w))
    for t in exclude_topics:
        parts.append("-topic:%s" % t)
    if extra:
        parts.append(extra)
    return trim_query(" ".join(parts))


def request(query, sort, order, per_page, token):
    params = {"q": query, "sort": sort, "order": order, "per_page": str(per_page)}
    url = API_URL + "?" + urllib.parse.urlencode(params)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "WorkBuddy-Bot",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer %s" % token
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")), url, None
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "ignore")[:300]
        except Exception:
            pass
        return None, url, "HTTP %s %s | %s" % (e.code, e.reason, body)
    except Exception as e:
        return None, url, str(e)


def ui_score(repo, readme=""):
    """给一个仓库打「是否上镜」的分。返回 (分数, 命中理由列表)。"""
    score, reasons = 0, []
    topics = [t.lower() for t in (repo.get("topics") or [])]
    name = (repo.get("name") or "").lower()
    full = (repo.get("full_name") or "").lower()
    desc = (repo.get("description") or "").lower()

    hit_t = [t for t in topics if t in UI_TOPIC_HINTS]
    if hit_t:
        score += min(6, 3 * len(hit_t))
        reasons.append("topic 命中 %s" % "/".join(hit_t[:3]))

    hit_n = [h for h in UI_NAME_HINTS if h in name]
    if hit_n:
        score += 2
        reasons.append("项目名含 %s" % "/".join(hit_n[:2]))

    hit_d = [h for h in UI_DESC_HINTS if h in desc]
    if hit_d:
        score += min(4, 2 * len(hit_d))
        reasons.append("简介含 %s" % "/".join(hit_d[:2]))

    if repo.get("homepage"):
        score += 1
        reasons.append("有演示主页")

    if repo.get("language") in UI_LANG_HINTS:
        score += 1
        reasons.append("前端/桌面系语言 %s" % repo.get("language"))

    anti = [a for a in ANTI_HINTS if a in full or a in name or a in desc]
    if anti:
        score -= 5
        reasons.append("疑似底层/学习类（%s）" % "/".join(anti[:2]))

    if readme:
        if readme.count("![") >= 1 or "![" in readme:
            score += 2
            reasons.append("README 含截图/动图")
        if any(k in readme.lower() for k in ["screenshot", "demo", "演示", "截图", "preview"]):
            score += 1
            reasons.append("README 提到 Demo")

    return score, reasons


def fetch_readme(full_name, token):
    """可选增强：拉 README 判断有没有截图/Demo。失败静默返回空串。"""
    url = "https://api.github.com/repos/%s/readme" % full_name
    headers = {"Accept": "application/vnd.github.raw", "User-Agent": "WorkBuddy-Bot",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer %s" % token
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception:
        return ""


def to_cards(items, with_score=False):
    """把 API 结果压成下游 Skill 能直接吃的 Markdown 文本。"""
    lines = []
    for i, it in enumerate(items, 1):
        name = it.get("name") or ""
        full = it.get("full_name") or name
        url = it.get("html_url") or ""
        desc = (it.get("description") or "（无简介）").strip().replace("\n", " ")
        stars = it.get("stargazers_count", 0)
        topics = ", ".join(it.get("topics") or []) or "无"
        lang = it.get("language") or "未标注"
        created = (it.get("created_at") or "")[:10]
        homepage = it.get("homepage") or ""
        lines.append("### 项目 %d：%s\n" % (i, name))
        lines.append("- **项目名称**：%s" % name)
        lines.append("- **仓库全名**：%s" % full)
        lines.append("- **项目地址**：%s" % url)
        if homepage:
            lines.append("- **演示/主页**：%s" % homepage)
        lines.append("- **一句话介绍**：%s" % desc)
        lines.append("- **实时 Star**：%s" % stars)
        lines.append("- **主题标签**：%s" % topics)
        lines.append("- **主要语言**：%s" % lang)
        lines.append("- **创建时间**：%s" % created)
        if with_score:
            s, reasons = ui_score(it)
            lines.append("- **上镜评分**：%d 分（%s）" % (s, "；".join(reasons) or "无明显 UI 特征"))
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="GitHub 爆款项目嗅探器")
    ap.add_argument("--days", type=int, default=7, help="时间窗口（天），默认 7")
    ap.add_argument("--min-stars", type=int, default=200, help="Star 下限，默认 200")
    ap.add_argument("--limit", type=int, default=5, help="返回条数，默认 5")
    ap.add_argument("--topics", default=",".join(DEFAULT_TOPICS),
                    help="正向锁定的 topic，逗号分隔")
    ap.add_argument("--exclude-words", default=",".join(DEFAULT_EXCLUDE_WORDS),
                    help="排除的关键词，逗号分隔")
    ap.add_argument("--exclude-topics", default=",".join(DEFAULT_EXCLUDE_TOPICS),
                    help="排除的 topic，逗号分隔")
    ap.add_argument("--sort", default="stars", help="排序维度，默认 stars")
    ap.add_argument("--order", default="desc", help="升/降序，默认 desc")
    ap.add_argument("--json", action="store_true", help="输出原始 JSON")
    ap.add_argument("--out", default="", help="结果落盘路径（可选）")
    ap.add_argument("--query-only", action="store_true", help="只打印查询语句与 URL，不请求")
    ap.add_argument("--mode", default="hybrid", choices=["hybrid", "topic", "hot"],
                    help="hybrid=热度通道+UI打分（默认，推荐）；topic=纯 topic 锁定；hot=纯热度")
    ap.add_argument("--min-ui-score", type=int, default=2,
                    help="上镜评分门槛，默认 2（hybrid 模式生效）")
    ap.add_argument("--deep", action="store_true",
                    help="额外拉取 README 判断有无截图/Demo（更准，但每个项目多 1 次请求）")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    ex_words = [w.strip() for w in args.exclude_words.split(",") if w.strip()]
    ex_topics = [t.strip() for t in args.exclude_topics.split(",") if t.strip()]
    since = since_date(args.days)

    if args.query_only:
        for b in split_topics(topics, len(ex_words)):
            q = build_query(b, since, args.min_stars, ex_words, ex_topics)
            print("QUERY: " + q)
            print("URL:   " + API_URL + "?" + urllib.parse.urlencode(
                {"q": q, "sort": args.sort, "order": args.order, "per_page": args.limit}))
            print("")
        return 0

    def run_level(level_name, ex_words, min_stars, use_not):
        """跑一个降级层级：topic 分批请求 -> 合并去重 -> 按排序键取前 N。"""
        return run_batches(split_topics(topics, len(ex_words) if use_not else 0),
                           ex_words, min_stars, use_not)

    def run_batches(batches, ex_words, min_stars, use_not, per_page=None):
        pool, queries, fatal = {}, [], []
        for batch in batches:
            q = build_query(batch, since, min_stars, ex_words, ex_topics, use_not)
            data, url, err = request(q, args.sort, args.order,
                                     per_page or min(args.limit * 3, 100), token)
            if data is None:
                if err and ("403" in err or "429" in err or "401" in err):
                    fatal.append(err)
                    break
                continue
            queries.append(q)
            for it in data.get("items", []):
                pool[it.get("id") or it.get("html_url")] = it
        merged = sorted(pool.values(), key=lambda x: (x.get("stargazers_count") or 0),
                        reverse=(args.order == "desc"))
        return merged, queries, fatal

    def run_hot(min_stars, days, per_page=None):
        """热度通道：不限制 topic，只按 新建时间 + Star 捞池子。"""
        q = "created:>%s stars:>%d" % (since_date(days), min_stars)
        for t in ex_topics:
            q = trim_query(q + " -topic:%s" % t)
        data, url, err = request(q, "stars", "desc", per_page or min(args.limit * 4, 100), token)
        if data is None:
            return [], q, err or ""
        return data.get("items", []), q, ""

    score_cache = {}

    def score_of(it):
        key = it.get("id") or it.get("html_url")
        if key not in score_cache:
            rd = fetch_readme(it.get("full_name", ""), token) if args.deep else ""
            score_cache[key] = ui_score(it, rd)
        return score_cache[key]

    def rank(pool_list, min_score):
        scored = []
        for it in pool_list:
            s, _ = score_of(it)
            if s >= min_score:
                scored.append((s, it))
        scored.sort(key=lambda x: (-x[0], -(x[1].get("stargazers_count") or 0)))
        return [it for _, it in scored]

    items, used_query, last_err, level = [], "", "", ""

    if args.mode == "topic":
        # ---- 纯 topic 模式（原始方案，保留供对照）----
        attempts = [
            ("严格模式（topic 锁定 + NOT 排除）", dict(ex_words=ex_words, min_stars=args.min_stars, use_not=True)),
            ("放宽：去掉 NOT 关键词", dict(ex_words=[], min_stars=args.min_stars, use_not=True)),
            ("放宽：Star 门槛减半", dict(ex_words=[], min_stars=max(10, args.min_stars // 2), use_not=False)),
        ]
        for level, cfg in attempts:
            merged, queries, fatal = run_level(level, **cfg)
            if fatal:
                last_err = fatal[0]
                items = []
                break
            used_query = "  ||  ".join(queries) if queries else ""
            if merged:
                items = merged[:args.limit]
                break
            last_err = "0 条结果"

    else:
        # ---- hybrid / hot：热度通道捞池 + UI 启发式打分 ----
        pool, queries, errs = {}, [], []
        for lv_name, st, dy in [("热度通道", args.min_stars, args.days),
                                ("热度通道·Star 门槛减半", max(10, args.min_stars // 2), args.days),
                                ("热度通道·窗口放宽到 %d 天" % (args.days * 3), max(10, args.min_stars // 4), args.days * 3)]:
            got, q, err = run_hot(st, dy)
            if err and ("403" in err or "429" in err or "401" in err):
                errs.append(err)
                break
            if q:
                queries.append(q)
            for it in got:
                pool[it.get("id") or it.get("html_url")] = it
            if len(pool) >= args.limit * 4:
                break
        level = "hybrid（热度通道 + UI 打分）" if args.mode == "hybrid" else "hot（纯热度通道）"
        used_query = "  ||  ".join(queries)

        if errs:
            last_err = errs[0]
            items = []
        else:
            min_score = args.min_ui_score if args.mode == "hybrid" else 0
            items = rank(list(pool.values()), min_score)

            # hybrid：UI 分达标的不够，就用 topic 通道补齐（保证"一定有界面"的兜底）
            if args.mode == "hybrid" and len(items) < args.limit:
                tp, tq, tf = run_level("topic 兜底", ex_words, max(10, args.min_stars // 4), True)
                if tq:
                    used_query += "  ||  [topic 兜底] " + "  ||  ".join(tq)
                for it in tp:
                    key = it.get("id") or it.get("html_url")
                    if key not in pool:
                        pool[key] = it
                items = rank(list(pool.values()), max(0, min_score - 2))
            items = items[:args.limit]

    if not items:
        sys.stderr.write("[ERROR] GitHub 请求失败或未命中：%s\n" % (last_err or "0 条结果"))
        if "403" in last_err or "429" in last_err:
            sys.stderr.write("[提示] 大概率触发限流。请配置 GITHUB_TOKEN（免费）："
                             "https://github.com/settings/tokens （无需勾选任何 scope 即可搜索）\n")
        elif "422" in last_err:
            sys.stderr.write("[提示] 查询语法被拒：单条 query 的 AND/OR/NOT 超过 5 个，或超 256 字符。请减少 --topics / --exclude-words。\n")
        return 1

    header = ("# GitHub 爆款候选（%s ~ 今，近 %d 天）\n\n"
              "- 命中数量：%d\n- 检索模式：%s\n- 查询语句：`%s`\n\n"
              % (since, args.days, len(items), level, used_query))
    body = to_cards(items, with_score=(args.mode != "topic"))
    text = header + body

    if args.json:
        json.dump({"query": used_query, "level": level, "since": since, "items": items},
                  sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(text)

    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        sys.stderr.write("[OK] 已落盘：%s\n" % args.out)

    if not token:
        sys.stderr.write("[提示] 未检测到 GITHUB_TOKEN，当前限流 60 次/小时。"
                         "建议配置后提升至 5000 次/小时。\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
