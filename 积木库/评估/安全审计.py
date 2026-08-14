# -*- coding: utf-8 -*-
"""段言积木库 安全审计扫描器（路径解析 / 解压逻辑逃逸专项）。

扫描范围：积木库/*.py 与 积木库/**/*.py（递归），排除 评估/（本工具自身所在目录）
与 __pycache__。

覆盖漏洞类别：
  1) 路径穿越 (path traversal) —— 文件写/读使用 块名 / 需求 / LLM 返回 / 方案.路径 等
     不可信输入拼接路径时，落点是否净化。
  2) zip/tar 解压逃逸 —— 是否使用 zipfile/tarfile 解压且未校验成员名 ../ / 绝对路径 / 符号链接。
  3) 不安全反序列化 —— pickle.loads / yaml.load(无 SafeLoader) / marshal 等。
  4) 命令注入 —— os.system / subprocess shell=True 拼接不可信输入；或 eval()/exec() 直接消费不可信串。
  5) 其他 —— __import__ 动态导入不可信模块名、危险 tempfile 权限等。

用法：
  python 评估/安全审计.py                 # 纯报告模式（默认，不改动任何代码）
  python 评估/安全审计.py --自修复        # 在报告基础上，对已知确证路径穿越做最小净化修复
  python 评估/安全审计.py --verbose       # 额外打印每条“已净化/未触发”细节

退出码：发现 0 个确证高危 => 0；发现 >=1 个确证高危 => 1（便于接入 CI）。

诚实边界：本扫描器只报告真实存在的代码特征，不虚构漏洞；对所有“是否确证”给出
可复核的判定依据（代码落点 + 是否已有净化调用）。
"""

import argparse
import ast
import os
import re
import sys

# ---------------------------------------------------------------------------
# 路径 / 范围
# ---------------------------------------------------------------------------
_HERE = os.path.abspath(os.path.dirname(__file__))          # 积木库/评估
_LIB = os.path.dirname(_HERE)                               # 积木库
EXCLUDE_DIRS = {'评估', '__pycache__'}
SCAN_EXT = ('.py',)

# 不可信来源键：块名/导出名/路径 等，用于污点判定
_PATH_KEYS = {'名称', '导出名', '路径'}
# 视为不可信输入的形参名（仅 注销(名称) 这类直接拿参数拼路径的入口需要种子；
# 其余靠 _不可信载体 {块,blk,s} 的 .get/下标 规则判定，避免把 索引/候选/内部名 误伤）
_SEED_PARAMS = {'名称'}
# 落点净化调用：函数体中出现这些调用之一即视为该写入/读取已做净化
_SANITIZERS = {'_归一块名', '_安全名', '_安全块路径', 'normpath', 'basename'}


# ---------------------------------------------------------------------------
# 文件收集
# ---------------------------------------------------------------------------
def 收集文件():
    out = []
    for 根, 目录, 文件 in os.walk(_LIB):
        目录[:] = [d for d in 目录 if d not in EXCLUDE_DIRS]
        for f in 文件:
            if f.endswith(SCAN_EXT):
                out.append(os.path.join(根, f))
    out.sort()
    return out


# ---------------------------------------------------------------------------
# AST 污点分析（路径穿越）
# ---------------------------------------------------------------------------
class _污点访问(ast.NodeVisitor):
    """在单个函数体内判定某个节点是否携带不可信来源（块名/路径 等）。"""

    def __init__(self, 污点集):
        self.污点集 = 污点集
        self.命中 = False

    # 仅当接收变量是 块/blk/s（LLM 生成块 / 方案步骤）时，其 名称/导出名/路径 才视为不可信。
    # 这样可排除 索引/候选 等受信本地数据（条目['名称']、c.get('名称') 用于提示串/打印串等），
    # 避免把 str.join 拼接提示、打印日志误报为文件落点穿越。
    _不可信载体 = {'块', 'blk', 's'}

    def visit_Call(self, n):
        f = n.func
        if isinstance(f, ast.Attribute) and f.attr == 'get' and n.args:
            v = f.value
            if isinstance(v, ast.Name) and v.id in self._不可信载体:
                a0 = n.args[0]
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str) \
                        and a0.value in _PATH_KEYS:
                    self.命中 = True
        self.generic_visit(n)

    def visit_Subscript(self, n):
        v = n.value
        if isinstance(v, ast.Name) and v.id in self._不可信载体:
            k = n.slice
            # Python <3.9 用 ast.Index 包裹常量
            if isinstance(k, ast.Index):
                k = k.value
            if isinstance(k, ast.Constant) and isinstance(k.value, str) \
                    and k.value in _PATH_KEYS:
                self.命中 = True
        self.generic_visit(n)

    def visit_Name(self, n):
        if n.id in self.污点集:
            self.命中 = True
        self.generic_visit(n)


