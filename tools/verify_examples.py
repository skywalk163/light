#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证所有段言示例文件的语法正确性"""

import sys
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR / 'src'))
sys.path.insert(0, str(PROJECT_DIR))

from duan_parser_v3 import DuanParser

EXAMPLES = [
    "examples/todo_app/main.duan",
    "examples/blog_app/main.duan",
    "examples/data_pipeline/pipeline.duan",
    "examples/games/guess_number.duan",
    "examples/games/snake.duan",
    "examples/algorithms/sorting.duan",
    "examples/algorithms/data_structures.duan",
]

def verify():
    parser = DuanParser()
    ok = 0
    fail = 0
    errors = []

    for rel_path in EXAMPLES:
        abs_path = PROJECT_DIR / rel_path
        print(f"--- 检查: {rel_path} ---")
        try:
            source = abs_path.read_text(encoding='utf-8')
            module = parser.parse(source)
            if module is not None:
                print("  语法 OK")
                ok += 1
            else:
                print("  语法 FAIL: 解析返回 None")
                fail += 1
                errors.append(rel_path)
        except Exception as e:
            print(f"  语法 FAIL: {e}")
            fail += 1
            errors.append(rel_path)

    print(f"\n{'='*50}")
    print(f"结果: {ok} 通过, {fail} 失败")
    if errors:
        print(f"失败文件: {errors}")
    return fail == 0

if __name__ == '__main__':
    success = verify()
    sys.exit(0 if success else 1)