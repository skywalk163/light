# -*- coding: utf-8 -*-
"""R96 T2：版本号三处一致性校验。

光明版本号分散在三处：
  1. src/version.py 的 VERSION
  2. pyproject.toml 的 [project].version
  3. 最新语义化 tag（如 v7.0.0）

本脚本在 CI 中运行：任意两处不一致即报错，避免「文档说 7.0 但 tag 停在 6.3」的错位。

用法:
  python scripts/check_version_consistency.py            # 仅校验 1 与 2
  python scripts/check_version_consistency.py --git     # 同时校验当前 tag
  python scripts/check_version_consistency.py --strict  # 任何不一致都 rc=1（CI 用）
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _版本_from_version_py():
    path = os.path.join(ROOT, 'src', 'version.py')
    if not os.path.exists(path):
        return None
    txt = io.open(path, encoding='utf-8').read()
    m = re.search(r"^\s*VERSION\s*=\s*['\"]([^'\"]+)['\"]", txt, re.M)
    return m.group(1) if m else None


def _版本_from_pyproject():
    path = os.path.join(ROOT, 'pyproject.toml')
    if not os.path.exists(path):
        return None
    txt = io.open(path, encoding='utf-8').read()
    m = re.search(r"^\s*version\s*=\s*['\"]([^'\"]+)['\"]", txt, re.M)
    return m.group(1) if m else None


def _版本_from_git():
    try:
        out = subprocess.check_output(
            ['git', 'describe', '--tags', '--abbrev=0'],
            cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        return out.lstrip('v') if out else None
    except Exception:
        return None


def main():
    sources = {'src/version.py': _版本_from_version_py(),
               'pyproject.toml': _版本_from_pyproject()}
    if '--git' in sys.argv:
        sources['git-tag(latest)'] = _版本_from_git()

    print('版本号来源校验：')
    for k, v in sources.items():
        print('  %-20s = %s' % (k, v if v is not None else '(未找到)'))

    values = {v for v in sources.values() if v is not None}
    ok = len(values) <= 1
    if ok:
        print('\n✅ 一致：所有来源版本号相同（%s）。' % (next(iter(values)) if values else 'N/A'))
        return 0

    print('\n❌ 不一致：存在多个版本号。请统一（推荐以 src/version.py 为准）。')
    if '--strict' in sys.argv:
        return 1
    print('（非严格模式，仅提示；CI 请加 --strict。）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
