# -*- coding: utf-8 -*-
"""R157-B · `tests/` 顶层门禁下一档：xfail 用例不得因 ImportError 而 xfail。

为什么要有这道门
----------------
R153 的 `tests/test_R153_顶层collect门禁.py` 挡住了**模块级** ImportError（collect-only，
rc != 0 即红），但它的文档字符串里明文登记了一个更深的洞：

    函数内 ImportError 若发生在 `pytest.mark.xfail(strict=False)` 用例里，会被**吞成 xfail**
    （`test_stdlib_phase4.py:303` 正是如此），即使顶层真跑起来也不红。
    要堵这一档需要「xfail 用例不得因 ImportError 而 xfail」的专项，属下一档门禁。

**本文件就是那个「下一档」**（R157 任务书 B 线）。

本门做什么 / 不做什么
----------------------
* **做**：
  1. **动态枚举** `tests/` 顶层全部 xfail 构造（AST，无手抄清单，新增 xfail 自动入面）：
     - 声明式 `@pytest.mark.xfail(...)` 装饰的用例（按 `文件::类::方法` 定位）；
     - 命令式 `pytest.xfail(...)` 调用所在用例（辅助函数里的调用解析到同文件测试调用方）。
  2. **动态执行**：对枚举出的节点跑 `pytest --runxfail`（xfail 标记/命令式调用全部失效，
     用例按普通用例真跑，失败如实报 failed）——判定**必须动态**，不许只扫不跑。
  3. **失败二分类**：
     - `ImportError` / `ModuleNotFoundError` / `cannot import name` / 收集错 =
       **门禁红**（正是要堵的洞，无欠账通道）；
     - 断言 / 语义 / 环境类失败 = **合法 xfail**，但必须登记进 `_已知欠账`
       （`_已知欠账[节点ID] = (理由, issue, 到期日)`，**过期自动红**，R153 体例）。
  4. **静态吞点**：命令式 `pytest.xfail()` 若位于 `except (ImportError|ModuleNotFoundError|
     NameError|Exception)` 处理器内，属 `--runxfail` **无法透视**的吞并（except 先把异常
     接走，动态层只看到下游二次失败）——必须登记欠账，否则红。活样本：
     `tests/test_distributed_eval_light.py::_过A1缺口`（except NameError → xfail，
     吞掉「时间格式化 转译腿零映射」的 NameError）。
* **不做（明确边界）**：
  - 不跑顶层**非 xfail** 用例（「顶层全套真跑」耗时太长，属 E 线候选，任务书 §1.6）；
  - 不改 / 不删任何现有 xfail marker（只诊断 + 登记，修不修由业主裁）；
  - 不覆盖 `tests/unit/` 下的 xfail（常规回归的地盘；`test_原生腿_R13C_对拍扩展.py` 的
    2 处 strict=True marker 留待后续轮同机制扩展，本轮登记不扩 scope）。

与 R153 门禁的分工
------------------
R153 = 收集期（模块级 import 坏 → collect 红）；本门 = 执行期（函数内 import 坏被 xfail
吞 → --runxfail 真跑后红）。两道门互补，不互相替代；R153 必须保持绿（本门不改它）。

子进程跑法（含一条本机实测约束）
--------------------------------
子命令**继承 pyproject addopts**（`--timeout=60 -n 4 --dist=loadscope`），并显式追加
`--timeout=300`（后置覆盖 60，遵守 R152-C2「逐例提限、不动全局」纪律）。
⚠️ 为什么不清空 addopts 跑串行：本机 Windows 沙箱实测，python 父进程嵌套一个**串行**
pytest 子进程执行 tests/ 用例会触发进程树 SIGTERM（与用例轻重无关，探针 G 实证）；
继承 xdist（-n 4）后编译/执行落在 worker，父子树可正常存活。真实机（0.82/0.86）无此
限制；若某台机器嵌套 xdist 资源紧张，可用环境变量 `R157B_CHILD_WORKERS=<n>` 覆盖
子进程并发度（默认继承配置）。

欠账清单契约（业主裁定，R153 体例）
----------------------------------
`_已知欠账[节点ID] = (理由, issue, 到期日)`：缺字段 / 到期日非 ISO / 已过期 → 红。
到期逼人销账或重订期，**不许静默 skip**。

耗时
----
枚举 155 个顶层文件 AST ~2s；子进程 --runxfail 跑 21 个 xfail 节点本机实测 ~70s
（含 3 个原生腿真编译用例）。按 R152-C2 纪律逐例提限：本门禁主用例 `timeout(900)`。

反跑（有牙）
------------
1. `test_反跑_注入假import必须转红`：在 `tests/` 临时造一个 xfail(strict=False) +
   `from 不存在的模块 import x` 的探针 → 枚举必须抓到它 → 门禁必须转红且原因含
   ModuleNotFoundError → 删探针 → 枚举不再含它。
2. `test_分类器有牙` / `test_欠账机制有牙`：单元级反跑分类器与欠账校验。
"""
import ast
import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_测试根 = os.path.join(_REPO, 'tests')

