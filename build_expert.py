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
EXPERT_SRC = REPO / "expert" / "github-viral-producer"
DIST = REPO / "dist"
ZIP_NAME = "github-viral-producer.zip"

# 打 zip 时排除的东西
EXCLUDE_DIRS = {"__pycache__", ".git", ".DS_Store"}
EXCLUDE_FILES = {".DS_Store", ".gitkeep"}


def refresh_from_repo():
    """把仓库里最新的 skills 和 sync.py 同步进专家包源码，保证 zip 是最新版。"""
    src_skills = REPO / "skills"
    dst_skills = EXPERT_SRC / "skills"
    if not src_skills.is_dir():
        print("[ERROR] 找不到仓库 skills/ 目录：%s" % src_skills)
        return False

    dst_skills.mkdir(parents=True, exist_ok=True)
    copied = []
    for d in sorted(p for p in src_skills.iterdir() if p.is_dir()):
        dst = dst_skills / d.name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(d, dst)
        copied.append(d.name)
    print("  同步 %d 个技能：%s" % (len(copied), "、".join(copied)))

    # sync.py 以仓库根为准？不，sync.py 属于专家包，保持 expert/ 里的版本
    return True


def build_zip():
    DIST.mkdir(parents=True, exist_ok=True)
    zip_path = DIST / ZIP_NAME
    if zip_path.exists():
        zip_path.unlink()

    n = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(EXPERT_SRC.rglob("*")):
            rel = p.relative_to(EXPERT_SRC.parent)
            if any(part in EXCLUDE_DIRS for part in rel.parts):
                continue
            if p.is_file():
                if p.name in EXCLUDE_FILES:
                    continue
                z.write(p, rel.as_posix())
                n += 1
    size = zip_path.stat().st_size
    print("  打包 %d 个文件 → %s（%.0f KB）" % (n, zip_path, size / 1024))
    return zip_path


def install_local():
    """把专家包装进本机 WorkBuddy 并跑一次 sync.py。"""
    config = os.environ.get("WORKBUDDY_CONFIG_DIR", "").strip()
    base = pathlib.Path(config).expanduser() if config else pathlib.Path.home() / ".workbuddy"
    dst = base / "plugins" / "marketplaces" / "my-experts" / "plugins" / "github-viral-producer"

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(EXPERT_SRC, dst)
    print("  已安装到：%s" % dst)

    # 写回本机真实路径
    import subprocess
    py = shutil.which("python3") and "python3" or "python"
    r = subprocess.run([py, str(dst / "sync.py"), "--workspace", str(REPO)],
                       capture_output=True, text=True)
    print(r.stdout.strip() if r.stdout else "  (sync 无输出)")
    if r.returncode != 0:
        print("  [WARN] sync.py 退出码 %d" % r.returncode)

    print("")
    print("  ⚠️ 装完还差一步：在 WorkBuddy 里让它重新注册才会显示。")
    print("     对 WorkBuddy 说：「用 expert-manager 注册专家 %s」" % dst)
    return dst


def main():
    ap = argparse.ArgumentParser(description="重建专家包分发 zip")
    ap.add_argument("--install", action="store_true",
                    help="顺便装进本机 WorkBuddy 并跑 sync.py")
    args = ap.parse_args()

    print("=" * 58)
    print("专家包构建器 · 开源爆款短视频制片人")
    print("=" * 58)

    if not EXPERT_SRC.is_dir():
        print("[ERROR] 找不到 %s" % EXPERT_SRC)
        return 1

    if not refresh_from_repo():
        return 1

    zip_path = build_zip()

    if args.install:
        print("")
        install_local()

    print("")
    print("=" * 58)
    print("✅ 完成：%s" % zip_path)
    print("")
    print("换电脑时：WorkBuddy 专家中心 → 导入这个 zip → 跑专家包里的 sync.py")
    print("           （或让 AI 用 viral-producer-sync 技能从 GitHub 拉最新版）")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    sys.exit(main())
