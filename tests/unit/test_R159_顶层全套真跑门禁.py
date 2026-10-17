# -*- coding: utf-8 -*-
"""R159-E · E-4（R157-E4）：顶层 `tests/` 全套真跑门禁（新门 + 首跑基线）。

为什么要有这道门
----------------
`tests/` 顶层长期只被**收集**、不被**执行**：

* R153 门禁（`tests/test_R153_顶层collect门禁.py`）= `--collect-only`，
  只挡**模块级** ImportError（rc≠0 即红），**不执行用例**；
* R157-B 门禁（`tests/unit/test_R157_顶层xfail门禁.py`）= 对 xfail 节点跑
  `--runxfail` 真跑并二分类，其文档字符串明文写着：
  「不跑顶层**非 xfail** 用例（『顶层全套真跑』耗时太长，属 E 线候选）」；
* 其余顶层文件**没有任何常规执行门禁**——断言腐化、行为回归、平台分叉
  只能等全量门（~21min/次）才撞见，或者永远撞不见。

**本文件就是那一档**（R159 任务书 E 线 = `docs/语言升级方向.md` §2 R157-E4）。

本门做什么 / 不做什么
----------------------
* **做**：
  1. **动态枚举** `tests/` 顶层全部 `test_*.py`（glob，**无手抄清单**，
     新增文件自动入面）。起草时实测 **156** 个——`docs/语言升级方向.md`
     记的 171 与任何现行口径都对不上（顶层 156 / 含 unit+e2e 354 /
     排除 archive 346），疑为旧计数，**以动态枚举为准**，差异进交付报告。
  2. **真跑**：子进程 `pytest --runxfail`（xfail 标记全部失效、按普通用例
     真跑，判定必须动态，不许只扫不跑）。两种模式：
     - `full`（`R159E_FULL=1` 显式开启）：156 文件全量，首跑武装用；
     - `incremental`（**日常默认**）：只跑「基线中红文件 + 基线后新增文件」。
  3. **失败三分类**：
     - **import 类**（缺的是仓库内模块 / cannot import name / 收集错且缺的
       是仓库内模块）= **门禁红**——正是本门要堵的洞，无常规欠账通道；
     - **环境类**（缺的全是第三方依赖，如某台机没装 aiohttp）= 合法存量
       欠账，登记 `_已知欠账`（理由 + issue + 到期日，过期自动红）；
     - **语义类**（断言 / 行为 / 平台分叉）= 合法存量欠账，同通道登记。
  4. **基线**：full 模式产出 `_r159_scratch/e_顶层全套基线.json`（gitignored），
     记录逐节点结论 + 文件清单快照；**同时是 D 线（E-3 容器布尔 repr）断言
     扫描的对照表**（R159 任务书 §1.5：D 修后复跑本门，new_reds=0 即没扫漏）。
* **不做（明确边界）**：
  - 不进 CI 主链（E-4 原文口径：耗时 ~9-40min/轮，只做增量/失败重跑）；
  - 不改 / 不删任何现有 xfail marker 或 skip（只诊断 + 登记，修不修由业主裁）；
  - 不覆盖 `tests/unit/`（常规回归的地盘；本文件自身在 `tests/unit/`）；
  - 不重复 R157-B 的静态吞点层（见下「已知局限」）。

`--runxfail` 实测语义（2026-10-17 本机探针，写码前实证）
------------------------------------------------------
* marker-xfail 用例**真跑**：失败如实落 junit `<failure>`（R157-B 同款）；
* 命令式 `pytest.xfail()` 在 `--runxfail` 下呈现为**通过**（junit 无
  skipped 子元素、终端计 passed）——**已知局限**：非 except 型的命令式
  xfail 会让用例「看起来绿」。该洞与 R157-B 静态吞点层同族（R157-B 已覆盖
  except 吞并型），本门不重复建设，交付报告已立 L-219 登记。

子进程跑法（Windows 嵌套约束，R157-B 实证沿用）
----------------------------------------------
子命令**继承 pyproject addopts** 并显式追加 `--timeout=300`（后置覆盖全局
60，遵守 R152-C2「逐例提限、不动全局」）与 `--continue-on-collection-errors`
（pytest 默认遇收集错会**中断整场**——本门要的是「一个坏文件不妨碍其余
155 个文件的真跑结论」，2026-10-17 探针实证 rc=2 + Interrupted）。
⚠️ 本机 Windows 沙箱：父进程嵌套**串行** pytest 子进程会触发进程树 SIGTERM
（R157-B 探针 G 实证）⇒ 子进程必须走 xdist。默认 `-n 1`（R157-B 收口修复：
父层 `-n auto` 时避免嵌套并发把原生腿真编译用例撞出假超时）；可用
`R159E_CHILD_WORKERS=<n>` 覆盖并发度。

武装流程 / 日常模式
------------------
1. **武装（首跑基线）**：`R159E_FULL=1 R159E_CHILD_WORKERS=4 pytest
   tests/unit/test_R159_顶层全套真跑门禁.py`（本机 ~20-40min；0.86 同款
   `R159E_CHILD_WORKERS=3`）→ 产出基线 + 存量失败清单 → 逐条登记
   `_已知欠账` 后复跑转绿。full 模式**无论红绿都先落基线**（红态基线
   正是欠账登记的输入，也是 D 线的修前对照表）。
2. **日常（增量）**：默认即增量——只跑「基线中红文件 + 基线后新增文件」。
   **局限（诚实声明）**：基线中绿的文件不被复跑，其中的新断言回归抓不到；
   定期 `R159E_FULL=1` 重新武装是唯一补法（E-4「只做增量/失败重跑」
   口径的固有代价）。
3. **无基线且未声明 full** → 主用例 **skip 并打印武装指引**（不静默通过：
   pytest 显式报 SKIPPED。0.82/CI 上 `_r159_scratch/` 不同步，门禁自动
   退化为「静态层 + 跳过真跑」，不拖慢全量门；需要时把 `_r159_scratch/`
   一并同步或以 `R159E_BASELINE=<路径>` 指过去即可武装）。

欠账清单契约（R153 体例，业主裁定）
----------------------------------
`_已知欠账[键] = (理由, issue, 到期日)`：键 = 节点 ID（`tests/x.py::...`）
或文件键（`tests/x.py`，收集期环境类失败用）；缺字段 / 到期日非 ISO /
已过期 → 红。到期逼人销账或重订期，**不许静默 skip**。

`_存量import欠账`（窄口径例外通道）
---------------------------------
首跑武装时若发现**仓库内** import 类存量红（顶层从不被执行留下的真洞），
按本通道**逐条**登记（理由 + issue + 到期日），每次运行都大声打印；
**新增**的仓库内 import 类失败（不在本清单）一律红，不进任何通道。

耗时
----
full：156 文件本机 ~20-40min（`-n 4` 子进程）、0.86 ~9min（`-n 3`）；
incremental：只跑红/新文件（基线红文件量级 ~3-6min）。

反跑（有牙）
------------
1. `test_反跑_注入假import必须转红`：在 `_r159_scratch/e_反跑隔离/`
   （**不落 `tests/` 主扫描区**——R157-B 收口修复的教训：探针若进
   `tests/`，会与 R153 collect 门禁争用扫描区，并发下把 R153 带红）
   造一个 `from 节点网络 import 不存在的导出名字` 的探针 → 节点重建
   必须抓到它 → 门禁必须转红且原因含 import 类特征 → 删探针。
2. `test_分类器有牙` / `test_仓库内模块判定有牙`：三分类与仓库内判定有牙。
3. `test_欠账机制有牙` / `test_存量import欠账机制有牙`：坏登记必须不合规。
4. `test_增量文件集有牙`：基线与新增文件的选择逻辑有牙。
"""
import datetime
import glob
import json
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
_基线目录 = os.path.join(_REPO, '_r159_scratch')
_基线文件名 = 'e_顶层全套基线.json'

