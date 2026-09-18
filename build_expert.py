#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专家包构建器 —— 从本仓库重建「开源爆款短视频制片人」专家包的分发 zip。

什么时候跑：
  改了 skills/ 里任何内容之后，重新生成一次 zip，换新电脑时用的就是最新版。

用法：
  python3 build_expert.py                 # 只生成 dist/github-viral-producer.zip
  python3 build_expert.py --install       # 生成 zip，同时装进本机 WorkBuddy 并注册

为什么不能直接打包 ~/.workbuddy 里那份：
  那份已经被 sync.py 写成了这台机器的绝对路径。换台电脑（或换成 Windows）路径全错。
  所以必须先从本仓库的「占位符版」重建，导入新机器后再跑 sync.py 写回真实路径。
"""

import argparse
import os
import shutil
import sys
import zipfile
import pathlib

REPO = pathlib.Path(__file__).resolve().parent
DIST = REPO / "dist"

# 打 zip 时排除的东西
EXCLUDE_DIRS = {"__pycache__", ".git", ".DS_Store"}
EXCLUDE_FILES = {".DS_Store", ".gitkeep"}

# 三个专家包：技能来源目录不同（skills_src 可以是单个目录名，也可以是列表 = 多来源合并）
#   github-viral-producer     完整包，技能来自 skills/（含占位符，导入后要跑 sync.py）
#   viral-producer-bootstrap  引导包，技能来自 bootstrap/（只负责去 GitHub 拉全套）
#   viral-producer-allinone   全能包，skills/ + bootstrap/ 合并
#                             → 一个 zip 就同时具备"离线可用"和"联网自我更新"
PACKAGES = {
    "viral-producer-allinone": {
        "skills_src": ["skills", "bootstrap"],
        "title": "爆导全能版（离线 + 可自我更新，推荐只传这一个）",
    },
    "github-viral-producer": {
        "skills_src": "skills",
        "title": "爆导（完整离线版）",
    },
    "viral-producer-bootstrap": {
        "skills_src": "bootstrap",
        "title": "装配工（远程安装版）",
    },
}


def refresh_from_repo(name, cfg):
    """把仓库里最新的技能同步进专家包源码，保证 zip 是最新版。

    skills_src 可以是单个目录名，也可以是列表（多来源合并，用于全能包）。
    """
    sources = cfg["skills_src"]
    if isinstance(sources, str):
        sources = [sources]

    dst_skills = REPO / "expert" / name / "skills"
    dst_skills.mkdir(parents=True, exist_ok=True)
    copied = []
    for src_name in sources:
        src_skills = REPO / src_name
        if not src_skills.is_dir():
            print("  [ERROR] 找不到 %s" % src_skills)
            return False
        for d in sorted(p for p in src_skills.iterdir() if p.is_dir()):
            dst = dst_skills / d.name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(d, dst)
            copied.append(d.name)
    print("  同步 %d 个技能（来源 %s）：%s"
          % (len(copied), " + ".join(sources), "、".join(copied)))
    return True


def build_zip(name):
    expert_src = REPO / "expert" / name
    DIST.mkdir(parents=True, exist_ok=True)
    zip_path = DIST / ("%s.zip" % name)
    if zip_path.exists():
        zip_path.unlink()

    n = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(expert_src.rglob("*")):
            rel = p.relative_to(expert_src.parent)
            if any(part in EXCLUDE_DIRS for part in rel.parts):
                continue
            if p.is_file():
                if p.name in EXCLUDE_FILES:
                    continue
                z.write(p, rel.as_posix())
                n += 1
    size = zip_path.stat().st_size
    print("  打包 %d 个文件 → %s（%.0f KB）" % (n, zip_path.name, size / 1024))
    return zip_path


def install_local(name):
    """把专家包装进本机 WorkBuddy。"""
    expert_src = REPO / "expert" / name
    config = os.environ.get("WORKBUDDY_CONFIG_DIR", "").strip()
    base = pathlib.Path(config).expanduser() if config else pathlib.Path.home() / ".workbuddy"
    dst = base / "plugins" / "marketplaces" / "my-experts" / "plugins" / name

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(expert_src, dst)
    print("  已安装到：%s" % dst)

    # 完整包有占位符，必须跑 sync.py 写回本机路径；引导包没有占位符
    sync = dst / "sync.py"
    if sync.exists():
        import subprocess
        py = shutil.which("python3") or "python"
        r = subprocess.run([py, str(sync), "--workspace", str(REPO)],
                           capture_output=True, text=True)
        print((r.stdout or "").strip() or "  (sync 无输出)")
        if r.returncode != 0:
            print("  [WARN] sync.py 退出码 %d" % r.returncode)

    print("")
    print("  ⚠️ 装完还差一步：在 WorkBuddy 里让它重新注册才会显示。")
    print("     对 WorkBuddy 说：「用 expert-manager 注册专家 %s」" % dst)
    return dst


def main():
    ap = argparse.ArgumentParser(description="重建专家包分发 zip")
    ap.add_argument("--install", action="store_true",
                    help="顺便装进本机 WorkBuddy")
    ap.add_argument("--only", choices=list(PACKAGES), help="只构建指定的包")
    args = ap.parse_args()

    print("=" * 58)
    print("专家包构建器")
    print("=" * 58)

    made = []
    for name, cfg in PACKAGES.items():
        if args.only and name != args.only:
            continue
        expert_src = REPO / "expert" / name
        if not expert_src.is_dir():
            print("\n[WARN] 跳过 %s（找不到 %s）" % (name, expert_src))
            continue
        print("\n【%s】%s" % (name, cfg["title"]))
        if not refresh_from_repo(name, cfg):
            continue
        made.append(build_zip(name))
        if args.install:
            install_local(name)

    if not made:
        print("\n[ERROR] 没有任何包被构建")
        return 1

    print("")
    print("=" * 58)
    for p in made:
        print("✅ %s" % p)
    print("")
    print("换电脑怎么选：")
    print("  ★ 只传一个 → viral-producer-allinone.zip（约 540KB）")
    print("     自带 5 个技能离线可用，联网时还能从 GitHub 自我更新。")
    print("     导入后跑一次包里的 sync.py 写回本机路径。")
    print("  ① viral-producer-bootstrap.zip（20KB）→ 说「装一下生产线」，联网拉最新全套")
    print("  ② github-viral-producer.zip（520KB）→ 离线直接用，但版本固定在打包时")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    sys.exit(main())