def _含污点(节点, 污点集):
    v = _污点访问(污点集)
    try:
        v.visit(节点)
    except Exception:
        pass
    return v.命中


def _函数污点集(函数):
    """收集函数内被不可信来源污染的局部变量名（多轮传播）。"""
    污点 = set()
    # 种子：形参中本就是不可信输入的名字
    for a in 函数.args.args:
        if a.arg in _SEED_PARAMS:
            污点.add(a.arg)
    for _ in range(4):
        变 = False
        for n in ast.walk(函数):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and _含污点(n.value, 污点) \
                            and t.id not in 污点:
                        污点.add(t.id)
                        变 = True
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                if _含污点(n.value, 污点) and n.target.id not in 污点:
                    污点.add(n.target.id)
                    变 = True
        if not 变:
            break
    return 污点


def _有净化(函数):
    for n in ast.walk(函数):
        if isinstance(n, ast.Call):
            f = n.func
            名 = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if 名 in _SANITIZERS:
                return True
    return False


def _扫描函数_路径穿越(函数, 文件, 源码行, 结果):
    污点 = _函数污点集(函数)
    if not 污点:
        return
    for n in ast.walk(函数):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        # open(...) 第一个实参
        if isinstance(f, ast.Name) and f.id == 'open' and n.args:
            if _含污点(n.args[0], 污点):
                _记(文件, n.lineno, 源码行, 结果, 函数, 污点, '写')
        # os.path.join / os.path.isfile / os.remove / os.makedirs
        # 仅认 os.path.join（f.value.attr == 'path'），避免误伤 str.join
        elif isinstance(f, ast.Attribute):
            if f.attr == 'join' and isinstance(f.value, ast.Attribute) \
                    and f.value.attr == 'path' and _含污点(n, 污点):
                _记(文件, n.lineno, 源码行, 结果, 函数, 污点, '拼')
            elif f.attr in ('isfile', 'remove', 'makedirs') and n.args \
                    and _含污点(n.args[0], 污点):
                _记(文件, n.lineno, 源码行, 结果, 函数, 污点, '操作')


def _记(文件, 行号, 源码行, 结果, 函数, 污点, 动作):
    片段 = 源码行[行号 - 1].rstrip() if 0 < 行号 <= len(源码行) else ''
    净化 = _有净化(函数)
    结果.append({
        '文件': os.path.relpath(文件, _LIB),
        '行': 行号,
        '类别': '路径穿越',
        '函数': getattr(函数, 'name', '?'),
        '动作': 动作,
        '片段': 片段.strip(),
        '污点': sorted(污点),
        '确证': not 净化,
        '净化': 净化,
    })


# ---------------------------------------------------------------------------
# 正则扫描（zip/tar、反序列化、命令注入、动态导入、tempfile）
# ---------------------------------------------------------------------------
_正则类别 = [
    ('zip/tar 解压逃逸', re.compile(
        r'zipfile|tarfile|\.extractall\s*\(|\.extract\s*\(')),
    ('不安全反序列化', re.compile(
        r'pickle\.loads?\s*\(|yaml\.load\s*\(|marshal\.loads?\s*\(')),
    ('命令注入(shell/eval/exec)', re.compile(
        r'os\.system\s*\(|subprocess[^\n]*shell\s*=\s*True|os\.popen\s*\(|'
        r'os\.exec[^\n]*\(|\beval\s*\(|\bexec\s*\(')),
    ('动态导入不可信模块', re.compile(r'__import__\s*\(|importlib\.import_module\s*\(')),
    ('危险临时文件', re.compile(r'tempfile\.(mkdtemp|mkstemp|NamedTemporaryFile)')),
]


def _扫描正则(文件, 源码行, 结果, verbose):
    命中 = {c: [] for c, _ in _正则类别}
    for i, 行 in enumerate(源码行, 1):
        for 类别, 式 in _正则类别:
            m = 式.search(行)
            if m:
                命中[类别].append((i, 行.strip()))
    for 类别, _ in _正则类别:
        if 命中[类别]:
            for i, 行 in 命中[类别]:
                结果.append({
                    '文件': os.path.relpath(文件, _LIB), '行': i, '类别': 类别,
                    '函数': '-', '动作': '正则命中', '片段': 行,
                    '污点': [], '确证': True, '净化': False,
                })
        elif verbose:
            结果.append({
                '文件': os.path.relpath(文件, _LIB), '行': 0, '类别': 类别,
                '函数': '-', '动作': '未触发', '片段': '',
                '污点': [], '确证': False, '净化': False,
            })


