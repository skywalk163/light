# -*- coding: utf-8 -*-
"""重生成 tests/unit/doc_examples_baseline.json（阶段 3 文档示例编译门禁的基线）。

    python tools/ci/run_with_memory_cap.py tools/ci/gen_doc_examples_baseline.py

## 什么时候跑

修好一批文档代码块之后。基线应当**只降不升**：
`test_基线里修好的条目必须下线` 会在你修好却忘了重生成时报红。

## 安全须知：别裸跑，走 run_with_memory_cap.py

2026-08-20 事故：本脚本的前身裸跑在后台，15 分钟吃到 **15.5GB 且仍在涨**
（~2GB/分钟，只增不减），最后靠 `Stop-Process` 掐掉。根因不在本脚本，而在
光明 parser——`匹配` 的列表 rest 模式 `情况 [头, 尾...]` 会让它进入不终止的
分配循环（单变量 A/B：去掉 `...` 则 1.0s / 17MB 正常通过）。

现在该块已进 `tests/unit/doc_block_scan._HOSTILE_HASHES`，扫描时根本不喂给
parser，正常峰值约 **22MB / 2 秒**。但只要 docs 里再出现同类写法（rest 模式、
或任何别的无限分配触发点），就会再次失控。所以：

- **别用后台任务裸跑本脚本。** 后台跑意味着没人看着内存。
- 一律经 `tools/ci/run_with_memory_cap.py` 包一层（外部看门狗，超限即 kill）；
  为什么必须是外部看门狗、进程内自救为何不可行，见那个文件的文档串。
- 跑完确认输出里的 peak 在几十 MB 量级；若看到几百 MB 起跳，立刻停手排查，
  多半是又踩到一个无限分配块——**别去调大上限**。
"""

import json
import os
import sys
from collections import Counter

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_ROOT, 'tests', 'unit'))

from doc_block_scan import scan_all, classify   # noqa: E402

_OUT = os.path.join(_ROOT, 'tests', 'unit', 'doc_examples_baseline.json')


def main():
    results = scan_all()
    entries = []
    for r in results:
        if r['exc'] is None:
            continue
        entries.append({
            'file': r['file'],
            'hash': r['hash'],
            'category': classify(r['code'], r['exc'], r['msg']),
            'exc': r['exc'],
            'first_line': r['first_line'][:64],
        })
    entries.sort(key=lambda e: (e['file'], e['hash']))
    out = {
        'note': '本文件由 tools/ci/gen_doc_examples_baseline.py 生成，勿手改；'
                '分类口径见 tests/unit/test_doc_examples_gate.py 模块文档串',
        'total_scanned': len(results),
        'failing': len(entries),
        'entries': entries,
    }
    with open(_OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('scanned', len(results), 'failing', len(entries),
          dict(Counter(e['category'] for e in entries)))
    print('written', os.path.relpath(_OUT, _ROOT))


if __name__ == '__main__':
    main()
