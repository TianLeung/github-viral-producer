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
import time
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


def _curl(method, url, token, payload):
    """用系统 curl 发请求（能正确吃 http_proxy，比 urllib 稳）。返回 (status, text)。"""
    cmd = ["curl", "-s", "--max-time", "30", "-X", method, url,
           "-H", "Accept: application/vnd.github+json",
           "-H", "User-Agent: workbuddy-setup",
           "-w", "\n%{http_code}"]
    if token:
        cmd += ["-H", "Authorization: Bearer %s" % token]
    if payload is not None:
        cmd += ["-H", "Content-Type: application/json",
                "-d", json.dumps(payload, ensure_ascii=False)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=45).stdout
    except Exception:
        return 0, ""
    if not out:
        return 0, ""
    body, _, code = out.rpartition("\n")
    try:
        return int(code.strip()), body
    except ValueError:
        return 0, body


def _urllib(method, url, token, payload):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in UA.items():
        req.add_header(k, v)
    if token:
        req.add_header("Authorization", "Bearer %s" % token)
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8")


def api(method, path, token, payload=None, retries=6):
    """调 GitHub API，返回 (status, data)。

    有代理时 urllib 常报 SSL_ERROR_SYSCALL / UNEXPECTED_EOF（本机实测），
    所以优先走 curl；curl 也没有或返回 000（连接失败）就退到 urllib，
    两者都带重试 —— 网络抖动时代理时通时断，重试比报错有用。
    """
    url = API + path
    last = (0, {"message": "unknown"})
    for attempt in range(retries):
        for sender in (_curl, _urllib):
            try:
                st, body = sender(method, url, token, payload)
            except urllib.error.HTTPError as e:
                st, body = e.code, e.read().decode("utf-8", "ignore")
            except Exception as e:
                st, body = 0, str(e)

            if st == 0 and sender is _curl:
                continue          # curl 没装上或连不上，换 urllib 试试
            if st == 0:
                last = (0, {"message": body if isinstance(body, str) else ""})
                break             # urllib 也连不上 → 判定为网络抖动，等下一轮重试

            try:
                return st, json.loads(body or "{}")
            except Exception:
                return st, {"message": str(body)[:300]}

        if attempt < retries - 1:
            time.sleep(3)
    return last


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

    # 自动打开 Token 生成页，省得自己找路
    page = "https://github.com/settings/tokens/new?description=workbuddy&scopes=repo"
    print("\n  正在打开 Token 生成页…")
    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", page], check=False)
        elif platform.system() == "Windows":
            subprocess.run(["start", "", page], shell=True, check=False)
        else:
            subprocess.run(["xdg-open", page], check=False)
        ok("浏览器已打开（若没反应，手动访问 github.com/settings/tokens）")
    except Exception:
        warn("打不开浏览器，请手动访问 github.com/settings/tokens")

    print("\n" + "=" * 62)
    print("  请粘贴你的 GitHub Personal Access Token")
    print("  （输入时屏幕不显示，粘贴后直接回车）")
    print("")
    print("  生成步骤（页面已打开，照着点即可）：")
    print("    1. Note 随便填，比如 workbuddy")
    print("    2. 勾选 repo（建仓库和推送需要；只要不限流抓取的话可以不勾）")
    print("    3. 拉到最底点 Generate token")
    print("    4. 复制那串 ghp_ 开头的字符 —— 只显示这一次")
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

    # 凭据走 URL 内嵌，不走 http.extraheader ——
    # 实测在有 http_proxy 的机器上 extraheader 会被吞掉，git 转而去问「Username for ...」
    # 然后卡在交互输入上。推完立刻把 remote 改回无凭据地址，Token 不会留在 .git/config。
    clean_url = url
    auth_url = "https://%s:%s@github.com/%s/%s.git" % (owner, token, owner, name)
    env = dict(os.environ)
    env["GIT_ASKPASS"] = "true"
    env["GIT_TERMINAL_PROMPT"] = "0"   # 绝不交互等待，否则进程会挂死

    for attempt in range(1, 7):
        git("remote", "set-url", "origin", auth_url)
        r = subprocess.run(["git", "push", "-u", "origin", branch],
                           capture_output=True, text=True, env=env)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0 or "Everything up-to-date" in out:
            ok("推送成功")
            git("remote", "set-url", "origin", clean_url)
            return True
        # 代理时通时断：SSL_ERROR_SYSCALL / Connection reset 都是可重试的
        if attempt < 6:
            warn("第 %d 次推送失败（网络抖动），3 秒后重试…" % attempt)
            print("    %s" % out.strip().splitlines()[-1][:160])
            time.sleep(3)

    err = (r.stderr or r.stdout or "").strip()
    fail("推送失败（已重试 6 次）")
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