# ---------------------------------------------------------------------------
# --自修复：对已知确证路径穿越做最小净化（幂等）
# ---------------------------------------------------------------------------
_兜底修正 = [
    # 注册：名 来自 LLM 返回，先净化
    ('    名 = 块.get(\'名称\') or 块.get(\'导出名\')\n    路径 = \'生成/%s.duan\' % 名',
     '    名 = _安全名(块.get(\'名称\') or 块.get(\'导出名\'))\n    路径 = \'生成/%s.duan\' % 名'),
    # 入待审：名 来自 LLM 返回，先净化
    ('    名 = 块.get(\'名称\') or 块.get(\'导出名\')\n    目录 = 待审目录(库根)',
     '    名 = _安全名(块.get(\'名称\') or 块.get(\'导出名\'))\n    目录 = 待审目录(库根)'),
    # 注销：名称 形参直接拼路径，先净化
    ('    库根 = 库根 or _HERE\n    idx_path = os.path.join(库根, \'索引.json\')',
     '    库根 = 库根 or _HERE\n    名称 = _安全名(名称)\n    idx_path = os.path.join(库根, \'索引.json\')'),
]

_粘合修正 = [
    ('        blk_path = os.path.join(库根, s.get(\'路径\') or \'\')\n'
     '        if not (blk_path and os.path.isfile(blk_path)):',
     '        blk_path = _安全块路径(库根, s.get(\'路径\') or \'\')\n'
     '        if not (blk_path and os.path.isfile(blk_path)):'),
]


def _插入_安全名(源码):
    """在 兜底生成器.py 的 _归一块名 定义后插入 _安全名 辅助函数（幂等）。"""
    标 = '    return (新 or \'生成块\'), (新 != 原)\n'
    if '_安全名(' in 源码 or '_安全名 (' in 源码:
        return None
    if 标 not in 源码:
        return None
    辅助 = (
        '\n'
        '\n'
        'def _安全名(名):\n'
        '    """把积木名净化成安全文件名基名（防御性净化落点）。\n'
        '    块名来自 LLM 返回（不可信），可能携带 ../ 、绝对路径或非法字符；\n'
        '    在写入 生成/ 前必须净化为合法基名，杜绝路径穿越。\n'
        '    """\n'
        '    新, _ = _归一块名(名)\n'
        '    # 双保险：归一已剔除非法字符，这里再显式剔除路径分隔符与父目录记号，并限长\n'
        '    新 = 新.replace(os.sep, \'\').replace(\'/\', \'\').replace(\'\\\\\', \'\').replace(\'..\', \'\')\n'
        '    return 新[:64]\n'
    )
    return 源码.replace(标, 标 + 辅助, 1)


def _插入_安全块路径(源码):
    """在 粘合.py 的 _提取段落 定义后插入 _安全块路径（幂等）。"""
    标 = "    return '\\n'.join(out).strip('\\n')\n"
    if '_安全块路径(' in 源码 or '_安全块路径 (' in 源码:
        return None
    if 标 not in 源码:
        return None
    辅助 = (
        '\n'
        '\n'
        'def _安全块路径(库根, 相对):\n'
        '    """把 方案 里的 路径 字段净化并校验不逃逸 库根。\n'
        '    方案可由外部提供，路径字段不可信；含 父目录记号(..) / 绝对路径 / 空成分\n'
        '    一律拒绝（返回 None），交由上层回退到 领域/块名 推断的安全路径；\n'
        '    仅当归一后仍严格落在 库根 内才放行。\n'
        '    """\n'
        '    相对 = (相对 or \'\').replace(\'\\\\\\\', \'/\').strip()\n'
        '    if not 相对:\n'
        '        return None\n'
        '    部件 = 相对.split(\'/\')\n'
        '    if any(p in (\'\', \'.\', \'..\') for p in 部件) or 相对.startswith(\'/\'):\n'
        '        return None\n'
        '    完整 = os.path.normpath(os.path.join(库根, 相对))\n'
        '    库根规范 = os.path.normpath(库根)\n'
        '    if 完整 != 库根规范 and not 完整.startswith(库根规范 + os.sep):\n'
        '        return None\n'
        '    return 完整\n'
    )
    return 源码.replace(标, 标 + 辅助, 1)


