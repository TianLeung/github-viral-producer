#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库打包器 —— 把「私有资产」单独打包带走，不进 git。

背景：
  提示词原文（PDF / Pages）是你的付费或私有方法论，参考视频是他人的版权内容。
  这两类东西一旦 push 到公开仓库，Git 历史会永久保留，删不干净。
  所以仓库 .gitignore 已经把它们排除，换机时改用本脚本打包，走网盘 / 移动硬盘带走。

用法：
  python3 pack_knowledge.py                       # 打包到 dist/knowledge-kit-日期.zip
  python3 pack_knowledge.py --icloud              # 打包 + 复制一份到 iCloud Drive
  python3 pack_knowledge.py --to /某目录          # 打包 + 复制一份到指定目录（U盘等）

换机后：把 zip 拷到新电脑，解压到工作区根目录即可（解压出 相关参考提示词/ 和 参考视频/）。
"""

import argparse
import datetime
import pathlib
import shutil
import sys
import zipfile

REPO = pathlib.Path(__file__).resolve().parent
DIST = REPO / "dist"
KNOWLEDGE_DIRS = ["相关参考提示词", "参考视频"]


def build_zip():
    DIST.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().strftime("%Y-%m-%d")
    zip_path = DIST / ("knowledge-kit-%s.zip" % today)
    if zip_path.exists():
        zip_path.unlink()

    n = 0
    total = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for d in KNOWLEDGE_DIRS:
            src = REPO / d
            if not src.is_dir():
                continue
            for p in sorted(src.rglob("*")):
                if p.is_dir() or p.name in {".DS_Store"}:
                    continue
                z.write(p, p.relative_to(REPO).as_posix())
                n += 1
                total += p.stat().st_size
    return zip_path, n, total


def main():
    ap = argparse.ArgumentParser(description="打包私有知识库（不进 git）")
    ap.add_argument("--icloud", action="store_true", help="同时复制一份到 iCloud Drive")
    ap.add_argument("--to", metavar="目录", help="同时复制一份到指定目录（U 盘、网盘等）")
    args = ap.parse_args()

    print("=" * 58)
    print("知识库打包器（私有资产，不进 git）")
    print("=" * 58)

    missing = [d for d in KNOWLEDGE_DIRS if not (REPO / d).is_dir()]
    if missing == KNOWLEDGE_DIRS:
        print("[ERROR] 两个知识库目录都不存在，没有可打包的内容。")
        return 1

    zip_path, n, total = build_zip()
    print("  打包 %d 个文件 → %s（%.1f MB）" % (n, zip_path, total / 1024 / 1024))
    if missing:
        print("  [!] 缺少：%s" % "、".join(missing))

    # 复制到 iCloud
    if args.icloud:
        icloud = (pathlib.Path.home() / "Library" / "Mobile Documents"
                  / "com~apple~CloudDocs")
        if icloud.is_dir():
            dst = icloud / zip_path.name
            shutil.copy2(zip_path, dst)
            print("  ✅ 已复制到 iCloud Drive：%s" % dst)
        else:
            print("  [!] 未找到 iCloud Drive，跳过")

    # 复制到指定目录
    if args.to:
        target = pathlib.Path(args.to).expanduser()
        if target.is_dir():
            dst = target / zip_path.name
            shutil.copy2(zip_path, dst)
            print("  ✅ 已复制到：%s" % dst)
        else:
            print("  [!] 目录不存在，跳过：%s" % target)

    print("")
    print("  换机后：把 zip 拷过去，解压到工作区根目录，")
    print("          解压出「相关参考提示词/」和「参考视频/」即可。")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    sys.exit(main())