# ── 已知欠账清单（R153 体例；每条 = (理由, issue/来源, 到期日 YYYY-MM-DD)）─────────
# 种子 = R157-B 门禁 _已知欠账（2026-10-16 登记，2026-11-30 到期）原样承接：
# 这些节点在 --runxfail 真跑下同样失败，属「合法存量欠账」，理由不改写。
# R159-E 首跑 full 新增登记见下一节（依据 _R159_E线交付报告.md，2026-10-17）。
# 全部为「断言/语义/环境类」合法失败；**import 类失败无常规欠账通道，直接红**。
_已知欠账 = {
    # ── phase4 / phase13：纯光明腿（.light）实现与 .py 契约的行为差异 ──
    'tests/test_stdlib_phase4.py::Test编码解码::test_Base64': (
        '纯光明腿无 bytes 类型：Base64二进制 回路返 str（本机实测 AssertionError: '
        "'hello' != b'hello'）；stdlib/编码解码.light 与 .py 契约差异",
        'R157-B _已知欠账 承接 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase4.py::Test编码解码::test_二进制十六进制转换': (
        '二进制十六进制转换走 .light 腿，字节序列以串表示致 ord() 收到 int'
        '（本机实测 TypeError: ord() expected string of length 1, but int found）',
        'R157-B _已知欠账 承接 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase4.py::Test编码解码::test_字符集转换': (
        '字符集转换 对 GBK 数据返 str 无 .decode（codecs 依赖按能力边界占位）'
        '（本机实测 AttributeError: str has no attribute decode）',
        'R157-B _已知欠账 承接 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase4.py::Test编码解码::test_字节字符串转换': (
        '字节字符串转换返十六进制串而非 bytes 实例（本机实测 AssertionError: '
        "'68656c6c6f' is not an instance of bytes）",
        'R157-B _已知欠账 承接 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase4.py::Test数据验证::test_验证IP地址': (
        '数据验证.light 验证IP地址 返否（本机实测 AssertionError: False is not true）',
        'R157-B _已知欠账 承接 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase4.py::Test数据验证::test_验证JSON': (
        '数据验证.light 验证JSON 边界口径分歧返真（本机实测 AssertionError: True is not false）',
        'R157-B _已知欠账 承接 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase13.py::测试高级文件模块::test_磁盘使用情况': (
        '高级文件.light 磁盘使用情况 返 0（本机实测 AssertionError: 0 not greater than 0）',
        'R157-B _已知欠账 承接 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    'tests/test_stdlib_phase13.py::测试高级文件模块::test_命令存在': (
        '高级文件.light 命令存在 判否（本机实测 AssertionError: False is not true）',
        'R157-B _已知欠账 承接 / _R157_B线交付报告.md §3',
        '2026-11-30'),
    # ── path_guard D9：Windows 特异性真失败（Linux 同节点通过）──
    'tests/test_path_guard_light.py::Test对抗用例_D9::test_链接指向沙箱外时经过链接的子路径也被拒_附变异反跑': (
        'Windows 特异性真失败（非 import 类），Linux 同节点反而通过 —— 跨平台分叉，疑真实缺陷候选。'
        '本机 Windows 实测 assert True is False：junction 指向外部时，穿过链接的子路径未被路径护栏拒绝'
        '（用例内命令式 xfail 因 symlink 可建而未触发，故落到真断言）。0.86 Linux 同节点 [通过]，'
        '说明断言逻辑本身正确、缺口仅在 Windows 的 junction 解析路径上。修复前维持登记，'
        '见交付报告「新发现」D9 跨平台分叉',
        'R157-B _已知欠账 承接 / _R157_B线交付报告.md §4 新发现',
        '2026-11-30'),
}

# ── R159-E 首跑 full 增量登记（2026-10-17 L0 本机 full 首跑实测；0.86 复跑核对）──
# （首跑后按 _R159_E线交付报告.md 清单逐条填写；import 类不得进本通道）
_已知欠账.update({
    # ── R159-E 首跑 full 新发现（2026-10-17 L0 本机；单跑确定性复现 12.29s）──
    'tests/test_http_client.py::test_connection_error': (
        'Windows 平台网络栈差异（行为类，非 import）：HTTP获取 http://127.0.0.1:1/ '
        '期望抛 连接错误，但本机对该端口不回即时 RST 而是挂起，1s 超时抛 超时错误'
        '（两者是 HTTP错误 的兄弟子类，except 连接错误 捕不到）。本机单跑确定性复现；'
        'Linux 0.86 预期立即 RST → 连接错误 → 通过（0.86 平台批核对）。'
        '修法（测试放宽判定 / 实现把超时归并）由业主裁，E 线只登记',
        '_R159_并行任务书.md E 线 / _R159_E线交付报告.md §3 首跑新发现',
        '2026-11-30'),
})

# ── 存量 import 欠账（窄口径例外通道）────────────────────────────────────────
# 首跑武装时若发现**仓库内** import 类存量红（顶层从不被执行留下的真洞），
# 在此**逐条**登记（理由 + issue + 到期日），每次运行大声打印；**新增**的
# 仓库内 import 类失败（不在本清单）一律红。当前为空（首跑待填）。
_存量import欠账 = {}


# ─────────────────────────────────────────────────────────────────────────────
# 枚举层：动态扫描 tests/ 顶层（无手抄清单）
# ─────────────────────────────────────────────────────────────────────────────

def _顶层测试文件():
    """顶层 `tests/test_*.py` 文件名清单（只扫一层，不递归 unit/e2e）。"""
    return sorted(os.path.basename(p) for p in
                  glob.glob(os.path.join(_测试根, 'test_*.py'))
                  if os.path.isfile(p))


def _枚举():
    return _顶层测试文件()


def _全量路径们():
    return [os.path.join('tests', f) for f in _枚举()]


# ─────────────────────────────────────────────────────────────────────────────
# 判定层：三分类 + 欠账校验 + junit 节点重建
# ─────────────────────────────────────────────────────────────────────────────

# import 类失败特征（命中才进入「缺模块」分析；纯 Assertion 等不进来）
_IMPORT类特征 = ('ImportError', 'ModuleNotFoundError', 'No module named',
                'cannot import name', 'error during collection',
                'ERROR collecting', 'ImportError during collection')

# 仓库内模块解析的候选根（相对 _REPO）
_仓库内候选根 = ('', 'src', 'tests', 'stdlib')


def _是import类失败(消息):
    文本 = 消息 or ''
    return any(特征 in 文本 for 特征 in _IMPORT类特征)


def _缺的模块名们(文本):
    """从失败文本提取缺失的模块名（两种 pytest 口径）。"""
    文本 = 文本 or ''
    名们 = re.findall(r"No module named '([^']+)'", 文本)
    名们 += re.findall(r"cannot import name '[^']*' from '([^']+)'", 文本)
    return 名们


def _是仓库内模块(名):
    """模块名是否指向本仓代码（src/ stdlib/ tests/ 或顶层同名模块）。

    判「环境类」用：缺的全是第三方包 → 环境欠账通道；缺仓库内模块 →
    import 类红（正是本门要堵的洞：顶层从不被执行，仓库内 import 坏了也没人知道）。
    """
    if not 名:
        return False
    部分们 = [p for p in 名.split('.') if p]
    if not 部分们:
        return False
    for 根 in _仓库内候选根:
        基 = os.path.join(_REPO, 根) if 根 else _REPO
        for 后缀 in ('.py', '.light', os.sep + '__init__.py'):
            if os.path.isfile(os.path.join(基, *部分们) + 后缀):
                return True
    # stdlib 子目录（stdlib/分布式/节点网络.light 这类中文子目录）
    stdlib目录 = os.path.join(_REPO, 'stdlib')
    if os.path.isdir(stdlib目录):
        for 子 in os.listdir(stdlib目录):
            基 = os.path.join(stdlib目录, 子)
            if not os.path.isdir(基):
                continue
            for 后缀 in ('.py', '.light'):
                if os.path.isfile(os.path.join(基, *部分们) + 后缀):
                    return True
    return False


def _失败分类(消息):
    """失败消息三分类：'import类' / '环境类' / '语义类'。"""
    文本 = 消息 or ''
    if not _是import类失败(文本):
        return '语义类'
    缺们 = _缺的模块名们(文本)
    if 缺们 and all(not _是仓库内模块(m) for m in 缺们):
        return '环境类'
    return 'import类'


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


def _模块名到文件(路径们):
    """junit classname（rootdir 相对点分路径）→ 节点前缀（POSIX 路径）。

    对每个待跑路径登记双键：完整点分名（`tests.test_x`）与裸模块名
    （`test_x`）——两种 classname 口径都能重建（R157-B 收口修复同款考虑）。
    """
    表 = {}
    for 路径 in 路径们:
        posix = 路径.replace('\\', '/')
        模块 = posix[:-3].replace('/', '.')
        表[模块] = posix
        表.setdefault(os.path.basename(posix)[:-3], posix)
    return 表


def _从junit重建节点ID(用例, 模块表):
    """xdist 下 junit 无 file 属性，用 classname（点分模块名[.类]）+ name 重建。"""
    类名 = 用例.attrib.get('classname') or ''
    名 = 用例.attrib.get('name') or ''
    文件 = 用例.attrib.get('file')
    if 文件:
        裸 = os.path.basename(文件)[:-3]
        模块 = None
        for m in 模块表:
            if m == 裸 or m.endswith('.' + 裸):
                模块 = m
                break
        if 模块 is None:
            return None
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


def _收集错文件们(输出):
    """从子进程输出提取收集期失败的文件及其错误段（按文件切开）。

    返回 {posix路径: 错误段文本}。同时兜底收录短汇总里的裸 `ERROR x.py` 行。
    """
    行们 = (输出 or '').splitlines()
    结果 = {}
    当前 = None
    for 行 in 行们:
        # 段标题形如 `____ ERROR collecting tests/x.py ____`（前导下划线 + 空格）
        m = re.match(r'[_\s]*ERROR collecting (\S+\.py)', 行)
        if m:
            当前 = m.group(1).replace('\\', '/')
            结果.setdefault(当前, '')
            continue
        if 当前 is not None:
            if 行.startswith('=') or 行.startswith('!'):
                当前 = None
                continue
            结果[当前] += 行 + '\n'
    for 行 in 行们:
        m = re.match(r'^ERROR (\S+\.py)\s*$', 行)
        if m:
            结果.setdefault(m.group(1).replace('\\', '/'), '')
    return 结果


# ─────────────────────────────────────────────────────────────────────────────
# 基线层：full 写 / incremental 读（JSON 模块，勿文本正则）
# ─────────────────────────────────────────────────────────────────────────────

def _基线路径():
    return os.environ.get('R159E_BASELINE') or os.path.join(_基线目录, _基线文件名)


def _读基线():
    路径 = _基线路径()
    if not os.path.isfile(路径):
        return None
    try:
        with open(路径, encoding='utf-8') as f:
            数据 = json.load(f)
    except (ValueError, OSError):
        return None
    if not (isinstance(数据, dict) and isinstance(数据.get('节点结论'), dict)
            and isinstance(数据.get('文件清单'), list)):
        return None
    return 数据


def _写基线(模式, 路径们, 逐节点, 汇总):
    os.makedirs(os.path.dirname(_基线路径()) or '.', exist_ok=True)
    数据 = {
        '门禁': 'R159-E 顶层全套真跑门禁',
        '生成时间': datetime.datetime.now().isoformat(timespec='seconds'),
        '模式': 模式,
        '文件清单': [os.path.basename(p) for p in 路径们],
        '节点结论': 逐节点,
        '汇总': 汇总,
        '欠账键': sorted(_已知欠账),
        '存量import欠账键': sorted(_存量import欠账),
    }
    with open(_基线路径(), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(数据, f, ensure_ascii=False, indent=1)
    return _基线路径()


def _增量文件集(基线, 当前文件):
    """基线中红（失败/xfailed）文件 + 基线后新增文件（基线中绿不复发）。"""
    红文件 = set()
    for 节点ID, 结论 in (基线.get('节点结论') or {}).items():
        if (结论 or {}).get('状态') in ('失败', 'xfailed'):
            文件 = 节点ID.split('::')[0]
            if 文件.startswith('tests/') and 文件.endswith('.py'):
                红文件.add(os.path.basename(文件))
    新增 = set(当前文件) - set(基线.get('文件清单') or [])
    return sorted(红文件 | 新增)


def _解析模式():
    """返回 (模式, 路径们或None)。模式 ∈ {'full', 'incremental', 'unarmed'}。"""
    if os.environ.get('R159E_FULL') == '1':
        return 'full', _全量路径们()
    基线 = _读基线()
    if 基线 is None:
        return 'unarmed', None
    文件们 = _增量文件集(基线, _枚举())
    return 'incremental', [os.path.join('tests', f) for f in 文件们]


# ─────────────────────────────────────────────────────────────────────────────
# 执行层：子进程 --runxfail 真跑 → junit 解析 → 判定
# ─────────────────────────────────────────────────────────────────────────────

def _跑子进程(路径们, 超时):
    """子进程 --runxfail 真跑；返回 (rc, 输出文本, junit路径, 临时目录)。"""
    子环境 = dict(os.environ)
    worker覆盖 = 子环境.get('R159E_CHILD_WORKERS')
    临时目录 = tempfile.mkdtemp(prefix='r159e_顶层全套_')
    junit路径 = os.path.join(临时目录, 'junit.xml')
    命令 = [sys.executable, '-m', 'pytest', '--runxfail', '-q',
            '-p', 'no:cacheprovider', '--timeout=300',
            '--continue-on-collection-errors',
            '--junitxml', junit路径]
    命令 += [p.replace('\\', '/') for p in 路径们]
    命令 += ['-n', worker覆盖 or '1']
    try:
        r = subprocess.run(命令, cwd=_REPO, env=子环境,
                           capture_output=True, timeout=超时)
    except subprocess.TimeoutExpired:
        shutil.rmtree(临时目录, ignore_errors=True)
        raise AssertionError(
            '顶层全套门禁子进程超时（>%ds）——native 编译用例在负载下过慢？'
            '按 R152-C2 纪律逐例提限，不许动全局。' % 超时)
    输出 = ((r.stdout or b'') + b'\n' + (r.stderr or b'')).decode('utf-8', 'replace')
    return r.returncode, 输出, junit路径, 临时目录


def _跑门禁(模式, 路径们, 落基线=None):
    """门禁核心：真跑 → junit 解析 → 三分类 → 欠账校验。红则 raise。

    `落基线`：None = 仅 full 模式落；显式 False 供反跑用（不覆盖真基线）。
    """
    if 落基线 is None:
        落基线 = (模式 == 'full')
    if not 路径们:
        return {'模式': 模式, '文件数': 0, '执行节点数': 0, '逐节点': {},
                '通过': 0, '失败': 0, 'xfailed': 0, '跳过': [],
                'import类红': [], '未登记合法失败': [], '僵尸欠账提示': [],
                '存量import欠账在案': [], '说明': '增量集为空（无基线红、无新增文件）'}

    超时 = 2400 if 模式 == 'full' else 1800
    超时覆盖 = os.environ.get('R159E_TIMEOUT')
    if 超时覆盖:
        超时 = int(超时覆盖)
    rc, 输出, junit路径, 临时目录 = _跑子进程(路径们, 超时)
    try:
        if rc not in (0, 1, 2, 5):
            raise AssertionError(
                '顶层全套门禁子进程异常退出 rc=%d（非 0/1/2/5）——基础设施错误，'
                '按红处理：\n%s' % (rc, 输出[-2000:]))
        if not os.path.exists(junit路径):
            raise AssertionError('顶层全套门禁子进程未生成 junit——按红处理：\n%s'
                                 % 输出[-2000:])

        模块表 = _模块名到文件(路径们)
        逐节点 = {}
        for 套件 in ET.parse(junit路径).getroot().iter('testsuite'):
            for 用例 in 套件.iter('testcase'):
                节点ID = _从junit重建节点ID(用例, 模块表)
                if 节点ID is None:
                    continue
                失败 = [c for c in 用例 if c.tag in ('failure', 'error')]
                跳过 = [c for c in 用例 if c.tag == 'skipped']
                if 失败:
                    消息 = (失败[0].attrib.get('message')
                            or (失败[0].text or ''))[:300]
                    逐节点[节点ID] = {'状态': '失败', '消息': 消息}
                elif 跳过:
                    类型 = 跳过[0].attrib.get('type') or ''
                    消息 = (跳过[0].attrib.get('message') or '')[:200]
                    逐节点[节点ID] = {'状态': 'xfailed' if 'xfail' in 类型 else '跳过',
                                      '消息': 消息}
                else:
                    逐节点[节点ID] = {'状态': '通过', '消息': ''}

        收集错 = _收集错文件们(输出)
        if not 逐节点 and not 收集错:
            raise AssertionError(
                '子进程无任何节点结论且无收集错记录（rc=%d）——基础设施可疑，'
                '按红处理：\n%s' % (rc, 输出[-2000:]))

        # ── 判定 ──
        import类红 = []
        未登记合法失败 = []
        跳过们 = []
        for 节点ID, c in sorted(逐节点.items()):
            if c['状态'] == '失败':
                分类 = _失败分类(c['消息'])
                if 分类 == 'import类':
                    if 节点ID not in _存量import欠账:
                        import类红.append((节点ID, c['消息']))
                elif 节点ID not in _已知欠账:
                    未登记合法失败.append((节点ID, '[%s] %s' % (分类, c['消息'])))
            elif c['状态'] == 'xfailed':
                # 命令式 xfail（--runxfail 无法透视的那一档，R157-B 同族）：
                # 必须登记，不许静默跳过
                if 节点ID not in _已知欠账:
                    未登记合法失败.append((节点ID, '[命令式xfail] %s' % c['消息']))
            elif c['状态'] == '跳过':
                跳过们.append(节点ID)
        for 文件, 段 in sorted(收集错.items()):
            分类 = _失败分类(段)
            if 分类 == 'import类':
                if 文件 not in _存量import欠账:
                    import类红.append((文件, '收集期失败：%s' % 段.strip()[-200:]))
            elif 文件 not in _已知欠账:
                未登记合法失败.append((文件, '[收集期%s] %s' % (分类, 段.strip()[-200:])))

        欠账问题 = {k: _检查欠账条目(v) for k, v in _已知欠账.items()
                    if _检查欠账条目(v)}
        存量问题 = {k: _检查欠账条目(v) for k, v in _存量import欠账.items()
                    if _检查欠账条目(v)}
        僵尸欠账提示 = sorted(
            k for k in _已知欠账
            if k in 逐节点 and 逐节点[k]['状态'] == '通过')
        存量在案 = sorted(k for k in _存量import欠账 if k in 逐节点)

        汇总 = {'文件数': len(路径们), '执行节点数': len(逐节点),
                '通过': sum(1 for v in 逐节点.values() if v['状态'] == '通过'),
                '失败': sum(1 for v in 逐节点.values() if v['状态'] == '失败'),
                'xfailed': sum(1 for v in 逐节点.values() if v['状态'] == 'xfailed'),
                '跳过': len(跳过们),
                'import类红': len(import类红), '未登记合法失败': len(未登记合法失败)}
        报告 = {'模式': 模式, '文件数': len(路径们), '执行节点数': len(逐节点),
                '逐节点': 逐节点, '通过': 汇总['通过'], '失败': 汇总['失败'],
                'xfailed': 汇总['xfailed'], '跳过': 跳过们,
                'import类红': import类红, '未登记合法失败': 未登记合法失败,
                '僵尸欠账提示': 僵尸欠账提示, '存量import欠账在案': 存量在案,
                '收集错': 收集错}

        # full 模式无论红绿先落基线（红态基线 = 欠账登记输入 + D 线对照表）
        if 落基线:
            报告['基线落点'] = _写基线(模式, 路径们, 逐节点, 汇总)
    finally:
        shutil.rmtree(临时目录, ignore_errors=True)

    if 存量问题:
        raise AssertionError('存量 import 欠账清单有条目不合规：\n%s' % 存量问题)
    if import类红:
        raise AssertionError(
            '🚨 顶层全套真跑发现 import 类失败（本门禁要堵的洞；仓库内模块缺失/'
            '导入名不存在无常规欠账通道）：\n%s\n'
            '——修 import；确属存量须逐条登记 _存量import欠账（理由+issue+到期）。\n%s'
            % ('\n'.join('  %s\n    %s' % (k, m) for k, m in import类红),
               输出[-1500:]))
    if 未登记合法失败:
        raise AssertionError(
            '以下顶层用例真跑失败（环境类/语义类 = 合法存量欠账）或命令式 xfail，'
            '但未登记欠账：\n%s\n'
            '——按 _已知欠账[键] = (理由, issue, 到期日) 登记（过期自动红），'
            '或修好后摘掉 marker。\n%s'
            % ('\n'.join('  %s\n    %s' % (k, m) for k, m in 未登记合法失败),
               输出[-1500:]))
    if 欠账问题:
        raise AssertionError('欠账清单有条目不合规：\n%s' % 欠账问题)
    return 报告


# ─────────────────────────────────────────────────────────────────────────────
# 门禁用例
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.timeout(2700)
def test_顶层全套真跑_无新增红():
    """动态枚举顶层全部 test_*.py 真跑；import 类红，合法存量须登记欠账。"""
    模式, 路径们 = _解析模式()
    if 模式 == 'unarmed':
        pytest.skip(
            '顶层全套真跑门禁尚未武装：未找到基线 %s。\n'
            '武装方式（首跑一次全量，~20-40min）：\n'
            '  R159E_FULL=1 R159E_CHILD_WORKERS=4 pytest '
            'tests/unit/test_R159_顶层全套真跑门禁.py\n'
            '日常模式（增量）在武装后自动生效；0.82/CI 不同步 _r159_scratch/，'
            '故本门在那些机器上退化为静态层 + 本跳过（不拖慢全量门）。'
            % _基线路径())
    报告 = _跑门禁(模式, 路径们)
    print('R159E摘要（%s）：文件 %d，节点 %d，通过 %d，失败 %d，xfailed %d，跳过 %d'
          % (模式, 报告['文件数'], 报告['执行节点数'], 报告['通过'],
             报告['失败'], 报告['xfailed'], len(报告['跳过'])))
    if 报告.get('说明'):
        print('R159E说明：%s' % 报告['说明'])
    if 报告.get('基线落点'):
        print('R159E基线已写入：%s' % 报告['基线落点'])
    if 报告['存量import欠账在案']:
        print('存量 import 欠账在案（到期必须清零）：%s'
              % '; '.join(报告['存量import欠账在案']))
    # 摘要 + 非通过结论进 stdout，便于 0.82/0.86 跑批时肉眼核对（审计友好）
    for 节点ID, c in sorted(报告['逐节点'].items()):
        if c['状态'] != '通过':
            print('R159E逐节点 [%s] %s —— %s'
                  % (c['状态'], 节点ID, (c['消息'] or '')[:120]))
    if 报告['僵尸欠账提示']:
        print('提示（不拦）：登记欠账但本次通过的键：%s' % 报告['僵尸欠账提示'])


def test_枚举覆盖顶层全部文件():
    """枚举必须自洽：非空、数量下限、文件真实存在、旧门边界保持。"""
    文件们 = _枚举()
    assert 文件们, 'tests/ 顶层没扫到任何 test_*.py —— 扫描逻辑坏了'
    assert len(文件们) >= 150, (
        '顶层枚举数 %d < 150——扫描逻辑可疑（起草时实测 156）' % len(文件们))
    for f in 文件们:
        assert os.path.isfile(os.path.join(_测试根, f)), f
    # 旧门边界：R153 collect 门禁是顶层文件，必须仍在枚举面内
    assert 'test_R153_顶层collect门禁.py' in 文件们
    # 本门与 R157-B 门禁在 tests/unit/，不在顶层扫描面（不自我递归）
    assert os.path.basename(__file__) not in 文件们
    assert 'test_R157_顶层xfail门禁.py' not in 文件们


def test_欠账清单条目字段完整():
    for 路径, 条目 in _已知欠账.items():
        assert isinstance(条目, tuple) and len(条目) == 3, \
            '%s 欠账条目必须是 (理由, issue, 到期) 三元组' % 路径
        assert _检查欠账条目(条目) is None, \
            '%s 欠账登记不合规：%s' % (路径, _检查欠账条目(条目))


def test_欠账清单不过期():
    过期 = {p: _检查欠账条目(e) for p, e in _已知欠账.items() if _检查欠账条目(e)}
    assert not 过期, '以下欠账已过期，必须销账或重订期：%s' % 过期


def test_欠账机制有牙():
    """反跑：四种坏登记都必须被判不合规（清单不是摆设）。"""
    assert _检查欠账条目(('理由', 'ISSUE-1', '2020-01-01')) is not None
    assert _检查欠账条目(('', 'ISSUE-1', '2999-01-01')) is not None
    assert _检查欠账条目(('理由', '', '2999-01-01')) is not None
    assert _检查欠账条目(('理由', 'ISSUE-1', '2026/11/30')) is not None
    assert _检查欠账条目(('理由', 'ISSUE-1', '2999-01-01')) is None


def test_存量import欠账机制有牙():
    """反跑：存量 import 通道同一契约（坏登记必须不合规）。"""
    assert _检查欠账条目(('理由', 'ISSUE-1', '2020-01-01')) is not None
    assert _检查欠账条目(('理由', 'ISSUE-1', '2999-01-01')) is None


def test_分类器有牙():
    """反跑：import 类（仓库内）/ 环境类（第三方缺失）/ 语义类 三分有牙。"""
    # import 类（缺的是仓库内模块）→ import类
    for 消息 in ("ModuleNotFoundError: No module named '节点网络'",
                "ImportError: cannot import name '字符集转换为字符串' from '编码解码'",
                "ModuleNotFoundError: No module named 'tests.conftest'",
                "error during collection of tests/test_x.py"):
        assert _失败分类(消息) == 'import类', '漏判 import 类：%s' % 消息
    # 环境类（缺的全是第三方包）→ 环境类（欠账通道）
    for 消息 in ("ModuleNotFoundError: No module named 'aiohttp'",
                "ModuleNotFoundError: No module named 'pypinyin'"):
        assert _失败分类(消息) == '环境类', '误判 import 类：%s' % 消息
    # 语义类 → 放过
    for 消息 in ("AssertionError: 'hello' != b'hello'",
                "TypeError: ord() expected string of length 1, but int found",
                "TimeoutError: 子进程超时"):
        assert _失败分类(消息) == '语义类', '误判：%s' % 消息


def test_仓库内模块判定有牙():
    assert _是仓库内模块('节点网络'), 'stdlib/分布式/节点网络.light 应判仓库内'
    assert _是仓库内模块('编码解码'), 'stdlib/编码解码.light 应判仓库内'
    assert _是仓库内模块('src.llvm.compiler'), 'src/llvm/compiler.py 应判仓库内'
    assert not _是仓库内模块('aiohttp'), '第三方包不应判仓库内'
    assert not _是仓库内模块(''), '空名不应判仓库内'


def test_增量文件集有牙():
    """反跑：基线中红文件 + 新增文件必须被选中；基线绿文件不复发。"""
    假基线 = {'文件清单': ['test_a.py', 'test_b.py'],
              '节点结论': {
                  'tests/test_a.py::test_x': {'状态': '失败', '消息': 'x'},
                  'tests/test_a.py::test_y': {'状态': 'xfailed', '消息': 'y'},
                  'tests/test_b.py::test_z': {'状态': '通过', '消息': ''}}}
    # 基线红文件选中；基线绿文件（test_b）不复发；基线后新增（test_c）入面
    assert _增量文件集(假基线, ['test_a.py', 'test_b.py']) == ['test_a.py']
    assert _增量文件集(假基线, ['test_a.py', 'test_b.py', 'test_c.py']) == \
        ['test_a.py', 'test_c.py']
    assert _增量文件集({'文件清单': [], '节点结论': {}}, ['test_a.py']) == ['test_a.py']


def test_反跑_注入假import必须转红():
    """端到端反跑：函数内 `from 节点网络 import 不存在的导出名字` → 门禁必须转红。

    ⚠️ 探针落 `_r159_scratch/e_反跑隔离/`（**不落 `tests/` 主扫描区**）：
    R157-B 收口修复的教训——探针若进 `tests/`，会与 R153 collect 门禁争用
    扫描区，并发下把 R153 带红。该目录 gitignored，且不受 tests/conftest.py
    的导入钩子影响（钩子只作用于 tests/ 下的用例），正好模拟「函数内 import
    仓库内模块的错误导出」这一真洞形态。
    """
    探针文件 = 'test_R159E_反跑探针_自动清理.py'
    探针目录 = os.path.join(_基线目录, 'e_反跑隔离')
    探针路径 = os.path.join(探针目录, 探针文件)
    探针相对 = os.path.relpath(探针路径, _REPO).replace('\\', '/')
    探针节点 = 探针相对 + '::test_假import必须被顶层全套门禁抓住'
    内容 = (
        '# -*- coding: utf-8 -*-\n'
        '"""R159-E 反跑探针（临时存在数秒，finally 强制删除）。\n'
        '模拟顶层从不被执行的真洞：函数内 import 仓库内模块的错误导出。\n'
        '"""\n'
        '\n'
        '\n'
        'def test_假import必须被顶层全套门禁抓住():\n'
        '    from 节点网络 import 不存在的导出名字\n'
        '    assert 不存在的导出名字\n'
    )
    os.makedirs(探针目录, exist_ok=True)
    try:
        with open(探针路径, 'w', encoding='utf-8', newline='\n') as f:
            f.write(内容)
        with pytest.raises(AssertionError) as 异常:
            _跑门禁('full', [探针相对], 落基线=False)
        消息 = str(异常.value)
        assert _失败分类(消息) == 'import类', (
            '门禁转红的原因不是 import 类——分类器或判定链坏了：\n%s' % 消息[:1500])
        assert 探针节点 in 消息 or os.path.basename(探针文件) in 消息, (
            '转红信息没定位到探针节点：\n%s' % 消息[:1500])
    finally:
        if os.path.exists(探针路径):
            os.remove(探针路径)
        try:
            os.rmdir(探针目录)
        except OSError:
            pass


def test_门禁不碰共享文件():
    """自律断言：本门禁只读 tests/ 顶层（诊断），不写任何被测文件。"""
    assert os.path.basename(__file__) not in _顶层测试文件()
    assert 'test_R153_顶层collect门禁.py' in _顶层测试文件()
    assert 'test_R157_顶层xfail门禁.py' not in _顶层测试文件()
