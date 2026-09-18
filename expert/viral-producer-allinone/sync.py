#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专家包自愈脚本 —— 把专家包内 skills 的路径占位符替换为本机真实值。

为什么需要它：
  专家包里的 skill 文档不能写死路径（Mac 和 Windows 完全不同，换电脑也一定变），
  所以用 {{WORKSPACE}} / {{SKILLS_DIR}} / {{PYTHON}} 三个占位符代替。
  导入专家包后跑一次本脚本，占位符就会被换成这台机器的真实值。

何时需要跑：
  1. 换电脑导入专家包后（必跑一次）
  2. 把专家包挪到别的目录后
  3. 不跑也能用，但 AI 需要每次自己找脚本路径，会慢一点

用法：
  python3 sync.py                              # 用专家包内置的 workspace/
  python3 sync.py --workspace /path/to/dir     # 指定已有工作区（推荐：复用你的知识库）
"""

import argparse
import os
import re
import shutil
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_WORKSPACE = HERE / "workspace"

PLACEHOLDERS = ("{{WORKSPACE}}", "{{SKILLS_DIR}}", "{{PYTHON}}")


def detect_python():
    """按平台挑一个能用的 python 命令名。"""
    for cmd in ("python3", "python", "py"):
        if shutil.which(cmd):
            return cmd
    return "python3"


def ensure_workspace(workspace):
    """确保工作区目录齐全（output 必须有，否则落盘会失败）。"""
    (workspace / "output").mkdir(parents=True, exist_ok=True)
    made = []
    for name, note in (("相关参考提示词", "放你的提示词 PDF / Pages 原文"),
                       ("参考视频", "放你的对标爆款视频")):
        d = workspace / name
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            made.append(name)
            readme = d / "把文件放这里.txt"
            readme.write_text("%s：%s。\n放进来后，产线会自动读取它们作为洗稿规范和分镜骨架。\n"
                              % (name, note), encoding="utf-8")
    return made


def main():
    ap = argparse.ArgumentParser(description="专家包路径自愈")
    ap.add_argument("--workspace", default=str(DEFAULT_WORKSPACE),
                    help="工作区路径（放提示词、参考视频、output 的目录）")
    args = ap.parse_args()

    SKILLS = HERE / "skills"
    WORKSPACE = pathlib.Path(args.workspace).expanduser().resolve()
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    if not SKILLS.is_dir():
        sys.stderr.write("[ERROR] 找不到 skills/ 目录：%s\n" % SKILLS)
        return 1

    py = detect_python()
    mapping = {
        "{{WORKSPACE}}": str(WORKSPACE),
        "{{SKILLS_DIR}}": str(SKILLS),
        "{{PYTHON}}": py,
    }

    changed_files, total = [], 0
    for p in sorted(SKILLS.rglob("*")):
        if not p.is_file() or p.suffix not in (".md", ".py"):
            continue
        try:
            s = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if not any(ph in s for ph in PLACEHOLDERS):
            continue
        n = sum(s.count(ph) for ph in PLACEHOLDERS)
        for ph, val in mapping.items():
            s = s.replace(ph, val)
        p.write_text(s, encoding="utf-8")
        changed_files.append((p.relative_to(HERE).as_posix(), n))
        total += n

    made = ensure_workspace(WORKSPACE)

    # ---- 报告 ----
    print("专家包：%s" % HERE)
    print("")
    if changed_files:
        for rel, n in changed_files:
            print("  已写回 %-52s %d 处" % (rel[:52], n))
    else:
        print("  占位符已是本机值，无需改动")
    print("")
    print("  Python 命令    : %s" % py)
    print("  Skills 目录    : %s" % SKILLS)
    print("  工作区          : %s" % WORKSPACE)
    have_kb = (WORKSPACE / "相关参考提示词").is_dir() and any(
        (WORKSPACE / "相关参考提示词").iterdir())
    have_vid = (WORKSPACE / "参考视频").is_dir() and any(
        (WORKSPACE / "参考视频").iterdir())
    print("  知识库          : %s" % ("已就位 ✅" if have_kb else "⚠️ 空的，产出会退化成通用分镜"))
    print("  参考视频        : %s" % ("已就位 ✅" if have_vid else "⚠️ 空的，骨架会用默认版"))
    if made:
        print("  新建目录        : %s" % "、".join(made))
    print("")

    left = 0
    for p in SKILLS.rglob("*"):
        if p.is_file() and p.suffix in (".md", ".py"):
            try:
                s = p.read_text(encoding="utf-8")
            except Exception:
                continue
            left += len(re.findall(r"\{\{[A-Z_]+\}\}", s))
    print("  残留占位符      : %d %s" % (left, "✅" if left == 0 else "⚠️"))

    if not os.environ.get("GITHUB_TOKEN"):
        print("")
        print("  ⚠️ GITHUB_TOKEN 未配置 —— 抓取限流 60 次/小时（按出口 IP 共享）。")
        print("     配置后 5000 次/小时，且能开启 --deep 深度模式。")
        print("     生成地址：https://github.com/settings/tokens （无需勾选任何 scope）")
    else:
        print("  GITHUB_TOKEN    : 已配置 ✅")

    print("")
    print("完成 ✅  共替换 %d 处路径占位符。" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