def 自修复(报告):
    改动 = []
    # 兜底生成器.py
    路径 = os.path.join(_LIB, '兜底生成器.py')
    if os.path.isfile(路径):
        s = open(路径, encoding='utf-8').read()
        s2 = _插入_安全名(s)
        if s2 is not None:
            s = s2
            改动.append('兜底生成器.py: 新增 _安全名() 净化辅助')
        for 旧, 新 in _兜底修正:
            if 旧 in s and 新 not in s:
                s = s.replace(旧, 新, 1)
                改动.append('兜底生成器.py: 注册/入待审/注销 写入前调用 _安全名()')
        open(路径, 'w', encoding='utf-8').write(s)
    # 粘合.py
    路径 = os.path.join(_LIB, '粘合.py')
    if os.path.isfile(路径):
        s = open(路径, encoding='utf-8').read()
        s2 = _插入_安全块路径(s)
        if s2 is not None:
            s = s2
            改动.append('粘合.py: 新增 _安全块路径() 越界校验')
        for 旧, 新 in _粘合修正:
            if 旧 in s and 新 not in s:
                s = s.replace(旧, 新, 1)
                改动.append('粘合.py: synthesize() 用 _安全块路径() 净化 方案.路径')
        open(路径, 'w', encoding='utf-8').write(s)
    return 改动


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def 主(参数):
    文件列表 = 收集文件()
    结果 = []
    for 文件 in 文件列表:
        try:
            源码 = open(文件, encoding='utf-8').read()
        except Exception as e:
            print('[跳过] 无法读取 %s: %s' % (文件, e), file=sys.stderr)
            continue
        源码行 = 源码.splitlines()
        # AST 路径穿越
        try:
            树 = ast.parse(源码)
        except SyntaxError as e:
            print('[跳过] 语法错误 %s: %s' % (文件, e), file=sys.stderr)
            continue
        for n in 树.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _扫描函数_路径穿越(n, 文件, 源码行, 结果)
        # 正则其他类别
        _扫描正则(文件, 源码行, 结果, 参数.verbose)

    # 去重（同一文件同一行的同一类别只报一次）
    已见 = set()
    唯一 = []
    for r in 结果:
        k = (r['文件'], r['行'], r['类别'])
        if k in 已见:
            continue
        已见.add(k)
        唯一.append(r)
    结果 = 唯一

    # 输出报告
    print('═' * 64)
    print('段言积木库 安全审计扫描')
    print('扫描根: %s' % _LIB)
    print('扫描文件数: %d（排除 评估/ 与 __pycache__）' % len(文件列表))
    print('═' * 64)

    确证列表 = [r for r in 结果 if r['确证']]
    for 类别 in ['路径穿越', 'zip/tar 解压逃逸', '不安全反序列化',
                '命令注入(shell/eval/exec)', '动态导入不可信模块', '危险临时文件']:
        该 = [r for r in 结果 if r['类别'] == 类别]
        if 类别 == '路径穿越':
            print('\n【%s】' % 类别)
            if not 该:
                print('  未发现确证漏洞')
            for r in 该:
                状态 = '确证高危' if r['确证'] else '已净化(非高危)'
                print('  %s:%d  [%s]  %s' % (r['文件'], r['行'], 状态, r['函数']))
                if r['片段']:
                    print('      代码: %s' % r['片段'])
                if r['确证']:
                    print('      风险: 写/读文件使用不可信输入(块名/路径)拼接，落点未净化，'
                          '可经 ../ 或绝对路径逃逸 库根。')
                    print('      判定: 确证 —— 函数体内无 %s 任一净化调用。' % '/'.join(sorted(_SANITIZERS)))
                else:
                    print('      风险: 已通过 _安全名/_安全块路径 等净化落点，不具穿越条件。')
                    print('      判定: 非高危 —— 已净化。')
        else:
            print('\n【%s】' % 类别)
            if 该:
                for r in 该:
                    print('  %s:%d  [%s]' % (r['文件'], r['行'], '确证高危' if r['确证'] else '已净化'))
                    if r['片段']:
                        print('      代码: %s' % r['片段'])
            else:
                print('  未发现确证漏洞（覆盖范围：积木库/*.py、积木库/**/*.py，'
                      '排除 评估/ 与 __pycache__）')

    print('\n' + '═' * 64)
    print('确证高危总数: %d' % len(确证列表))
    if 确证列表:
        print('退出码=1（建议接入 CI 阻断）')
    else:
        print('退出码=0（无确证高危）')
    print('═' * 64)

    return 1 if 确证列表 else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='段言积木库 安全审计扫描器')
    ap.add_argument('--自修复', action='store_true', help='在报告基础上对已知确证路径穿越做最小净化修复')
    ap.add_argument('--verbose', action='store_true', help='额外打印“已净化/未触发”细节')
    a = ap.parse_args()
    if a.自修复:
        改动 = 自修复(None)
        if 改动:
            print('[自修复] 已应用以下最小净化：')
            for c in 改动:
                print('  - ' + c)
        else:
            print('[自修复] 无需改动（相关净化已就位）')
        print('-' * 64)
    码 = 主(a)
    raise SystemExit(码)
