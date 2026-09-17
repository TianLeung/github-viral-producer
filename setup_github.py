#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_github.py —— 把本地仓库一键推上 GitHub，并配好 GITHUB_TOKEN。

它会依次做完这 5 件事，全程只需你填一次 Token：
  1. 验证 Token 是否有效、属于哪个账号
  2. 在 GitHub 上创建仓库（不存在才建，已存在则直接复用）
  3. git remote add origin + 推送（推送用临时凭据，不把 Token 写进 .git/config）
  4. 把 Token 写进 shell 配置（macOS 写 ~/.zshrc，Windows 写用户环境变量）
  5. 验证搜索配额是否从 60 次/小时 提升到 5000 次/小时

用法：
  python3 setup_github.py                       # 交互式，会请你粘贴 Token（不回显）
  python3 setup_github.py --private             # 建私有仓库（默认公开）
  python3 setup_github.py --repo 别的仓库名
  GITHUB_TOKEN=ghp_xxx python3 setup_github.py  # 已配好环境变量时非交互

跨平台：macOS / Linux / Windows 通用。
"""

import argparse
import base64
import getpass
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
UA = {"User-Agent": "WorkBuddy-Bot", "Accept": "application/vnd.github+json"}
PLACEHOLDER = "{{WORKSPACE}}"


# ---------------------------------------------------------------- 基础工具

def info(msg=""):
    print(msg)


def ok(msg):
    print("  \033[32m✅\033[0m %s" % msg)


def warn(msg):
    print("  \033[33m⚠️ \033[0m %s" % msg)


def fail(msg):
    print("  \033[31m❌\033[0m %s" % msg)


def die(msg, hint=None):
    fail(msg)
    if hint:
        print("\n  %s\n" % hint)
    sys.exit(1)


def api(method, path, token, payload=None):
    """调 GitHub API，返回 (status, data)。"""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    for k, v in UA.items():
        req.add_header(k, v)
    if token:
        req.add_header("Authorization", "Bearer %s" % token)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"message": body[:300]}
    except Exception as e:
        return 0, {"message": str(e)}


def git(*args, **kw):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True, **kw)


# ---------------------------------------------------------------- Token

def get_token(cli_token):
    """优先级：命令行 > 环境变量 > 交互式输入（不回显）。"""
    if cli_token:
        return cli_token.strip()
    env = os.environ.get("GITHUB_TOKEN", "").strip()
    if env:
        ok("使用环境变量里已配置的 GITHUB_TOKEN")
        return env

    print("\n" + "=" * 62)
    print("  请粘贴你的 GitHub Personal Access Token")
    print("  （输入时屏幕不显示，粘贴后直接回车）")
    print("")
    print("  还没有？按这个路径生成：")
    print("    github.com → 右上角头像 ▾ → Settings")
    print("    → 左侧最底部 Developer settings")
    print("    → Personal access tokens → Tokens (classic)")
    print("    → Generate new token (classic)")
    print("    → 勾选 repo（本脚本建仓库/推送需要）→ Generate")
    print("=" * 62)
    t = getpass.getpass("\n  Token: ").strip()
    if not t:
        die("Token 为空，已取消。")
    return t


def verify_token(token):
    st, d = api("GET", "/user", token)
    if st != 200:
        msg = d.get("message", "未知错误")
        if st == 401:
            die("Token 无效或已过期（401）。",
                "请重新生成一个：github.com/settings/tokens")
        die("验证 Token 失败（HTTP %s）：%s" % (st, msg))
    ok("Token 有效，账号：%s" % d.get("login"))
    return d.get("login")


# ---------------------------------------------------------------- 建仓库

def ensure_repo(token, owner, name, private, desc):
    st, d = api("GET", "/repos/%s/%s" % (owner, name), token)
    if st == 200:
        ok("仓库已存在，直接复用：%s" % d["html_url"])
        return d
    if st != 404:
        die("查询仓库失败（HTTP %s）：%s" % (st, d.get("message")))

    st, d = api("POST", "/user/repos", token, {
        "name": name,
        "description": desc,
        "private": private,
        "auto_init": False,
    })
    if st not in (200, 201):
        msg = d.get("message", "")
        if st == 403 and "scope" in json.dumps(d, ensure_ascii=False).lower():
            die("Token 权限不足（403）：%s" % msg,
                "重新生成 Token 时请勾选 repo 这一项。")
        if "already exists" in msg.lower():
            die("同名仓库已存在，可能属于别的账号。换个名字重试：--repo 新名字")
        die("创建仓库失败（HTTP %s）：%s" % (st, msg))
    ok("仓库已创建：%s（%s）" % (d["html_url"], "私有" if private else "公开"))
    return d


# ---------------------------------------------------------------- 推送

def push(owner, name, token, branch):
    url = "https://github.com/%s/%s.git" % (owner, name)

    # 先清掉可能存在的旧 remote
    git("remote", "remove", "origin")
    r = git("remote", "add", "origin", url)
    if r.returncode != 0:
        die("配置 remote 失败：%s" % r.stderr.strip())
    ok("remote origin → %s" % url)

    # 当前分支统一为 main
    cur = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if cur != branch:
        git("branch", "-M", branch)
    ok("分支：%s" % branch)

    # 用临时 header 推送，避免 Token 落进 .git/config
    auth = base64.b64encode(("%s:%s" % (owner, token)).encode()).decode()
    env = dict(os.environ)
    env["GIT_ASKPASS"] = "true"
    env["GIT_TERMINAL_PROMPT"] = "0"
    r = subprocess.run(
        ["git", "-c", "http.extraheader=AUTHORIZATION: basic %s" % auth,
         "push", "-u", "origin", branch],
        capture_output=True, text=True, env=env)

    if r.returncode == 0:
        ok("推送成功")
        return True
    err = (r.stderr or r.stdout or "").strip()
    fail("推送失败")
    print("\n  %s\n" % err[:500])
    if "403" in err or "401" in err:
        warn("多半是 Token 没勾 repo 权限，重新生成时勾上它。")
    return False


# ---------------------------------------------------------------- 写环境

def persist_token(token):
    """把 Token 写进 shell 配置，让抓取脚本以后能自动读到。"""
    sysname = platform.system()
    line = 'export GITHUB_TOKEN=%s' % token

    if sysname == "Windows":
        r = subprocess.run(["setx", "GITHUB_TOKEN", token],
                           capture_output=True, text=True)
        if r.returncode == 0:
            ok("已写入 Windows 用户环境变量（重启 WorkBuddy 后生效）")
        else:
            warn("写入环境变量失败，请手动配置")
        return

    shell_cfg = pathlib.Path.home() / ".zshrc"
    if sysname == "Linux":
        shell_cfg = pathlib.Path.home() / ".bashrc"
        if not shell_cfg.exists():
            shell_cfg = pathlib.Path.home() / ".profile"

    try:
        txt = shell_cfg.read_text(encoding="utf-8") if shell_cfg.exists() else ""
    except Exception:
        txt = ""

    if "GITHUB_TOKEN=" in txt:
        # 已配过就替换旧值，避免重复追加
        lines = txt.splitlines()
        out, hit = [], False
        for l in lines:
            if "GITHUB_TOKEN=" in l and not l.strip().startswith("#"):
                out.append(line); hit = True
            else:
                out.append(l)
        if not hit:
            out.append(line)
        new = "\n".join(out) + "\n"
        act = "更新"
    else:
        new = txt.rstrip("\n") + "\n\n# GitHub 搜索配额：60 → 5000 次/小时\n%s\n" % line
        act = "写入"

    shell_cfg.write_text(new, encoding="utf-8")
    ok("已%s %s（新开终端或 source 后生效）" % (act, shell_cfg))


def check_rate(token):
    st, d = api("GET", "/rate_limit", token)
    if st == 200:
        core = d.get("resources", {}).get("core", {})
        search = d.get("resources", {}).get("search", {})
        ok("搜索配额：%s 次/小时" % search.get("limit"))
        ok("通用配额：%s 次/小时" % core.get("limit"))
    else:
        warn("配额查询失败（不影响使用）")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="一键推送到 GitHub 并配置 Token")
    ap.add_argument("--repo", default="github-viral-producer", help="仓库名")
    ap.add_argument("--private", action="store_true", help="建私有仓库")
    ap.add_argument("--token", help="直接给 Token（不推荐，会留在命令历史里）")
    ap.add_argument("--skip-token-save", action="store_true", help="不写入 shell 配置")
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent
    os.chdir(root)

    if not (root / ".git").is_dir():
        die("当前目录不是 git 仓库：%s" % root)

    # 推送前最后一次安全检查
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout
    bad = [l for l in tracked.splitlines()
           if re.search(r"\.(pdf|pages|mp4|mov)$", l)]
    if bad:
        die("发现私有资产将被上传，已中止：\n    " + "\n    ".join(bad[:5]),
            "把它们加进 .gitignore 后重新提交。")

    print("\n\033[1m▶ 开源爆款生产线 · GitHub 一键同步\033[0m")
    print("  工作区：%s" % root)

    token = get_token(args.token)
    owner = verify_token(token)

    print("\n[2/5] 创建仓库")
    desc = ("GitHub 开源爆款短视频生产线 v2：抓项目 → 共鸣洗稿 → 三要素分镜 → "
            "去 AI 味 → 语速校验 → 落盘。含跨平台专家包。")
    repo = ensure_repo(token, owner, args.repo, args.private, desc)

    print("\n[3/5] 推送代码")
    if not push(owner, args.repo, token, "main"):
        sys.exit(1)

    print("\n[4/5] 配置 GITHUB_TOKEN")
    if args.skip_token_save:
        warn("已跳过写入 shell 配置")
    else:
        persist_token(token)

    print("\n[5/5] 验证配额")
    check_rate(token)

    print("\n" + "=" * 62)
    print("  \033[1m全部完成\033[0m")
    print("=" * 62)
    print("  仓库地址：%s" % repo["html_url"])
    print("  克隆命令：git clone %s" % repo["clone_url"])
    print("")
    print("  换电脑时：")
    print("    git clone %s <目录>" % repo["clone_url"])
    if platform.system() == "Windows":
        print("    python install.py")
    else:
        print("    python3 install.py")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
