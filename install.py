#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 开源爆款短视频生产线 v2 —— 跨平台一键安装 / 换机恢复

用法（两个系统都行）：
    python install.py          # Windows 一般用 python
    python3 install.py         # macOS / Linux

作用：
    1. 自动识别 Windows / macOS / Linux，找到 WorkBuddy 的技能目录
    2. 把 skills/ 下的 5 个技能装进去
    3. 把 {{WORKSPACE}} {{SKILLS_DIR}} {{PYTHON}} 三个占位符替换成当前机器的真实值
    4. 检查 Python、GITHUB_TOKEN、数据流文件夹是否齐备

幂等：可重复执行。
"""

import os
import sys
import shutil
import pathlib
import platform

# ---------------------------------------------------------------- 基础路径

REPO_DIR = pathlib.Path(__file__).resolve().parent
SKILLS_SRC = REPO_DIR / "skills"
SYSTEM = platform.system()          # Windows / Darwin / Linux

# WorkBuddy 配置目录：优先读环境变量（WorkBuddy 官方约定），否则 ~/.workbuddy
_config = os.environ.get("WORKBUDDY_CONFIG_DIR", "").strip()
if _config:
    CONFIG_DIR = pathlib.Path(_config).expanduser()
else:
    CONFIG_DIR = pathlib.Path.home() / ".workbuddy"

SKILLS_DST = CONFIG_DIR / "skills"


def info(msg=""):
    print(msg)


# ---------------------------------------------------------------- 平台适配

def pick_python_command():
    """返回当前系统上用来跑脚本的命令名。"""
    if SYSTEM == "Windows":
        for cand in ("python", "py", "python3"):
            if shutil.which(cand):
                return cand
        return "python"
    for cand in ("python3", "python"):
        if shutil.which(cand):
            return cand
    return "python3"


def token_hint():
    if SYSTEM == "Windows":
        return (
            "PowerShell 里执行（永久生效）：\n"
            "      [Environment]::SetEnvironmentVariable('GITHUB_TOKEN','ghp_你的Token','User')\n"
            "    配置后需重启 WorkBuddy 才会读到。"
        )
    return (
        "终端执行（永久生效）：\n"
        "      echo 'export GITHUB_TOKEN=ghp_你的Token' >> ~/.zshrc && source ~/.zshrc"
    )


# ---------------------------------------------------------------- 主流程

def main():
    info("=" * 58)
    info("GitHub 开源爆款短视频生产线 v2 · 安装器")
    info("=" * 58)
    info("  当前系统   : %s" % SYSTEM)
    info("  仓库目录   : %s" % REPO_DIR)
    info("  技能安装到 : %s" % SKILLS_DST)
    info()

    # 1. 前置检查
    if not SKILLS_SRC.is_dir():
        info("[ERROR] 找不到 %s，请在仓库根目录执行本脚本。" % SKILLS_SRC)
        return 1

    py_cmd = pick_python_command()
    if not shutil.which(py_cmd):
        info("[ERROR] 未检测到 Python，请先安装 Python 3.8+ 并勾选 Add to PATH。")
        return 1
    info("  Python 命令 : %s" % py_cmd)

    # 2. 安装技能
    SKILLS_DST.mkdir(parents=True, exist_ok=True)
    installed = []
    for src in sorted(p for p in SKILLS_SRC.iterdir() if p.is_dir()):
        dst = SKILLS_DST / src.name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        installed.append(src.name)
    info()
    info("  已安装 %d 个技能：%s" % (len(installed), "、".join(installed)))

    # 3. 替换占位符
    mapping = {
        "{{WORKSPACE}}": str(REPO_DIR),
        "{{SKILLS_DIR}}": str(SKILLS_DST),
        "{{PYTHON}}": py_cmd,
    }
    changed = 0
    for p in SKILLS_DST.rglob("*"):
        if p.is_file() and p.suffix in {".md", ".py", ".sh", ".json", ".yaml", ".yml"}:
            try:
                s = p.read_text(encoding="utf-8")
            except Exception:
                continue
            orig = s
            for k, v in mapping.items():
                s = s.replace(k, v)
            if s != orig:
                p.write_text(s, encoding="utf-8")
                changed += 1
    info("  已写回本机真实路径（%d 个文件）" % changed)

    # 4. 脚本执行权限（Windows 不需要）
    if SYSTEM != "Windows":
        fetch = SKILLS_DST / "github-trend-radar" / "scripts" / "fetch_trending.py"
        if fetch.exists():
            os.chmod(fetch, 0o755)
            info("  已赋予执行权限：fetch_trending.py")

    for name in (".workbuddy/cache", "output"):
        (REPO_DIR / name).mkdir(parents=True, exist_ok=True)

    # 5. 环境检查
    info()
    info("-" * 58)
    info("  安装完成。")

    warn = False

    if not os.environ.get("GITHUB_TOKEN"):
        warn = True
        info()
        info("  [!] 未检测到 GITHUB_TOKEN：抓取限流 60 次/小时（按出口 IP 共享，容易打满）。")
        info("      免费申请（无需勾选任何 scope）：https://github.com/settings/tokens")
        info("      " + token_hint().replace("\n", "\n      "))

    missing = [d for d in ("相关参考提示词", "参考视频") if not (REPO_DIR / d).is_dir()]
    if missing:
        warn = True
        info()
        info("  [!] 缺少数据流文件夹：%s" % "、".join(missing))
        info("      把它们放回仓库根目录，产线才能加载本地知识库。")

    if not warn:
        info("  环境检查全部通过。")

    info()
    info("  下一步：在 WorkBuddy 里说「跑一遍爆款生产线」。")
    info("  提醒：Automation 定时任务不会随本仓库迁移，需按《自动化配置清单.md》在 UI 重建。")
    info("-" * 58)
    return 0


if __name__ == "__main__":
    sys.exit(main())
