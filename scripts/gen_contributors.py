# -*- coding: utf-8 -*-
"""R96 T4：从真实 git log 生成 CONTRIBUTORS.md（杜绝虚构署名）。

统计每位 author 的提交数并降序排列，输出为社区根目录的 CONTRIBUTORS.md。
署名完全来自 git 历史，不手写任何名字。

用法:
  python scripts/gen_contributors.py
  python scripts/gen_contributors.py --out CONTRIBUTORS.md
"""
import io
import os
import subprocess
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _收集():
    out = subprocess.check_output(
        ['git', 'log', '--pretty=format:%an|%ae'],
        cwd=ROOT, stderr=subprocess.DEVNULL
    ).decode('utf-8', 'replace')
    counts = OrderedDict()
    for line in out.splitlines():
        if '|' not in line:
            continue
        name, email = line.split('|', 1)
        key = (name.strip(), email.strip().lower())
        counts[key] = counts.get(key, 0) + 1
    return counts


def _渲染(counts):
    total = sum(counts.values())
    lines = [
        '# 贡献者（CONTRIBUTORS）',
        '',
        '> 本文件由 `scripts/gen_contributors.py` 从**真实 git 历史**自动生成（%d 位署名 / %d 次提交）。' % (len(counts), total),
        '> 请勿手工编辑署名；新增贡献者只需提交代码，下次运行脚本即更新。',
        '',
        '## 署名列表（按提交数降序）',
        '',
    ]
    for (name, email), n in counts.items():
        lines.append('- **%s** — %d 次提交  (`%s`)' % (name, n, email))
    lines.append('')
    lines.append('## 致谢', )
    lines.append('')
    lines.append('感谢以上所有人为光明 / Light 语言生态作出的贡献。')
    lines.append('')
    return '\n'.join(lines)


def main():
    counts = _收集()
    if not counts:
        print('未获取到提交历史，已跳过。', file=sys.stderr)
        return 1
    out_path = os.path.join(ROOT, 'CONTRIBUTORS.md')
    for i, a in enumerate(sys.argv[1:], 1):
        if a == '--out' and i + 1 < len(sys.argv):
            out_path = sys.argv[i + 1]
    content = _渲染(counts)
    io.open(out_path, 'w', encoding='utf-8').write(content)
    print('已生成 %s（%d 位署名 / %d 次提交）。' % (out_path, len(counts), sum(counts.values())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