# ── 已知欠账清单（R153 体例；每条 = (理由, issue/来源, 到期日 YYYY-MM-DD)）─────────
# 登记依据 = R157-B L0 本机 --runxfail 实测（2026-10-16）+ 0.86 Linux 复跑（见交付报告）。
# 全部为「断言/语义/环境类」合法 xfail；**import 类失败无欠账通道，直接红**。
_已知欠账 = {
    # ── phase4 / phase13：纯光明腿（.light）实现与 .py 契约的行为差异 ──
    # 背景：R152-C1 起 conftest 会话级安装光明导入钩子，Windows 也加载 .light 纯光明腿；
    # 原 marker 条件 `_原生腿环境分叉_XFAIL = platform.system() != "Windows"` 与现状脱节
    # （Windows 现在同样失败，只因顶层从不被执行而不可见）。修法（改实现/改测试/改条件）
    # 由业主裁，B 线只登记。
    'tests/test_stdlib_phase4.py::Test编码解码::test_Base64': (
        '纯光明腿无 bytes 类型：Base64二进制 回路返 str（本机实测 AssertionError: '
        "'hello' != b'hello'）；stdlib/编码解码.light 与 .py 契约差异",
        '_R157_并行任务书.md B 线 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase4.py::Test编码解码::test_二进制十六进制转换': (
        '二进制十六进制转换走 .light 腿，字节序列以串表示致 ord() 收到 int'
        '（本机实测 TypeError: ord() expected string of length 1, but int found）',
        '_R157_并行任务书.md B 线 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase4.py::Test编码解码::test_字符集转换': (
        '字符集转换 对 GBK 数据返 str 无 .decode（codecs 依赖按能力边界占位）'
        '（本机实测 AttributeError: str has no attribute decode）',
        '_R157_并行任务书.md B 线 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase4.py::Test编码解码::test_字节字符串转换': (
        '字节字符串转换返十六进制串而非 bytes 实例（本机实测 AssertionError: '
        "'68656c6c6f' is not an instance of bytes）",
        '_R157_并行任务书.md B 线 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase4.py::Test数据验证::test_验证IP地址': (
        '数据验证.light 验证IP地址 返否（本机实测 AssertionError: False is not true）',
        '_R157_并行任务书.md B 线 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase4.py::Test数据验证::test_验证JSON': (
        '数据验证.light 验证JSON 边界口径分歧返真（本机实测 AssertionError: True is not false）',
        '_R157_并行任务书.md B 线 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase13.py::测试高级文件模块::test_磁盘使用情况': (
        '高级文件.light 磁盘使用情况 返 0（本机实测 AssertionError: 0 not greater than 0）',
        '_R157_并行任务书.md B 线 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase13.py::测试高级文件模块::test_命令存在': (
        '高级文件.light 命令存在 判否（本机实测 AssertionError: False is not true）',
        '_R157_并行任务书.md B 线 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    # ── path_guard D9：Windows 特异性真失败（Linux 同节点通过）──
    'tests/test_path_guard_light.py::Test对抗用例_D9::test_链接指向沙箱外时经过链接的子路径也被拒_附变异反跑': (
        'Windows 特异性真失败（非 import 类），Linux 同节点反而通过 —— 跨平台分叉，疑真实缺陷候选。'
        '本机 Windows 实测 assert True is False：junction 指向外部时，穿过链接的子路径未被路径护栏拒绝'
        '（用例内命令式 xfail 因 symlink 可建而未触发，故落到真断言）。0.86 Linux 同节点 [通过]，'
        '说明断言逻辑本身正确、缺口仅在 Windows 的 junction 解析路径上。修复前维持登记，'
        '见交付报告「新发现」D9 跨平台分叉',
        '_R157_并行任务书.md B 线 / _R157_B线交付报告.md §4 新发现',
        '2026-11-30'),
    # ── 静态吞点：命令式 xfail 位于 except NameError 内，--runxfail 无法透视 ──
    'tests/test_distributed_eval_light.py::_过A1缺口': (
        '静态吞点：pytest.xfail() 位于 except NameError 处理器内（A1 缺口：节点网络.light '
        '调 时间格式化，转译腿零映射 → NameError 被吞成 xfail，下游只见 TypeError）。'
        '待 A1 在 src/code_generator.py 补映射后自动转绿；本键为静态登记，非节点 ID',
        '_R157_并行任务书.md B 线 / _R157_B线交付报告.md §3',
        '2026-11-30'),
}


# ─────────────────────────────────────────────────────────────────────────────
# 枚举层：AST 动态扫描顶层 tests/（无手抄清单，新增 xfail 自动入面）
# ─────────────────────────────────────────────────────────────────────────────

def _前缀(根=None):
    """节点 ID 前缀。

    - `根=None` → 主扫描区 `tests/`（生产口径）。
    - `根=<隔离目录>` → 该目录的 POSIX 路径（**反跑隔离口径**）。
      ⚠️ R157 收口修复：反跑探针若落在主扫描区 `tests/` 里，会与 R153 的
      collect 门禁**共享扫描区**，xdist 并发下把 R153 门禁带红。
      故反跑走隔离目录，前缀随之切换，节点 ID 仍可正常重建。
    """
    if 根 is None:
        return 'tests/'
    return 根.replace('\\', '/').rstrip('/') + '/'


def _顶层测试文件(根=None):
    """顶层 `test_*.py` 清单。

    ⚠️ R157 收口修复：`根` 是为**反跑探针**准备的**隔离出口**。
    反跑探针若直接落在 `_测试根`（= `tests/`）里，会与 R153 的 collect 门禁
    **共享扫描区**：xdist 并发下 R153 枚举到这个临时探针文件，探针里的
    假 import 使 collect 报 rc=2 ⇒ **R153 门禁被带红**（0.82 权威全量门实测捕获）。
    故反跑一律走 `tempfile.mkdtemp()` 隔离目录，不污染共享扫描区。
    """
    return sorted(f for f in os.listdir(根 or _测试根)
                  if f.startswith('test_') and f.endswith('.py'))


def _是测试函数名(名):
    return 名.startswith('test') or 名.startswith('测试')


def _except捕获名(处理器):
    """返回 except 子句捕获的异常名集合（Name/Tuple 形态；裸 except → BaseException）。"""
    if 处理器.type is None:
        return {'BaseException'}
    名们 = set()
    for n in ast.walk(处理器.type):
        if isinstance(n, ast.Name):
            名们.add(n.id)
        elif isinstance(n, ast.Attribute):
            名们.add(n.attr)
    return 名们 or {'BaseException'}


# 会吞掉 import 类错误的 except 捕获集（命中即「静态吞点」，必须登记欠账）
_吞并类异常名 = {'ImportError', 'ModuleNotFoundError', 'NameError',
                'Exception', 'BaseException'}


def _枚举xfail(根=None):
    """动态枚举 `tests/` 顶层全部 xfail 构造（根可被反跑隔离覆盖）。

    返回 dict：
      声明式节点  : {节点ID: 行号}          —— 带 @pytest.mark.xfail 装饰的用例
      命令式节点  : {节点ID: [行号]}        —— 含命令式 pytest.xfail() 的用例
                    （辅助函数里的调用解析到同文件测试调用方）
      吞点        : [(文件, 行号, 外围函数, except类型)]  —— 位于吞并类 except 内的调用
      无法解析    : [描述]                  —— 辅助函数内调用但找不到测试调用方
    """
    声明式节点 = {}
    命令式节点 = {}
    吞点 = []
    无法解析 = []

    for 文件名 in _顶层测试文件(根):
        路径 = os.path.join(根 or _测试根, 文件名)
        try:
            with open(路径, encoding='utf-8') as f:
                树 = ast.parse(f.read())
        except (SyntaxError, UnicodeDecodeError) as e:
            无法解析.append('%s 解析失败：%s' % (文件名, e))
            continue

        父映射 = {}
        for n in ast.walk(树):
            for c in ast.iter_child_nodes(n):
                父映射[c] = n
        装饰器节点 = set()
        for n in ast.walk(树):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for d in n.decorator_list:
                    装饰器节点.add(id(d))

        def 走类体(节点, 类名=None):
            for item in 节点.body:
                if isinstance(item, ast.ClassDef):
                    走类体(item, item.name)
                elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    有xfail = any(
                        isinstance(d, ast.Call) and 'xfail' in ast.unparse(d)
                        for d in item.decorator_list)
                    if 有xfail:
                        节点ID = _前缀(根) + '%s::%s%s' % (
                            文件名, 类名 + '::' if 类名 else '', item.name)
                        声明式节点[节点ID] = item.lineno

        走类体(树)

        # 命令式 pytest.xfail() 调用（排除装饰器位置的同名 Call）
        for n in ast.walk(树):
            if not (isinstance(n, ast.Call) and id(n) not in 装饰器节点
                    and isinstance(n.func, ast.Attribute) and n.func.attr == 'xfail'):
                continue
            p = 父映射.get(n)
            类名 = None
            函数 = None
            except名 = set()
            while p is not None:
                if isinstance(p, ast.ClassDef) and 类名 is None:
                    类名 = p.name
                if isinstance(p, ast.ExceptHandler) and not except名:
                    except名 = _except捕获名(p)
                if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)) and 函数 is None:
                    函数 = p
                p = 父映射.get(p)
            if 函数 is None:
                无法解析.append('%s:%d 命令式 xfail 不在任何函数内' % (文件名, n.lineno))
                continue
            位置 = '%s:%d' % (文件名, n.lineno)
            if except名 & _吞并类异常名:
                吞点.append((位置, 函数.name, sorted(except名 & _吞并类异常名)))
            if _是测试函数名(函数.name):
                节点ID = _前缀(根) + '%s::%s%s' % (
                    文件名, 类名 + '::' if 类名 else '', 函数.name)
                命令式节点.setdefault(节点ID, []).append(n.lineno)
            else:
                # 辅助函数：找同文件里直接引用它的测试函数
                调用方 = [
                    f for f in 树.body
                    if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and _是测试函数名(f.name)
                    and any(isinstance(x, ast.Name) and x.id == 函数.name
                            for x in ast.walk(f))]
                if not 调用方:
                    无法解析.append(
                        '%s 命令式 xfail 位于辅助函数 %s 内，但同文件找不到测试调用方'
                        % (位置, 函数.name))
                for f in 调用方:
                    节点ID = _前缀(根) + '%s::%s' % (文件名, f.name)
                    命令式节点.setdefault(节点ID, []).append(n.lineno)

    return {'声明式节点': 声明式节点, '命令式节点': 命令式节点,
            '吞点': 吞点, '无法解析': 无法解析}


def _全部待跑节点(根=None):
    枚举 = _枚举xfail(根)
    return set(枚举['声明式节点']) | set(枚举['命令式节点']), 枚举


# ─────────────────────────────────────────────────────────────────────────────
# 判定层：--runxfail 真跑 + junit 解析 + 失败二分类 + 欠账校验
# ─────────────────────────────────────────────────────────────────────────────

# import 类失败特征（命中 = 门禁红，无欠账通道）
_IMPORT类特征 = ('ImportError', 'ModuleNotFoundError', 'No module named',
                'cannot import name', 'error during collection',
                'ERROR collecting', 'ImportError during collection')


def _是import类失败(消息):
    文本 = 消息 or ''
    return any(特征 in 文本 for 特征 in _IMPORT类特征)


def _检查欠账条目(条目):
    """返回 None 表示合规；否则返回不合规原因（R153 契约，供断言 + 反跑）。"""
    if not (isinstance(条目, tuple) and len(条目) == 3):
        return '欠账条目必须是 (理由, issue, 到期) 三元组'
    理由, issue, 到期 = 条目
    if not (理由 or '').strip():
        return '欠账缺「理由」——不许静默 skip'
    if not (issue or '').strip():
        return '欠账缺「issue/来源」——不许无出处 skip'
    try:
        到期日 = datetime.date.fromisoformat(到期)
    except (TypeError, ValueError):
        return '欠账到期日不是 ISO 日期（YYYY-MM-DD）：%r' % (到期,)
    if 到期日 < datetime.date.today():
        return '欠账已于 %s 到期，必须销账或重订期（理由：%s）' % (到期, 理由)
    return None


def _模块名到文件(根=None):
    """'tests.test_stdlib_phase4' → 'tests/test_stdlib_phase4.py'（junit 重建节点 ID 用）。

    ⚠️ R157 收口修复：同时登记「裸模块名」与「tests. 前缀」两种键。
    junit 的 classname 形态随 pytest/xdist 版本与调用路径而变
    （主扫描区为 `tests.<模块>`；隔离目录多为裸 `<模块>`），
    双键登记可保证两种口径下节点 ID 都能重建。
    """
    表 = {}
    前 = _前缀(根)
    for f in _顶层测试文件(根):
        表['tests.' + f[:-3]] = 前 + f
        表.setdefault(f[:-3], 前 + f)
    return 表


def _从junit重建节点ID(用例, 模块表, 前=None):
    """xdist 下 junit 无 file 属性，用 classname（tests.<模块>[.类]）+ name 重建。

    `前` 为节点 ID 前缀（反跑隔离时指向临时目录；默认 `tests/`）。
    """
    类名 = 用例.attrib.get('classname') or ''
    名 = 用例.attrib.get('name') or ''
    文件 = 用例.attrib.get('file')
    if 文件:
        基 = (前 or 'tests/') + os.path.basename(文件)
        模块 = 'tests.' + os.path.basename(文件)[:-3]
    else:
        模块 = None
        for m in 模块表:
            if 类名 == m or 类名.startswith(m + '.'):
                模块 = m
                break
        if 模块 is None:
            return None
        基 = 模块表[模块]
    余 = 类名[len(模块):].lstrip('.')
    部分 = [余] if 余 else []
    部分.append(名)
    return 基 + '::' + '::'.join(部分)


def _跑门禁(仅这些节点=None, 超时=900, 根=None):
    """门禁核心：枚举 → --runxfail 真跑 → 二分类 → 欠账校验。红则 raise。

    `根` 用于反跑隔离：把探针写进独立临时目录，避免落在 `_测试根` 里
    与 R153 collect 门禁争用同一扫描区（R157 收口修复）。
    """
    节点们, 枚举 = _全部待跑节点(根)
    if 仅这些节点 is not None:
        节点们 = set(仅这些节点)
    assert 节点们, '没枚举到任何 xfail 节点——枚举逻辑坏了（或顶层已无 xfail，请复核）'

    # 环境变量逃生口：覆盖子进程并发度（默认继承 pyproject addopts 的 -n 4）
    子环境 = dict(os.environ)
    worker覆盖 = 子环境.get('R157B_CHILD_WORKERS')

    临时目录 = tempfile.mkdtemp(prefix='r157b_xfail门禁_')
    junit路径 = os.path.join(临时目录, 'junit.xml')
    命令 = [sys.executable, '-m', 'pytest', '--runxfail', '-q',
            '-p', 'no:cacheprovider', '--timeout=300',
            '--junitxml', junit路径] + sorted(节点们)
    if worker覆盖:
        命令 += ['-n', worker覆盖]
    try:
        r = subprocess.run(命令, cwd=_REPO, capture_output=True, timeout=超时)
    except subprocess.TimeoutExpired:
        raise AssertionError(
            'xfail 门禁子进程超时（>%ds）——native 编译用例在负载下过慢？'
            '按 R152-C2 纪律逐例提限，不许动全局。' % 超时)
    输出 = ((r.stdout or b'') + b'\n' + (r.stderr or b'')).decode('utf-8', 'replace')

    if r.returncode not in (0, 1):
        raise AssertionError(
            'xfail 门禁子进程异常退出 rc=%d（非 0/1）——基础设施错误，按红处理：\n%s'
            % (r.returncode, 输出[-2000:]))
    if not os.path.exists(junit路径):
        raise AssertionError('xfail 门禁子进程未生成 junit——按红处理：\n%s' % 输出[-2000:])

    # junit → 每节点结论
    模块表 = _模块名到文件(根)
    前 = _前缀(根)
    结论 = {}
    for 套件 in ET.parse(junit路径).getroot().iter('testsuite'):
        for 用例 in 套件.iter('testcase'):
            节点ID = _从junit重建节点ID(用例, 模块表, 前)
            if 节点ID is None:
                continue
            失败 = [c for c in 用例 if c.tag in ('failure', 'error')]
            跳过 = [c for c in 用例 if c.tag == 'skipped']
            if 失败:
                消息 = (失败[0].attrib.get('message')
                        or (失败[0].text or '')) [:300]
                结论[节点ID] = ('失败', 消息)
            elif 跳过:
                结论[节点ID] = ('跳过', (跳过[0].attrib.get('message') or '')[:200])
            else:
                结论[节点ID] = ('通过', '')

    # 收集错（模块级 import 坏在本层再次显形）
    收集错文件 = set(re.findall(r'ERROR (?:collecting )?(tests[/\\][^\s:]+\.py)', 输出))

    # 请求了但 junit 里没有的节点 = 异常（保守按红）
    缺失 = sorted(节点们 - set(结论))

    # ── 判定 ──
    import类红 = []
    未登记合法失败 = []
    跳过们 = []
    for 节点ID, (状态, 消息) in sorted(结论.items()):
        if 状态 == '失败':
            所属文件 = 节点ID.split('::')[0].replace('\\', '/')
            if _是import类失败(消息) or 所属文件 in 收集错文件:
                import类红.append((节点ID, 消息))
            elif 节点ID not in _已知欠账:
                未登记合法失败.append((节点ID, 消息))
        elif 状态 == '跳过':
            跳过们.append(节点ID)

    # 静态吞点必须登记（--runxfail 无法透视的那一档）
    未登记吞点 = []
    for 位置, 函数名, 异常名们 in 枚举['吞点']:
        键 = 'tests/%s::%s' % (位置.split(':')[0], 函数名)
        if 键 not in _已知欠账:
            未登记吞点.append((位置, 函数名, 异常名们))

    # 欠账条目合规性（过期/缺字段 → 红，R153 契约）
    欠账问题 = {k: _检查欠账条目(v) for k, v in _已知欠账.items()
                if _检查欠账条目(v)}
    # 反向：登记了但枚举里已不存在的节点（销账未清清单）——提示不拦
    僵尸欠账 = sorted(set(_已知欠账) - 节点们
                     - {'tests/test_distributed_eval_light.py::_过A1缺口'})

    if 枚举['无法解析']:
        raise AssertionError(
            'xfail 枚举有无法解析的调用点（门禁不许静默漏采）：\n  %s'
            % '\n  '.join(枚举['无法解析']))
    if 缺失:
        raise AssertionError(
            '以下 xfail 节点请求执行但 junit 无结论（疑似收集失败/节点 ID 漂移）：\n  %s\n%s'
            % ('\n  '.join(缺失), 输出[-1500:]))
    if import类红:
        raise AssertionError(
            '🚨 xfail 吞 ImportError 实锤（本门禁要堵的洞，无欠账通道）：\n%s\n'
            '——修 import，或摘掉相关 xfail marker；不许把 import 类失败登记成欠账。\n%s'
            % ('\n'.join('  %s\n    %s' % (n, m) for n, m in import类红),
               输出[-1500:]))
    if 未登记合法失败:
        raise AssertionError(
            '以下 xfail 用例真跑失败（非 import 类 = 合法 xfail），但未登记欠账：\n%s\n'
            '——按 _已知欠账[节点ID] = (理由, issue, 到期日) 登记（过期自动红），'
            '或修好后摘掉 marker。\n%s'
            % ('\n'.join('  %s\n    %s' % (n, m) for n, m in 未登记合法失败),
               输出[-1500:]))
    if 未登记吞点:
        raise AssertionError(
            '发现「命令式 xfail 位于 except 吞并类处理器」的静态吞点（--runxfail 无法透视）：\n%s\n'
            '——按 _已知欠账 登记（理由 + issue + 到期），或改为不吞 import 类的写法。\n%s'
            % ('\n'.join('  %s（函数 %s，捕获 %s）' % t for t in 未登记吞点),
               输出[-1500:]))
    if 欠账问题:
        raise AssertionError('欠账清单有条目不合规：\n%s' % 欠账问题)

    return {'枚举节点数': len(节点们), '执行节点数': len(结论), '逐节点': 结论,
            '通过': sum(1 for v in 结论.values() if v[0] == '通过'),
            '跳过': 跳过们, 'import类红': import类红,
            '未登记合法失败': 未登记合法失败, '僵尸欠账提示': 僵尸欠账,
            '声明式': len(枚举['声明式节点']), '命令式': len(枚举['命令式节点']),
            '吞点': 枚举['吞点']}


# ─────────────────────────────────────────────────────────────────────────────
# 门禁用例
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.timeout(900)
def test_顶层xfail用例不得因ImportError而xfail():
    """动态枚举顶层全部 xfail 用例，--runxfail 真跑；import 类失败红，合法失败须登记。"""
    报告 = _跑门禁()
    # 摘要 + 逐节点结论进 stdout，便于 0.82/0.86 跑批时肉眼核对（审计友好）
    print('R157B摘要：枚举 xfail 节点 %d（声明式 %d + 命令式 %d），真跑 %d，通过 %d，跳过 %s'
          % (报告['枚举节点数'], 报告['声明式'], 报告['命令式'],
             报告['执行节点数'], 报告['通过'], 报告['跳过'] or '无'))
    for 节点ID, (状态, 消息) in sorted(报告['逐节点'].items()):
        print('R157B逐节点 [%s] %s%s' % (状态, 节点ID,
                                          ' —— %s' % 消息[:120] if 消息 else ''))
    if 报告['僵尸欠账提示']:
        print('提示（不拦）：欠账清单中已不存在于枚举的键：%s' % 报告['僵尸欠账提示'])


def test_枚举覆盖顶层全部xfail构造():
    """枚举必须自洽：非空、节点 ID 形态合法、文件真实存在、活吞点被抓到。"""
    节点们, 枚举 = _全部待跑节点()
    assert 节点们, '没枚举到任何 xfail 节点'
    assert len(枚举['声明式节点']) >= 1, '声明式 xfail 枚举为空'
    assert len(枚举['命令式节点']) >= 1, '命令式 xfail 枚举为空'
    for 节点ID in 节点们:
        文件 = 节点ID.split('::')[0]
        assert 文件.startswith('tests/') and 文件.endswith('.py'), 节点ID
        assert os.path.exists(os.path.join(_REPO, 文件)), '节点 ID 指向不存在的文件：%s' % 节点ID
    # 活样本：_过A1缺口 必须被判为静态吞点（except NameError）
    吞点描述 = ['tests/%s::%s' % (位置.split(':')[0], 函数名)
                for 位置, 函数名, _ in 枚举['吞点']]
    assert 'tests/test_distributed_eval_light.py::_过A1缺口' in 吞点描述, \
        '活吞点 _过A1缺口 没被抓到——吞点检测坏了：%s' % 吞点描述


def test_欠账清单条目字段完整():
    for 路径, 条目 in _已知欠账.items():
        assert isinstance(条目, tuple) and len(条目) == 3, \
            '%s 欠账条目必须是 (理由, issue, 到期) 三元组' % 路径
        assert _检查欠账条目(条目) is None, '%s 欠账登记不合规：%s' % (路径, _检查欠账条目(条目))


def test_欠账清单不过期():
    过期 = {p: _检查欠账条目(e) for p, e in _已知欠账.items() if _检查欠账条目(e)}
    assert not 过期, '以下欠账已过期，必须销账或重订期：%s' % 过期


def test_欠账机制有牙():
    """反跑：四种坏登记都必须被判不合规（清单不是摆设）。"""
    # 过期 → 必须红
    assert _检查欠账条目(('理由', 'ISSUE-1', '2020-01-01')) is not None
    # 缺理由 / 缺 issue → 必须红（不许静默 skip）
    assert _检查欠账条目(('', 'ISSUE-1', '2999-01-01')) is not None
    assert _检查欠账条目(('理由', '', '2999-01-01')) is not None
    # 到期日非 ISO → 必须红
    assert _检查欠账条目(('理由', 'ISSUE-1', '2026/11/30')) is not None
    # 合规 → 放行
    assert _检查欠账条目(('理由', 'ISSUE-1', '2999-01-01')) is None


def test_分类器有牙():
    """反跑：import 类特征必须判 import 类；断言/语义类必须放过（进欠账通道）。"""
    # import 类 → 红
    for 消息 in ("ModuleNotFoundError: No module named '不存在的模块'",
                "ImportError: cannot import name '字符集转换为字符串'",
                "error during collection of tests/test_x.py",
                "ImportError during collection"):
        assert _是import类失败(消息), '漏判 import 类：%s' % 消息
    # 断言/语义/环境类 → 放过
    for 消息 in ("AssertionError: 'hello' != b'hello'",
                "TypeError: ord() expected string of length 1, but int found",
                "AttributeError: 'str' object has no attribute 'decode'",
                "TimeoutError: 子进程超时"):
        assert not _是import类失败(消息), '误判 import 类：%s' % 消息


def test_反跑_注入假import必须转红():
    """端到端反跑：临时注入 xfail(strict=False) + 假 import → 门禁必须转红；删除 → 枚举干净。

    ⚠️ R157 收口修复（并发隔离）：探针**不再**落在 `tests/` 主扫描区。
    原写法与本仓 R153 的 collect 门禁共享扫描区，xdist `-n auto` 并发下
    R153 门禁枚举到这个临时探针文件，探针里的假 import 让 collect 报 rc=2
    ⇒ **R153 门禁被带红**（0.82 权威全量门实测捕获）。
    现改为「独立临时目录 + 枚举根注入」：既保留「枚举必须抓到新 xfail」的
    有牙断言，又不与 R153 争用扫描区。
    """
    探针文件 = 'test_R157B_反跑探针_自动清理.py'
    隔离根 = tempfile.mkdtemp(prefix='r157b_反跑隔离_')
    探针路径 = os.path.join(隔离根, 探针文件)
    前 = _前缀(隔离根)
    探针节点 = 前 + '%s::test_假import被xfail吞并探针' % 探针文件
    内容 = (
        '# -*- coding: utf-8 -*-\n'
        '"""R157-B 反跑探针（临时存在数秒，finally 强制删除）。\n'
        '模拟 R153 文档登记的死洞：函数内 ImportError 被 xfail(strict=False) 吞掉。\n'
        '"""\n'
        'import pytest\n'
        '\n'
        '\n'
        '@pytest.mark.xfail(reason="反跑探针：假 import 必须被门禁抓住", strict=False)\n'
        'def test_假import被xfail吞并探针():\n'
        '    from 不存在的模块 import 不该存在的名字\n'
        '    assert 不该存在的名字\n'
    )
    try:
        with open(探针路径, 'w', encoding='utf-8', newline='\n') as f:
            f.write(内容)
        节点们, _ = _全部待跑节点(隔离根)
        assert 探针节点 in 节点们, \
            '枚举没抓到临时探针——动态枚举失效（新 xfail 不会自动入面）'
        with pytest.raises(AssertionError) as 异常:
            _跑门禁(仅这些节点={探针节点}, 根=隔离根)
        消息 = str(异常.value)
        assert _是import类失败(消息), \
            '门禁转红的原因不是 import 类——分类器或判定链坏了：\n%s' % 消息[:1500]
        assert 探针节点 in 消息, '转红信息没定位到探针节点：\n%s' % 消息[:1500]
    finally:
        if os.path.exists(探针路径):
            os.remove(探针路径)
        shutil.rmtree(隔离根, ignore_errors=True)
    节点们2, _ = _全部待跑节点()
    assert 探针节点 not in 节点们2, '探针删除后枚举仍包含它——清理不彻底'


def test_门禁不碰共享文件():
    """自律断言：本门禁只读 tests/ 顶层（诊断），不写任何被测文件。"""
    # 本文件自身在 tests/unit，不在顶层扫描面；R153 门禁保持独立
    assert os.path.basename(__file__) not in _顶层测试文件()
    assert 'test_R153_顶层collect门禁.py' in _顶层测试文件()
