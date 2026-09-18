#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bootstrap.py —— 远程安装器：从 GitHub 仓库下载整套产线 → 解压 → 安装 → 验收。

设计目标：**零依赖、零认证、零提问**。
  - 不用装 git（直接走 HTTP 下载 zip）
  - 公开仓库不需要任何 Token
  - 仓库地址已预置在 config.json，不问用户

用法：
  python3 bootstrap.py                 下载 + 安装 + 验收
  python  bootstrap.py                 Windows 写法
  python3 bootstrap.py --dir <路径>     指定装到哪
  python3 bootstrap.py --token ghp_xxx  私有仓库才需要
  python3 bootstrap.py --check          只检查本机现状，不下载
  python3 bootstrap.py --force          已有目录也强制重装

跨平台：macOS / Linux / Windows，只用 Python 标准库。
"""

import argparse
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
CONFIG = HERE / "config.json"

DEFAULT_OWNER = "TianLeung"
DEFAULT_REPO = "github-viral-producer"
DEFAULT_BRANCH = "main"


# ---------------------------------------------------------------- 输出

def head(t):
    print("\n\033[1m%s\033[0m" % t)


def ok(t):
    print("  \033[32m✅\033[0m %s" % t)


def warn(t):
    print("  \033[33m⚠️ \033[0m %s" % t)


def fail(t):
    print("  \033[31m❌\033[0m %s" % t)


def die(t, hint=None):
    fail(t)
    if hint:
        print("\n  %s\n" % hint)
    sys.exit(1)


# ---------------------------------------------------------------- 配置

def load_config():
    cfg = {"owner": DEFAULT_OWNER, "repo": DEFAULT_REPO, "branch": DEFAULT_BRANCH}
    if CONFIG.exists():
        try:
            d = json.loads(CONFIG.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                cfg.update({k: v for k, v in d.items() if v})
        except Exception as e:
            warn("config.json 读取失败（用默认值）：%s" % e)
    # 兼容旧字段 repoUrl
    url = cfg.get("repoUrl", "")
    if url and "github.com" in url and "<" not in url:
        parts = url.rstrip("/").replace(".git", "").split("github.com")[-1].strip(":/").split("/")
        if len(parts) >= 2:
            cfg["owner"], cfg["repo"] = parts[-2], parts[-1]
    return cfg


def default_dir(cfg):
    """跨平台默认安装位置。用户可在 config.json 里用 localDir 覆盖。"""
    home = pathlib.Path.home()
    name = cfg["repo"]
    return home / name


# ---------------------------------------------------------------- 下载

def archive_url(cfg):
    # codeload 直连，比 github.com/archive 少一次跳转
    return "https://codeload.github.com/%s/%s/zip/refs/heads/%s" % (
        cfg["owner"], cfg["repo"], cfg["branch"])


def download(url, token, dest):
    """下载 zip，带进度。返回字节数。"""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "WorkBuddy-Bootstrap")
    req.add_header("Accept", "application/zip")
    if token:
        req.add_header("Authorization", "token %s" % token)

    head("第 1 步  下载")
    print("  %s" % url)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            total = int(r.headers.get("Content-Length") or 0)
            got = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = r.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    if total:
                        pct = got * 100 // total
                        bar = "█" * (pct // 4) + "░" * (25 - pct // 4)
                        sys.stdout.write("\r  %s %3d%%  %.1f MB" % (bar, pct, got / 1048576))
                        sys.stdout.flush()
            sys.stdout.write("\n")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            die("下载失败 404：仓库或分支不存在。",
                "确认 https://github.com/%s/%s 存在，且默认分支是 %s。"
                "分支不同就在 config.json 里改 branch。"
                % (cfg_owner, cfg_repo, cfg_branch))
        if e.code in (401, 403):
            die("下载失败 %d：没有权限。" % e.code,
                "私有仓库需要提供 Token：python3 bootstrap.py --token ghp_xxx")
        die("下载失败 HTTP %d" % e.code)
    except Exception as e:
        die("下载失败：%s" % e,
            "检查网络；国内若访问不了，可挂代理后重试。")

    size = os.path.getsize(dest)
    # 判断是不是真 zip：看文件头 PK\x03\x04，不能用大小判断（小仓库的 zip 可能只有几百字节）
    with open(dest, "rb") as f:
        magic = f.read(4)
    if magic != b"PK\x03\x04":
        with open(dest, "rb") as f:
            preview = f.read(200).decode("utf-8", "ignore")
        die("下载内容不是 zip（%d 字节），前 200 字节：%s" % (size, preview[:200]),
            "若提示 404，确认仓库和分支名；若提示权限，私有仓库要加 --token。")
    ok("已下载 %.2f MB" % (size / 1048576))
    return size


# ---------------------------------------------------------------- 解压

def unzip(zpath, target):
    """解压并把 GitHub 自动加的顶层目录摊平到 target。"""
    head("第 2 步  解压")
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        if not names:
            die("zip 是空的")
        top = names[0].split("/")[0]
        z.extractall(target)

    extracted = target / top
    if not extracted.is_dir():
        die("解压后找不到预期目录：%s" % extracted)

    # 把内容移动到 target 根，保持目录干净
    for item in list(extracted.iterdir()):
        dst = target / item.name
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        shutil.move(str(item), str(dst))
    extracted.rmdir()
    ok("解压到 %s" % target)


# ---------------------------------------------------------------- 安装

def run_install(target):
    head("第 3 步  安装")
    installer = target / "install.py"
    if not installer.exists():
        die("包里没有 install.py，可能下载到了错误的仓库。")

    r = subprocess.run([sys.executable, str(installer)],
                       capture_output=True, text=True, cwd=str(target))
    out = (r.stdout or "") + (r.stderr or "")
    print("\n".join("  " + l for l in out.rstrip().splitlines()))
    if r.returncode != 0:
        die("安装脚本返回非零状态（%d）。" % r.returncode)
    ok("安装完成")


def fetch_test(target, cfg):
    """实跑一次抓取，确认链路活着。"""
    head("第 4 步  验收")
    cfg_dir = os.environ.get("WORKBUDDY_CONFIG_DIR", "").strip()
    base = pathlib.Path(cfg_dir) if cfg_dir else pathlib.Path.home() / ".workbuddy"
    script = base / "skills" / "github-trend-radar" / "scripts" / "fetch_trending.py"

    if not script.exists():
        warn("没找到抓取脚本（%s），跳过实测" % script)
        return False

    try:
        r = subprocess.run(
            [sys.executable, str(script), "--days", "7", "--min-stars", "200",
             "--limit", "3", "--mode", "hybrid"],
            capture_output=True, text=True, timeout=120)
        out = r.stdout or ""
        if "命中数量" in out:
            line = [l for l in out.splitlines() if "命中数量" in l]
            ok("抓取实测通过：%s" % line[0].strip())
            for l in out.splitlines():
                if "项目名称" in l:
                    print("      " + l.strip())
            return True
        warn("抓取没返回项目（可能限流或未命中），但不影响安装")
        return False
    except subprocess.TimeoutExpired:
        warn("抓取超时（网络慢），不影响安装")
        return False
    except Exception as e:
        warn("抓取实测异常：%s" % e)
        return False


# ---------------------------------------------------------------- 报告

def report(cfg, target):
    cfg_dir = os.environ.get("WORKBUDDY_CONFIG_DIR", "").strip()
    base = pathlib.Path(cfg_dir) if cfg_dir else pathlib.Path.home() / ".workbuddy"
    skills = base / "skills"

    head("安装结果")
    print("  仓库    : https://github.com/%s/%s" % (cfg["owner"], cfg["repo"]))
    print("  工作区  : %s" % target)
    print("  技能目录: %s" % skills)

    need = ["github-trend-radar", "resonance-engine", "opensource-video-director",
            "colloquial-polisher", "github-viral-pipeline"]
    have = [n for n in need if (skills / n).is_dir()]
    print("  技能    : %d / %d 个就位" % (len(have), len(need)))
    if len(have) < len(need):
        warn("缺：%s" % "、".join(set(need) - set(have)))

    for name in ("相关参考提示词", "参考视频"):
        d = target / name
        n = len([p for p in d.iterdir() if not p.name.startswith(".")]) if d.is_dir() else 0
        if n:
            ok("%s：%d 个文件" % (name, n))
        else:
            warn("%s：空 —— 洗稿质量会退化成通用分镜，请把文件放进 %s" % (name, d))

    if os.environ.get("GITHUB_TOKEN"):
        ok("GITHUB_TOKEN：已配置")
    else:
        warn("GITHUB_TOKEN：未配置（不配也能跑，但限流 60 次/小时）")

    print("\n  \033[1m下一步\033[0m：在 WorkBuddy 里说「跑一遍爆款生产线」。\n")


# ---------------------------------------------------------------- main

cfg_owner = cfg_repo = cfg_branch = ""


def main():
    global cfg_owner, cfg_repo, cfg_branch
    ap = argparse.ArgumentParser(description="从 GitHub 下载安装爆款生产线")
    ap.add_argument("--dir", help="安装到哪个目录")
    ap.add_argument("--token", help="私有仓库的 Personal Access Token")
    ap.add_argument("--branch", help="分支，默认 main")
    ap.add_argument("--force", action="store_true", help="已存在也重装")
    ap.add_argument("--check", action="store_true", help="只检查现状")
    args = ap.parse_args()

    cfg = load_config()
    if args.branch:
        cfg["branch"] = args.branch
    cfg_owner, cfg_repo, cfg_branch = cfg["owner"], cfg["repo"], cfg["branch"]

    target = pathlib.Path(args.dir) if args.dir else \
        pathlib.Path(cfg.get("localDir") or default_dir(cfg))
    target = target.expanduser()

    if args.check:
        report(cfg, target if target.is_dir() else default_dir(cfg))
        return

    if "<" in str(cfg.get("repoUrl", "")):
        cfg["repoUrl"] = ""

    print("\n\033[1m▶ 爆款生产线 · 远程安装\033[0m")
    print("  目标目录：%s" % target)

    if target.exists() and any(target.iterdir()):
        if not args.force:
            warn("目录已存在且有内容，跳过下载（要重装加 --force）")
            print("  直接走安装步骤…\n")
            run_install(target)
            fetch_test(target, cfg)
            report(cfg, target)
            return
        ok("强制重装：清空 %s" % target)
        shutil.rmtree(target)

    target.mkdir(parents=True, exist_ok=True)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="viral-bootstrap-"))
    zpath = tmp / "repo.zip"
    try:
        download(archive_url(cfg), args.token or os.environ.get("GITHUB_TOKEN", ""), zpath)
        unzip(zpath, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    run_install(target)
    fetch_test(target, cfg)
    report(cfg, target)


if __name__ == "__main__":
    main()
