# -*- coding: utf-8 -*-
"""
内置名清单 —— 光明地板内置名（内置函数 / 内置类型 / 内置异常 / 值字面量）的机器可读登记。

用途（LH-21「light check 查不出未定义名」的直接补丁）：
  * 编译前先对拍：拿到 AI 生成的光明代码后，先 `python tools/内置名清单.py --pretty | grep <名字>`
    ，命中再落盘，从源头掐掉「造词」——AI 最爱把 `去除空白` 写成 `去空白`、把 `最后索引`
    写成 `最后出现位置`；
  * 给 linter 的 E016（未定义的名字）提供权威判定依据；
  * 给 `docs/AI编程指南.md` 的「最常用内置函数」表做真伪比对（该表含 `去空白`/`转布尔`/
    `repr`/`集合创建` 四条伪内置名，见 tests/unit/test_LH21_未定义名.py 的文档门禁）。

来源（三处权威登记 + 运行时权威清单，合并去重）：
  * `src/code_generator.py::PythonCodeGenerator.builtin_map` —— Python 腿调用点重定向表
  * `src/code_generator_unified.py::UnifiedCodeGenerator.builtin_map` —— unified 腿
  * `src/keywords.py::BUILTIN_TYPES` —— 内置类型名
  * `stdlib/builtins.py::__all__` —— 运行时真正导出的地板内置函数（114+ 条）
  * `stdlib/lightpub/__index__.py::functions` —— **最全**的 lightpub 模块内置函数登记（约 2600 条）
  * `真` / `假` / `空` —— 值字面量

用法:
    python tools/内置名清单.py                    # JSON 打印到 stdout
    python tools/内置名清单.py --pretty            # 人类可读（分组、带计数）
    python tools/内置名清单.py --grep 去空白        # 精确/前缀查找某名字
    python tools/内置名清单.py --out 内置名清单.json  # 写入文件

注意：内置名是**只增不改**的登记——只读本清单不会改任何代码；若发现缺名，请去
`stdlib/builtins.py` 或 `stdlib/lightpub/__index__.py` 补，别在本文件里硬编码。
"""

import os
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))


def _load():
    """加载内置名清单。返回 (内置名排序列表, 来源登记 dict)。"""
    from linter.light_linter import builtin_names, builtin_name_sources
    names = sorted(builtin_names())
    return names, builtin_name_sources()


def _build_payload(names, sources):
    return {
        "说明": "光明地板内置名机器可读清单（LH-21）。内置名=内置函数/内置类型/内置异常/值字面量，"
                "AI 生成光明代码前请先对拍，命中才用。",
        "内置名": names,
        "来源": sources,
        "统计": {
            "总数": len(names),
            "来源登记": {
                "code_generator.builtin_map": sum(
                    1 for v in sources.values() if 'src/code_generator.py:builtin_map' in v['来源']),
                "code_generator_unified.builtin_map": sum(
                    1 for v in sources.values() if 'src/code_generator_unified.py:builtin_map' in v['来源']),
                "stdlib_builtins_all": sum(
                    1 for v in sources.values() if 'stdlib/builtins.py:__all__' in v['来源']),
                "lightpub_index_functions": sum(
                    1 for v in sources.values() if 'stdlib/lightpub/__index__.py:functions' in v['来源']),
                "内置类型": sum(1 for v in sources.values() if '内置类型' in v['类别']),
            },
        },
    }


def main():
    ap = argparse.ArgumentParser(description='输出光明地板内置名清单')
    ap.add_argument('--pretty', action='store_true', help='人类可读分组输出')
    ap.add_argument('--grep', metavar='词', help='按名字精确/前缀查找')
    ap.add_argument('--out', metavar='文件', help='把 JSON 写入文件')
    args = ap.parse_args()

    names, sources = _load()

    if args.grep:
        hits = [n for n in names if args.grep in n]
        if hits:
            for n in hits:
                srcs = sources.get(n, {}).get('来源', [])
                print(f"{n}  ← {', '.join(srcs)}")
        else:
            print(f"（未找到内含「{args.grep}」的内置名）")
            # 顺手给出疑似正确拼写：最长公共前缀的候选
            cand = [n for n in names if n[:len(args.grep)] == args.grep[:len(n)]]
            if cand:
                print(f"  可能想找：{', '.join(cand[:10])}")
        return 0

    payload = _build_payload(names, sources)

    if args.pretty:
        print(f"光明地板内置名：共 {payload['统计']['总数']} 个")
        print("=" * 60)
        for cat in ('内置函数', '内置类型', '内置异常', '字面量'):
            items = sorted(n for n, v in sources.items() if cat in v['类别'])
            if items:
                print(f"\n【{cat}】 {len(items)} 个")
                print('  ' + ' '.join(items))
        print("\n" + "=" * 60)
        print("来源分布：")
        for k, v in payload['统计']['来源登记'].items():
            print(f"  {k}: {v}")
        return 0

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"已写入 {args.out}（{payload['统计']['总数']} 个内置名）")
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
