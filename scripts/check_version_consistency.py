# -*- coding: utf-8 -*-
"""R96 T2 / T-0265：版本号一致性校验（可从外部指定仓库）。

默认行为（向后兼容，R96 起 CI 就一直这么跑）：
  python scripts/check_version_consistency.py            # 只查本仓 src/version.py + pyproject.toml
  python scripts/check_version_consistency.py --git      # 再加上最近 tag
  python scripts/check_version_consistency.py --strict   # 不一致时 rc=1（CI 用）

T-0265 起支持跨仓（自动探测该仓存在的版本声明点）：
  python scripts/check_version_consistency.py --repo ../hive
  python scripts/check_version_consistency.py --repo .

跨仓模式默认严格（不一致即 rc=1），输出会写清：
  - 每个探测点查到的值；
  - 哪个文件该改、改成什么、以谁为准（单一真源口径见 docs/版本号口径.md）。

探测点（按存在性自动探测，不存在就跳过）：
  pyproject.toml 的 version / src/version.py 的 VERSION / hive.py 的 VERSION
  CHANGELOG.md 首条语义化版本 / cli.light_unified --version 输出 / 最近 git tag

本脚本只读；不修改任何文件、不打印任何凭据。
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 0.4.1 / 7.0.0 / 0.5.0-rc1 / 1.2.3.beta 之类；不匹配 "未发布"、"Unreleased"。
_版本号RE = re.compile(r'[0-9]+(?:\.[0-9]+)+(?:[-+][0-9A-Za-z.\-]+)?')

# 各仓的「单一真源」：键为仓库目录名，值为探测点标签。
_真源 = {
    'light': 'pyproject.toml',
    'hive': 'hive.py VERSION',
    'lightharness': 'CHANGELOG.md 首条',
    'lightmem': '最近 tag',
    'lightplugin': '最近 tag',
}
_真源理由 = {
    'light': '它是打包/发布入口，src/version.py 与 CHANGELOG 都必须跟它',
    'hive': '它是运行时真源（hive --version 打印的就是它）',
    'lightharness': '无 pyproject，CHANGELOG 首条是当前唯一人工维护的版本声明',
    'lightmem': '无 pyproject，git tag 是唯一机器可校验点',
    'lightplugin': '无 pyproject，git tag 是唯一机器可校验点',
}


def _读(path):
    try:
        return io.open(path, encoding='utf-8', errors='replace').read()
    except Exception:      # noqa: BLE001
        return ''


def _从文件(path, pattern):
    txt = _读(path)
    m = re.search(pattern, txt, re.M)
    return m.group(1) if m else None


def _版本_from_version_py(root):
    return _从文件(os.path.join(root, 'src', 'version.py'),
                   r"^\s*VERSION\s*=\s*['\"]([^'\"]+)['\"]")


def _版本_from_pyproject(root):
    return _从文件(os.path.join(root, 'pyproject.toml'),
                   r"^\s*version\s*=\s*['\"]([^'\"]+)['\"]")


def _版本_from_hive_py(root):
    return _从文件(os.path.join(root, 'hive.py'),
                   r"^\s*VERSION\s*=\s*['\"]([^'\"]+)['\"]")


def _版本_from_changelog(root):
    """取 CHANGELOG 首条语义化版本；跳过 [未发布]/Unreleased 这类占位条。"""
    path = os.path.join(root, 'CHANGELOG.md')
    if not os.path.exists(path):
        return None
    for line in _读(path).splitlines():
        if not line.startswith('##'):
            continue
        m = _版本号RE.search(line)
        if m:
            return m.group(0)
    return None


def _版本_from_git(root):
    if not os.path.exists(os.path.join(root, '.git')):
        return None
    try:
        out = subprocess.check_output(
            ['git', 'describe', '--tags', '--abbrev=0'],
            cwd=root, stderr=subprocess.DEVNULL, timeout=8
        ).decode('utf-8').strip()
        return out or None
    except Exception:      # noqa: BLE001
        return None


def _版本_from_cli(root):
    """light 专用：跑 `python -m cli.light_unified --version`，从输出里取 vX.Y.Z。"""
    if not os.path.exists(os.path.join(root, 'cli', 'light_unified.py')):
        return None, '未找到 cli.light_unified，跳过'
    try:
        out = subprocess.check_output(
            [sys.executable, '-m', 'cli.light_unified', '--version'],
            cwd=root, stderr=subprocess.STDOUT, timeout=20
        ).decode('utf-8', 'replace').strip()
        m = re.search(r'v?(' + _版本号RE.pattern + ')', out)
        return (m.group(1) if m else None), ('' if m else '输出里没有版本号：%s' % out[-80:])
    except Exception as e:      # noqa: BLE001
        return None, '运行失败（%s），跳过' % type(e).__name__


def _归一(v):
    """v0.15.2 / V0.15.2 -> 0.15.2；用于比较，不用于展示。"""
    return v.lstrip('vV') if isinstance(v, str) else v


# ---------------------------------------------------------------- 默认模式

def _默认校验(check_git, strict):
    """历史行为：只查 src/version.py + pyproject.toml，输出格式保持不变。"""
    sources = {'src/version.py': _版本_from_version_py(ROOT),
               'pyproject.toml': _版本_from_pyproject(ROOT)}
    if check_git:
        tag = _版本_from_git(ROOT)
        # 旧版会 lstrip('v') 再展示/比较，这里保持一致（向后兼容）。
        sources['git-tag(latest)'] = _归一(tag) if tag else None

    print('版本号来源校验：')
    for k, v in sources.items():
        print('  %-20s = %s' % (k, v if v is not None else '(未找到)'))

    values = {v for v in sources.values() if v is not None}
    if len(values) <= 1:
        print('\n✅ 一致：所有来源版本号相同（%s）。' % (
            next(iter(values)) if values else 'N/A'))
        return 0

    print('\n❌ 不一致：存在多个版本号。请统一（推荐以 src/version.py 为准）。')
    if strict:
        return 1
    print('（非严格模式，仅提示；CI 请加 --strict。）')
    return 0


# ---------------------------------------------------------------- 跨仓模式

def _探测(root):
    """返回 [(展示标签, 原始值或 None, 备注), ...]，只读。"""
    probes = []
    probes.append(('pyproject.toml', _版本_from_pyproject(root), ''))
    probes.append(('src/version.py', _版本_from_version_py(root), ''))
    probes.append(('hive.py VERSION', _版本_from_hive_py(root), ''))
    probes.append(('CHANGELOG.md 首条', _版本_from_changelog(root), ''))
    cli_v, cli_note = _版本_from_cli(root)
    probes.append(('cli --version', cli_v, cli_note))
    probes.append(('最近 tag', _版本_from_git(root), ''))
    return probes


def _报告(root):
    name = os.path.basename(os.path.abspath(root))
    print('[%s]' % name)
    rows = _探测(root)
    present = [(k, v) for k, v, _ in rows if v]
    for k, v, note in rows:
        if v:
            print('  %-20s = %s' % (k, v))
        elif note:
            print('  %-20s = (跳过：%s)' % (k, note))

    if not present:
        print('  ! 探测不到任何版本声明点（无 pyproject/hive.py/CHANGELOG/git tag），跳过本仓')
        return 0

    # 单一真源：优先按仓库名；不在表里就取第一个探测到且“文件类”的点。
    canonical_label = _真源.get(name)
    if canonical_label not in [k for k, _ in present]:
        file_like = [k for k, _ in present if not k.startswith(('最近 tag', 'cli '))]
        canonical_label = file_like[0] if file_like else present[0][0]
    canonical_value = dict(present)[canonical_label]

    归一值 = {_归一(v) for _, v in present}
    if len(归一值) <= 1:
        print('  ✅ 一致：%d 个探测点版本号相同（%s）。' % (len(present), _归一(canonical_value)))
        return 0

    print('  ✗ 不一致：存在多个版本号。')
    建议 = []
    for label, value in present:
        if _归一(value) == _归一(canonical_value):
            continue
        差值 = '%s(%s) != %s(%s)' % (label, value, canonical_label, canonical_value)
        print('  ✗ %s' % 差值)
        建议.append('  %s 改为 %s（以 %s 为准，%s）' % (
            label, _归一(canonical_value), canonical_label,
            _真源理由.get(name, '该点是本仓的单一真源')))
    for s in 建议:
        print('  建议：%s' % s.strip())
    if name == 'hive':
        print('  （hive 的 pyproject.toml 修复已拆给 T-0272，本脚本只报告、不代改。）')
    return 1


def main():
    args = sys.argv[1:]
    repo = None
    for i, a in enumerate(args):
        if a == '--repo':
            if i + 1 >= len(args):
                print('错误：--repo 需要一个仓库路径', file=sys.stderr)
                return 2
            repo = args[i + 1]
        elif a.startswith('--repo='):
            repo = a.split('=', 1)[1]
    check_git = '--git' in args
    strict = '--strict' in args

    if repo is None:
        return _默认校验(check_git, strict)

    root = os.path.abspath(repo)
    if not os.path.isdir(root):
        print('错误：--repo 指向的目录不存在：%s' % repo, file=sys.stderr)
        return 2
    return _报告(root)


if __name__ == '__main__':
    sys.exit(main())
