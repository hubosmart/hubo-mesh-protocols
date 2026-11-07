#!/usr/bin/env python3
"""Check that docs/en and docs/zh-CN contain the same file names.
比对 docs/en 与 docs/zh-CN 的文件清单（参考 ESP-IDF 的做法），不一致返回 1。
用法 / usage: python tools/check_lang_sync.py [repo_root]
"""
import sys
from pathlib import Path


def file_set(root: Path) -> set:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def diff(en: Path, zh: Path):
    a, b = file_set(en), file_set(zh)
    return sorted(a - b), sorted(b - a)


def main(argv=None):
    base = Path(argv[0]) if argv else Path(".")
    only_en, only_zh = diff(base / "docs" / "en", base / "docs" / "zh-CN")
    for f in only_en:
        print(f"[FAIL] 只有英文 / only in en: {f}")
    for f in only_zh:
        print(f"[FAIL] 只有中文 / only in zh-CN: {f}")
    if only_en or only_zh:
        return 1
    print("[OK] 中英文文档文件清单一致 / en and zh-CN file lists match")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
