# -*- coding: utf-8 -*-
"""版本号单一真源门禁（v7 版本口径单，阶段 1）。

## 立项由来

外部 AI 用光明做项目时报「编译器版本与文档版本存在语法差异」，编出了一个
仓库里根本不存在的号段（`v1.10.3`）。查下来 `1.10.x` 全仓零命中，但它反映的
问题是真的：同一个 HEAD 上对外可见的版本号有 **五个不同的值**，版本号本身
已经不携带信息了。修前实测：

- `src/version.py:9` = 7.0.0（`pyproject.toml` 一致，事实权威）
- `src/__init__.py:16` = 6.0.0（死值，全仓无人 import）
- `src/compiler.py:914` = 6.1.0，且 `python -m src.compiler --version` 真打印它
- `README.md:181` 让用户装完校验时**预期看到 `光明编译器 v1.9.0`**
- 三个安装脚本 = 6.1.0；两个 VS Code 扩展目录 = 0.1.0 / 5.0.0

## 本文件的职责

把「散开」这件事变成 CI 红。**只改文件不加门禁等于没修**——这些号段当初都
是随手写的字面量，下一次发版会以同样的方式再散一遍。

判据分两类，都不依赖 Python 版本 / 平台 / 外部工具链（口径 5(1)）：

1. **POSITIVE**：白名单文件里由指定正则捕到的每个版本串，必须等于
   `src/version.py` 的 `VERSION`。每条都带 `至少命中一次` 断言——否则有人把
   那行改名/删掉，正则空转，断言会**退化成永真式**（口径 16(3) 的坑）。
2. **NEGATIVE**：已经改成动态读取的位置，不得再出现写死的编译器版本字面量。
   这是回归守卫，防止「以后顺手又写回去」。

刻意**不纳入**门禁的版本号（它们不是编译器版本，纳入就是错咬）：

- `cli/light_unified.py` 里 `light.json` 脚手架模板的 `"version": "0.1.0"`
  ——那是给用户新建项目的默认值。
- `pyproject.toml` 的 `target-version` / `python_version`、`Depends: python3`
  ——Python 版本要求。
- `vscode-extension/package.json`（0.1.0）与 `vscode-light/CHANGELOG.md`（5.0.0）
  ——扩展有独立发布节奏，且 `.vsix` 产物名属用户可见契约，归 contract 阶段。

## 反跑（防永真式，口径 17）

落地后必须把源改动整体拉掉再跑本文件确认会红：

    git stash push -- src/__init__.py src/compiler.py cli/lightc.py \
        cli/light.py cli/light_unified.py README.md tools/installer
    python -m pytest tests/unit/test_version_single_source.py
    git stash pop

实测反跑 **6 failed / 3 passed**。绿的 3 条是 `test_权威真源自洽`、
`test_pyproject_与真源一致`、`test_CHANGELOG_最新条目等于真源`——它们改前也必须
绿（真源与打包元数据本来就是对的，散开的是下游；CHANGELOG 顶条本来就是
7.0.0，本单未动它），那正是「守卫不该反跑变红」的含义。

注：本文件初版把反跑预期写成 7 failed / 2 passed，是**凭推演写的**，实测差一条
（漏算了 CHANGELOG 不在本单改动面内，反跑时不会红）。反跑数字一律填实测值——
这条正是 31-E/31-G 那个教训的同型复发。

"""

import os
import re
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_ROOT, 'src'), _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from version import VERSION, __version__ as VERSION_DUNDER  # noqa: E402


def _read(*parts):
    path = os.path.join(_ROOT, *parts)
    with open(path, encoding='utf-8') as f:
        return path, f.read()


# (相对路径, 正则, 说明) —— 正则必须恰好圈住「编译器版本」这一个语义位置
_POSITIVE_CHECKS = [
    (
        ('src', 'version.py'),
        r'^VERSION = "([\d.]+)"',
        '唯一真源的 VERSION',
    ),
    (
        ('pyproject.toml',),
        r'(?m)^version = "([\d.]+)"',
        '打包元数据版本',
    ),
    (
        ('cli', 'light.py'),
        r"VERSION = '光明编译器 v([\d.]+)'",
        'ImportError 兜底串（导不到 src.version 时的显示值）',
    ),
    (
        ('cli', 'light_unified.py'),
        r"VERSION_STR = '光明 v([\d.]+)'",
        'ImportError 兜底串',
    ),
    (
        ('README.md',),
        r'# 输出：光明编译器 v([\d.]+)',
        '安装校验示例的预期输出',
    ),
    (
        ('tools', 'installer', 'windows', 'setup.iss'),
        r'#define MyAppVersion "([\d.]+)"',
        'Windows 安装包版本',
    ),
    (
        ('tools', 'installer', 'macos', 'build_pkg.sh'),
        r'^VERSION="([\d.]+)"',
        'macOS 安装包版本',
    ),
    (
        ('tools', 'installer', 'linux', 'build_deb.sh'),
        r'^VERSION="([\d.]+)"',
        'Linux .deb 构建脚本版本',
    ),
    (
        ('tools', 'installer', 'linux', 'build_deb.sh'),
        r'^Version: ([\d.]+)',
        'Linux .deb control 文件版本（在 quoted heredoc 里，$VERSION 不展开）',
    ),
]

