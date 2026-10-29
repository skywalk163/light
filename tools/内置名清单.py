#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输出光明**全部内置名**的机器可读清单（LH-21）。

用法:
    python tools/内置名清单.py                    # 默认：JSON 到 stdout
    python tools/内置名清单.py --json             # 同上（显式）
    python tools/内置名清单.py --python           # 只打印名字，每行一个
    python tools/内置名清单.py --check 名字       # 查询某名字是否为内置名（退出码 0/1）

输出 JSON 结构:
    {
        "内置名": ["打印", "去除空白", "是空", ...],   # 排序后
        "来源": {"打印": "内置函数", "是空": "内置函数", "整数": "内置类型", ...}
    }

设计意图（对拍 AI 生成代码/门禁用例）：
  * 让 AI 在生成 `light` 代码前先校验内置名，避免「造词」；
  * 让门禁用例能自动对拍文档（`docs/AI编程指南.md` 的「最常用内置函数」表）；
  * 刻意**不含** `去空白` 这类「常见但不存在」的错名——本清单是真实清单，
    `去除空白` 才是真的（LH-21 症状）。
"""

import json
import sys
from pathlib import Path

# 让 `src.linter.builtins` 可导入（工具常从仓库根运行）
_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / 'src')):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def load_builtin_data():
    """返回 (内置名列表(排序), 来源映射)。"""
    from src.linter.builtins import get_builtin_names, get_builtin_sources

    names = sorted(get_builtin_names())
    sources = dict(get_builtin_sources())
    return names, sources


def build_json() -> str:
    """构建机器可读 JSON 字符串。"""
    names, sources = load_builtin_data()
    payload = {
        "内置名": names,
        "来源": sources,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] == '--check':
        if len(argv) < 2:
            print("用法: python tools/内置名清单.py --check <名字>")
            return 2
        name = argv[1]
        names, _ = load_builtin_data()
        is_in = name in set(names)
        print(f"{'是' if is_in else '否'}内置名: {name}")
        return 0 if is_in else 1

    if argv and argv[0] == '--python':
        names, _ = load_builtin_data()
        for n in names:
            print(n)
        return 0

    # 默认 JSON
    print(build_json())
    return 0


if __name__ == '__main__':
    sys.exit(main())
