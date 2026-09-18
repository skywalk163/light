# -*- coding: utf-8 -*-
"""R40 任务3「语言支撑配套」回归守卫。

覆盖三件事（对应任务书 3.1 / 3.2 / 3.3）：

1. **全角标点等价契约**（任务3.1 判定的正面结论）
   语言**本就**承诺并实现了全角标点容错：`keywords.SYMBOL_MAP` 把
   `，；：（）、【】《》｛｝` 归一化为半角等价物，词法器经该表发出同型 token。
   规范明文见 `docs/光明-完整规范文档.md` §3「逗号：`，` 与 `,` 等价」/§4「分号：`；` 与 `;` 等价」。
   本类钉住该契约，防止未来保护表精简时误伤。

2. **NameError「词法整串合并嫌疑」提示**（任务3.2 新增的报错文本）
   只改报错文本生成路径，不改切词/解析。

3. **basic.light 两处既有词法回归的现状钉桩**（任务3.1/3.3 的取证结论）
   两处回归均为 **R19 / R22 引入、与全角逗号无关**；
   钉住现状使变化可感知：将来修好，本类会反红，逼着同步更新结论与入账。

证据与完整论证见 `light-merge/_task3_R40_语言支撑配套.md`。
"""

import io
import os
import subprocess
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_SRC = os.path.join(_ROOT, 'src')
for _p in (_SRC, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from keywords import SYMBOL_MAP                      # noqa: E402
from lexer import Lexer                              # noqa: E402
from enhanced_errors import ErrorFormatter           # noqa: E402


def _types(src):
    """只取 token 类型序列（全角/半角的值本身不同，语义等价要看类型）。"""
    return [t.type.name for t in Lexer().tokenize(src) if t.type.name != 'EOF']


def _tokens(src):
    return [(t.type.name, t.value) for t in Lexer().tokenize(src) if t.type.name != 'EOF']


# =============================================================================
# 1. 全角标点等价契约
# =============================================================================
class Test全角标点等价契约:
    """全角标点 → 半角 token 的等价性（语言既有契约，非 R40 新增）。"""

    # SYMBOL_MAP 里登记的全角 → 半角归一化映射（值层面）
    MAP_EXPECT = {
        '，': ',', '；': ';', '：': ':', '（': '(', '）': ')',
        '、': '\\', '。': '.', '【': '[', '】': ']',
        '《': '<', '》': '>', '｛': '{', '｝': '}',
    }

    def test_SYMBOL_MAP_全角归一化表存在(self):
        for fw, hw in self.MAP_EXPECT.items():
            assert SYMBOL_MAP.get(fw) == hw, (
                '全角 %r 应归一化为 %r；docs/光明-完整规范文档.md §3/§4 明文承诺'
                '「，与,等价」「；与;等价」' % (fw, hw))

    @pytest.mark.parametrize('fw,hw', [
        ('，', ','), ('；', ';'), ('：', ':'), ('（', '('), ('）', ')'),
        ('、', ','), ('【', '['), ('】', ']'), ('｛', '{'), ('｝', '}'),
    ])
    def test_全角与半角发出同型token(self, fw, hw):
        assert _types(fw) == _types(hw), '%r 与 %r 应发同型 token' % (fw, hw)

    def test_中文句号与书名号是专属token而非等价(self):
        """`。`/`《》` 归一化到半角**符号**但发出专属 token——这是有意设计，别误判为缺陷。

        `。` 是语句终止符（PERIOD），`. `是成员访问符（DOT），二者语义不同；
        `《》` 是书名号（LBOOK/RBOOK），`<`/`>` 是比较运算符。
        """
        assert _types('。')[0] == 'PERIOD' and _types('.')[0] == 'DOT'
        assert _types('》')[0] == 'RBOOK' and _types('>')[0] == 'GREATER'

    @pytest.mark.parametrize('fw,hw', [('，', ','), ('；', ';'), ('：', ':')])
    def test_全角标点在语句级等价(self, fw, hw):
        """同一段程序，全角/半角写法的 token 类型序列必须逐位一致。"""
        cases = {
            '，': ('设 甲 为 [1，2]。', '设 甲 为 [1,2]。'),
            '；': ('设 甲 为 1；设 乙 为 2。', '设 甲 为 1;设 乙 为 2。'),
            '：': ('如果 甲 大于 0：\n    设 乙 为 1。', '如果 甲 大于 0:\n    设 乙 为 1。'),
        }
        a, b = cases[fw]
        assert _types(a) == _types(b)

    def test_形参列表全角逗号等价(self):
        fw = '段落 加法(甲, 乙)：\n    返回 甲 加 乙。\n'
        hw = '段落 加法(甲, 乙)：\n    返回 甲 加 乙。\n'
        assert _types(fw) == _types(hw)
        assert 'COMMA' in _types(fw)

    def test_实参列表全角逗号等价(self):
        assert _types('打印(最大(1，2))。') == _types('打印(最大(1,2))。')

    def test_字典字面量全角逗号等价(self):
        assert _types('设 甲 为 {"一":1，1:"二"}。') == _types('设 甲 为 {"一":1,1:"二"}。')


# =============================================================================
# 2. NameError「词法整串合并嫌疑」提示（任务3.2）
# =============================================================================
class Test合并嫌疑提示:
    """只验提示文本生成（_lexical_merge_hint），不触碰切词/解析。"""

    HIT = [
        "name '如果数小于等于二那么返回一' is not defined",   # advanced.light L10 原案（3 个从句关键字）
        "name '如果甲大于乙那么返回甲' is not defined",        # 纯从句型（如果/那么/返回）
        "name '结果为甲加乙乘2' is not defined",              # basic.light L10 形态（为 + 运算符）
        "name '设和为加法' is not defined",                   # basic.light L23 形态（为 + 加）
        "name '设计数为计数加1' is not defined",              # basic.light L40 形态（为 + 加）
    ]
    MISS = [
        "name '甲' is not defined",                # 太短
        "name '余额' is not defined",              # 太短
        "name '因为天气原因' is not defined",       # 6 字符但只有 1 个关键字 → 正常中文名
        "name '当前工作目录' is not defined",       # 含 当/目录 → 正常中文名
        "name '作用域过滤组装' is not defined",     # 含 作用域 → 正常中文名
        "name 'undefined_xyz' is not defined",     # 无汉字
        "name '己余额' is not defined",            # 3 字符合并（短合并本提示不覆盖，已登记）
        "unsupported operand type(s)",             # 非 NameError
        # ↓ R40 第 3 版收紧（「形态一需 ≥2 个不同从句关键字」）后**新消除**的单关键字误报
        "name '返回JSON' is not defined",           # 正常名：只含 1 个从句关键字 返回
        "name '统计段落数' is not defined",          # 正常名：只含 段落
        "name '解析段落定义' is not defined",        # 正常名：只含 段落
        "name '跳过字符串字面量' is not defined",     # 正常名：只含 跳过
        "name '非空数组断言' is not defined",        # 正常名：只含 断言
        "name '返回值类型检查' is not defined",      # 正常名：只含 返回
        "name 'n乘阶乘加返回一' is not defined",     # 只含 1 个从句关键字（返回）⇒ 不提示（保守）
    ]

    @pytest.mark.parametrize('msg', HIT)
    def test_疑似合并名给出提示(self, msg):
        hint = ErrorFormatter()._lexical_merge_hint('NameError', msg)
        assert hint, '应给出合并嫌疑提示：%s' % msg
        assert '词法整串合并' in hint
        assert '空格' in hint

    @pytest.mark.parametrize('msg', MISS)
    def test_正常名与短名不提示(self, msg):
        assert ErrorFormatter()._lexical_merge_hint('NameError', msg) == '', \
            '不应误报：%s' % msg

    def test_只有NameError类型才提示(self):
        f = ErrorFormatter()
        assert f._lexical_merge_hint('TypeError', "name '结果为甲加乙乘2' is not defined") == ''
        assert f._lexical_merge_hint('AttributeError', "name '结果为甲加乙乘2' is not defined") == ''

    def test_格式化输出里真的出现提示行(self):
        """端到端（格式化器层）：format_error 的输出应含「提示:」行。"""
        err = NameError("name '结果为甲加乙乘2' is not defined")
        out = ErrorFormatter().format_error('打印(结果为甲加乙乘2)。', err)
        assert '名称错误' in out
        assert '提示:' in out and '词法整串合并' in out

    def test_格式化输出对正常名不出现提示行(self):
        err = NameError("name '因为天气原因' is not defined")
        out = ErrorFormatter().format_error('打印(因为天气原因)。', err)
        assert '名称错误' in out
        assert '词法整串合并' not in out


# =============================================================================
# 3. basic.light 既有词法回归的现状钉桩（R19 / R22 引入，与全角逗号无关）
# =============================================================================
class Test现状钉桩_既有词法回归:
    """⚠️ 本类**钉住的是当前（错误）行为**，不是期望行为。

    这样做的目的：任何人修好这些回归，本类立刻反红 → 强制同步更新任务3 结论、
    缺陷账与基线。任务3 全角逗号判定期间用跨版本 A/B 定位到的两个真因：

      · `为` 整串合并      —— R19 `49319306`（`lexer._EMBED_MAX_MATCH_KEYWORDS`）
      · `接收X` / `己X` 合并 —— R22 `e99bdb80`（IDENTIFIER_SAFE_KEYWORDS 清表副作用）

    两者都**不是**全角逗号造成的：把 `，` 换成 `,` 后报错逐字相同（见任务3 报告）。
    """

    def test_现状钉桩_R19_为字整串合并(self):
        """`设结果为甲加乙乘2` 曾吞成 `设` + IDENTIFIER('结果为甲加乙乘2')。

        R59 任务1（lexer._at_statement_start/._emb_head_trigger/._assign_tail）已修好
        _EMBED 的 `为` 合并，正确切分（父提交 500743bc 实测）现已成为现状：
          设 / 结果 / 为 / 甲 / 加 / 乙 / 乘 / 2
        钉桩转正：断言期望正确切分。缺陷条目 R19 `49319306` 已关闭（R59 任务1）。
        """
        got = _tokens('设结果为甲加乙乘2')
        assert got == [('KEYWORD', '设'), ('IDENTIFIER', '结果'), ('KEYWORD', '为'),
                       ('IDENTIFIER', '甲'), ('KEYWORD', '加'), ('IDENTIFIER', '乙'),
                       ('KEYWORD', '乘'), ('NUMBER', 2)], (
            'R59 任务1 修复后应为正确切分；若此处再变，请复核 lexer._assign_tail 四重判据。实际=%r'
            % (got,))

    def test_现状钉桩_R22_接收字合并(self):
        """[R60 转正] `段落加法接收甲，乙：` 现在正确切为 `接收` + `甲`。

        R60 任务1 修复B 定向豁免（`接收` + 余部已声明 且 整串后紧随 `，/：`
        的真形参表位置）后，`接收甲` 不再被并成一个 IDENTIFIER。
        正确切分 = 段落 / 加法 / 接收 / 甲 / ， / 乙 / ：
        原钉桩（断言合并仍在）已过期，转正为新现状（缺陷关闭）。
        """
        got = _tokens('段落加法接收甲，乙：')
        assert ('KEYWORD', '接收') in got, (
            '现状异常：`接收` 未切出。实际=%r' % (got,))
        assert ('IDENTIFIER', '接收甲') not in got, (
            '现状异常：`接收甲` 仍被合并。实际=%r' % (got,))

    def test_现状钉桩_R22_己字在类体内合并(self):
        """类体内 `己余额` 被并成一个 IDENTIFIER（同 R22 清表副作用）。

        独立单行 `己余额 等于 ...` 切分正常；只有**整文件**（预扫描出定义名后）才复现，
        所以这里用整份 examples/class_access_control.light 取证。
        """
        src = io.open(os.path.join(_ROOT, 'examples', 'class_access_control.light'),
                      encoding='utf-8').read()
        got = [(t.line, t.value) for t in Lexer().tokenize(src)
               if t.type.name == 'IDENTIFIER' and '己' in str(t.value)]
        assert got, ('现状已变（可能修好了 `己X` 合并）。请更新本钉桩与'
                     ' tests/unit/test_examples_run.py 的 class_* 期望。')
        assert got[0][1] == '己余额'

    def test_现状钉桩_全角逗号不是这两个回归的原因(self):
        """[R60 转正] 全角/半角逗号版本 token 形态一致（仍是同一组正确 token）。

        R60 任务1 修复B 后，两版都正确切为 段落/加法/接收/甲/，/乙/：，
        差异仅 COMMA 原始字符。原钉桩 ③ 断言 `接收甲` 合并（错误与逗号
        宽度无关的反证前提）已随修复过期，转正为新现状（缺陷关闭）。
        """
        fw = _tokens('段落加法接收甲，乙：')
        hw = _tokens('段落加法接收甲,乙：')
        # ① token **类型**序列逐位一致 —— SYMBOL_MAP 把 ，归一化成同一个 COMMA
        assert _types('段落加法接收甲，乙：') == _types('段落加法接收甲,乙：')
        # ② 唯一的差异就是逗号 token 携带的原始字符，别处一律不得有差
        diff = [(a, b) for a, b in zip(fw, hw) if a != b]
        assert len(diff) == 1 and diff[0][1][0] == 'COMMA', (
            '全角/半角版本的差异不止逗号本身，判定前提需重审：%r' % (diff,))
        # ③ 两版都把 `接收甲` 正确切开 —— 逗号宽度对切分无影响（修复后同为正确）
        assert ('KEYWORD', '接收') in fw and ('IDENTIFIER', '接收甲') not in fw
        assert ('KEYWORD', '接收') in hw and ('IDENTIFIER', '接收甲') not in hw


# =============================================================================
# 4. 端到端（真的跑一遍 cli/light.py run，断言 stderr 出现提示）
# =============================================================================
class Test端到端提示:
    def _run(self, source):
        tmpdir = tempfile.mkdtemp(prefix='r40_t3_')
        path = os.path.join(tmpdir, 'probe.light')
        io.open(path, 'w', encoding='utf-8', newline='\n').write(source)
        env = dict(os.environ)
        env['PYTHONIOENCODING'] = 'utf-8'
        proc = subprocess.run(
            [sys.executable, os.path.join(_ROOT, 'cli', 'light.py'), 'run', path],
            cwd=_ROOT, capture_output=True, env=env)
        return proc.returncode, (proc.stdout or b'').decode('utf-8', 'replace'), \
               (proc.stderr or b'').decode('utf-8', 'replace')

    def test_E2E_长未定义名触发提示(self):
        rc, _out, err = self._run('打印(结果为甲加乙乘2)。\n')
        assert rc != 0
        assert '名称错误' in err
        assert '词法整串合并' in err, 'stderr 应含合并嫌疑提示。实际：\n%s' % err

    def test_E2E_正常未定义名不触发提示(self):
        rc, _out, err = self._run('打印(因为天气原因)。\n')
        assert rc != 0
        assert '名称错误' in err
        assert '词法整串合并' not in err, '正常中文名不应被提示为合并。实际：\n%s' % err