# (相对路径, 禁止出现的正则, 说明) —— 已改成动态读取的位置
_NEGATIVE_CHECKS = [
    (
        ('src', '__init__.py'),
        r'__version__\s*=\s*[\'"][\d.]+[\'"]',
        'src/__init__.py 必须从 version.py 转发，不得写死（原为 6.0.0 死值）',
    ),
    (
        ('src', 'compiler.py'),
        r'VERSION\s*=\s*[\'"][\d.]+[\'"]',
        'LightCompiler.VERSION 必须读 version.py（原为 6.1.0，--version 真打印它）',
    ),
    (
        ('cli', 'lightc.py'),
        r"version='光明编译器 v[\d.]+'",
        'lightc --version 必须读 version.py（原为硬编码字面量）',
    ),
]


class TestVersionSingleSource(unittest.TestCase):

    def test_权威真源自洽(self):
        """version.py 内部两个导出必须一致，且形如 X.Y.Z。"""
        self.assertEqual(VERSION, VERSION_DUNDER)
        self.assertRegex(VERSION, r'^\d+\.\d+\.\d+$')

    def test_pyproject_与真源一致(self):
        path, text = _read('pyproject.toml')
        m = re.search(r'(?m)^version = "([\d.]+)"', text)
        self.assertIsNotNone(m, f'{path} 里找不到 project 版本行——正则失效，'
                                f'本断言已退化，请修正正则而非删掉本条')
        self.assertEqual(m.group(1), VERSION)

    def test_src_包属性转发真源(self):
        """`import src; src.__version__` 必须等于真源，而非独立字面量。"""
        import importlib
        src_pkg = importlib.import_module('src')
        self.assertEqual(src_pkg.__version__, VERSION)

    def test_编译器类版本读真源(self):
        """`LightCompiler.VERSION` 决定 `python -m src.compiler --version` 的输出。"""
        from compiler import LightCompiler
        self.assertEqual(LightCompiler.VERSION, VERSION)

    def test_所有对外可见版本串等于真源(self):
        """POSITIVE：白名单里每处捕获值都等于 VERSION，且每条正则至少命中一次。"""
        problems = []
        for parts, pattern, desc in _POSITIVE_CHECKS:
            path, text = _read(*parts)
            found = re.findall(pattern, text, re.MULTILINE)
            if not found:
                problems.append(
                    f'{os.path.join(*parts)}：正则 {pattern!r} 零命中（{desc}）'
                    f'——该位置被改名或删除，断言已失效，不是「通过」'
                )
                continue
            for got in found:
                if got != VERSION:
                    problems.append(
                        f'{os.path.join(*parts)}：{desc} = {got}，真源 = {VERSION}'
                    )
        self.assertEqual([], problems, '版本号散开：\n' + '\n'.join(problems))

    def test_已收口位置不得再写死版本(self):
        """NEGATIVE：回归守卫，防止改回字面量。"""
        problems = []
        for parts, pattern, desc in _NEGATIVE_CHECKS:
            path, text = _read(*parts)
            hits = re.findall(pattern, text)
            if hits:
                problems.append(f'{os.path.join(*parts)}：{desc}；命中 {hits}')
        self.assertEqual([], problems, '出现写死的版本字面量：\n' + '\n'.join(problems))

    def test_CHANGELOG_最新条目等于真源(self):
        """发版时 CHANGELOG 必须同步——否则用户看到的「最新版」不是实际装到的版本。"""
        path, text = _read('CHANGELOG.md')
        m = re.search(r'(?m)^## \[([\d.]+)\]', text)
        self.assertIsNotNone(m, f'{path} 里找不到 `## [X.Y.Z]` 形态的版本条目')
        self.assertEqual(m.group(1), VERSION,
                         'CHANGELOG 最新条目与真源不一致')

    def test_不得再出现历史号段(self):
        """钉住本单修掉的五个具体错值，把「已修」写成可执行的记录。

        这条不是重复上面的检查：上面查的是「等于真源」，这条查的是「那几个
        具体的错值不再出现在那几个具体位置」。真源哪天升到 8.0.0，上面会红、
        这条仍绿，两条职责不同。
        """
        stale = {
            ('src', '__init__.py'): ['6.0.0'],
            ('src', 'compiler.py'): ['6.1.0'],
            ('README.md'): ['v1.9.0'],
            ('tools', 'installer', 'windows', 'setup.iss'): ['6.1.0'],
            ('tools', 'installer', 'macos', 'build_pkg.sh'): ['6.1.0'],
            ('tools', 'installer', 'linux', 'build_deb.sh'): ['6.1.0'],
        }
        problems = []
        for parts, bad_values in stale.items():
            if isinstance(parts, str):
                parts = (parts,)
            _, text = _read(*parts)
            for bad in bad_values:
                if bad in text:
                    problems.append(f'{os.path.join(*parts)}：残留历史号段 {bad}')
        self.assertEqual([], problems, '\n'.join(problems))

    def test_dev_分支串不得写死旧主版本(self):
        """`v4.0dev-7.0.0` 这种「旧主版本 + 新号」的拼法已废，改为 `v7.0.0dev`。

        DEV_BRANCH 当前为 False，这两处是休眠代码——正因为休眠，没有任何用例
        会踩到它，只能靠静态断言钉住。
        """
        for parts in (('cli', 'light.py'), ('cli', 'light_unified.py')):
            _, text = _read(*parts)
            self.assertNotIn('v4.0dev-', text,
                             f'{os.path.join(*parts)}：dev 版本串仍写死旧主版本 4.0')
            self.assertIn(f'v{{LANG_VERSION}}dev', text,
                          f'{os.path.join(*parts)}：dev 版本串未改为读 LANG_VERSION')


if __name__ == '__main__':
    unittest.main()
