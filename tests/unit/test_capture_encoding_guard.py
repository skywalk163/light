# -*- coding: utf-8 -*-
"""捕获流编码护栏：被 pytest 收集的模块不许把 stdout/stderr 的 errors 收紧成 strict。

## 这条护栏钉的是什么

`tests/test_summary.py`、`tests/test_comprehensive.py`、`tests/test_class_definition.py`
曾在**模块顶层**（被 pytest 收集时就执行）调用只给 `encoding` 的 `reconfigure`。
这种写法会把 `errors` 一并重置回默认的 `strict`，而 pytest 的 fd 捕获流本来是
`errors='replace'`。收紧之后，只要后面有用例往捕获流里写进非法字节
（`tests/test_process_tree_light.py` 的 GBK 坏字节 / 混流用例正是干这个的），
pytest 每一次 setup/teardown 的 snap() 都会抛 UnicodeDecodeError。

实测后果：`pytest tests --ignore=tests/e2e` 出 **3635 个 ERROR**，而单独跑那几个文件
全绿——典型的「顺序相关、单跑看不见」的门禁污染。修法是保留 `errors='replace'`。

## 为什么用源码级断言而不是真跑

真跑复现要「污染源模块 + 写非法字节的用例」同场，且跑到全量才显形（约 11 分钟）。
这里改成 AST 级断言守单点：谁再写出不带 `errors=` 的 `reconfigure`，立刻红。

用 AST 而不是正则，是因为正则会把注释与文档字符串里的示例也算成调用——本文件
自己就写了那样的示例，第一版正则实现当场自我误报。
"""

import ast
from pathlib import Path

_仓根 = Path(__file__).resolve().parents[2]
_测试根 = _仓根 / 'tests'

# 只管**会被 pytest 收集**的模块。收集面对齐 `pyproject.toml` 的 `[tool.pytest.ini_options]`：
#   python_files = ["test_*.py", "_test_*.py"]
#   addopts = "... --ignore=tests/archive"，norecursedirs = ["archive", "__pycache__"]
# 外加 `conftest.py`（不是用例文件但同样在收集期被导入，顶层副作用一样生效）。
# `tests/verify.py`、`tests/run_tests.py` 这类独立脚本不被收集，它们的 errors 无副作用。
# 排除目录必须跟着 pyproject 走：`tests/archive/` 下是**编译产物**（光明编译器生成的 .py），
# 里面有裸 `except:` 这种 3.14 已不接受的写法，连 ast.parse 都过不去；
# 第一版把它们算进来，护栏直接崩在 SyntaxError 上。
_排除目录 = {'archive', '__pycache__'}


def _收集():
    出 = set()
    for 模式 in ('test_*.py', '_test_*.py', 'conftest.py'):
        for p in _测试根.rglob(模式):
            if _排除目录 & set(p.relative_to(_测试根).parts[:-1]):
                continue
            出.add(p)
    return sorted(出)


_被收集 = _收集()


def _查违规(源码: str):
    """返回 [(行号, 目标流名)]：sys.stdout/stderr.reconfigure(...) 里没写 errors= 的调用。"""
    结果 = []
    树 = ast.parse(源码)
    for 节点 in ast.walk(树):
        if not isinstance(节点, ast.Call):
            continue
        f = 节点.func
        if not (isinstance(f, ast.Attribute) and f.attr == 'reconfigure'):
            continue
        流 = f.value
        if not (isinstance(流, ast.Attribute) and 流.attr in ('stdout', 'stderr')):
            continue
        if not (isinstance(流.value, ast.Name) and 流.value.id == 'sys'):
            continue
        if not any(k.arg == 'errors' for k in 节点.keywords):
            结果.append((节点.lineno, 流.attr))
    return 结果


def test_被收集的模块里reconfigure必须显式给errors():
    违规 = []
    读不了 = []
    for p in _被收集:
        源 = p.read_text(encoding='utf-8', errors='replace')
        名 = p.relative_to(_仓根).as_posix()
        try:
            命中 = _查违规(源)
        except SyntaxError as e:
            # 不许静默跳过：解析不了就是护栏的盲区，直接算红并报出文件名。
            读不了.append(f'{名}:{e.lineno} {e.msg}')
            continue
        for 行号, 流名 in 命中:
            违规.append(f'{名}:{行号} sys.{流名}.reconfigure')
    assert not 读不了, (
        '这些被收集的模块 ast 解析不了，护栏看不见它们（要么修语法，要么从收集面里排掉）：\n  '
        + '\n  '.join(读不了))
    assert not 违规, (
        '这些 reconfigure 没给 errors，会把捕获流收紧成 strict，'
        '全量跑时后续用例会批量 ERROR：\n  ' + '\n  '.join(违规))


def test_收集面排掉的目录确实不被pytest收集():
    """反跑：排除清单必须与 pyproject 里的 pytest 配置一致，不能是随手加的挡箭牌。"""
    配置 = (_仓根 / 'pyproject.toml').read_text(encoding='utf-8')
    段 = 配置.split('[tool.pytest.ini_options]', 1)[1].split('\n[', 1)[0]
    for 目录 in _排除目录:
        assert f'"{目录}"' in 段, f'{目录} 不在 pyproject 的 pytest 配置里，不该被护栏排除'



def test_护栏能抓到反例():
    """反跑：确认上面那条不是永真断言。"""
    坏 = "import sys\nsys.stdout.reconfigure(encoding='utf-8')\n"
    好 = "import sys\nsys.stdout.reconfigure(encoding='utf-8', errors='replace')\n"
    无关 = "import sys\nsys.stdout.flush()\nfoo.reconfigure(encoding='utf-8')\n"
    assert _查违规(坏) == [(2, 'stdout')], _查违规(坏)
    assert _查违规(好) == []
    assert _查违规(无关) == [], '把非 sys 流的 reconfigure 也算进来了'


def test_收集面不为空():
    """再反跑一层：文件清单不能因为路径搞错而变成空集。"""
    assert len(_被收集) > 50, f'只找到 {len(_被收集)} 个被收集模块，路径大概率错了'
