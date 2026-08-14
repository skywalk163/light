# -*- coding: utf-8 -*-
"""段言积木类型系统 v2（v0.18）。

v0.14~v0.17 的类型只有 5 个原子标签（数/文本/列表/逻辑/字典），互不兼容、精确相等
才算接得上。这套粗类型有两个致命缺陷：

  1) 「列表」不区分元素类型 —— 斐波那契 输出 列表[数]、切分文本 输出 列表[文本]，
     在旧系统里都是「列表」，于是 求和(切分文本(...)) 这种荒谬接线能通过类型闸门。
  2) 没有「可选 / 联合 / 字典[K,V]」—— 查找类块（找不到时返回空）、解析类块
     （返回键值对）无法如实描述契约，只能谎报成 数/列表，接线器被迫瞎猜。

v2 引入结构化类型表达式，并用「匹配度」代替布尔兼容，让接线器能在多个可接候选里
优先挑类型最贴合的那个。

── 语法 ───────────────────────────────────────────────
    基础      数 | 文本 | 逻辑 | 任意 | 空
    列表      列表[元素类型]           列表[数]、列表[列表[文本]]
    字典      字典[键类型, 值类型]      字典[文本, 数]
    可选      可选[T]                  语法糖 = 联合[T, 空]
    联合      联合[A, B, ...] 或 A|B   联合[数, 文本]、数|文本

    裸写的旧标签向后兼容：「列表」== 列表[任意]、「字典」== 字典[任意, 任意]。

── 匹配度 ─────────────────────────────────────────────
    匹配度(槽位需要, 实际拥有) -> 0.0 ~ 1.0
      1.00  精确同构
      0.95  联合分支命中（need 是联合，have 命中其中一支）
      0.60  渐进匹配（任意 参与其中，即契约未标注元素类型 —— 接得上但不确定）
      0.00  不兼容（拒接）

    「任意」是渐进类型的逃生舱：老块没标元素类型时不至于全库接不上，但匹配度低于
    精确匹配，接线器排序时自然会让位给标注完整的块。
"""

# ── 原子 ───────────────────────────────────────────────
数 = ('基础', '数')
文本 = ('基础', '文本')
逻辑 = ('基础', '逻辑')
任意 = ('基础', '任意')
空 = ('基础', '空')

_基础名 = {'数', '文本', '逻辑', '任意', '空'}

# 同义词 → 规范名。只做「写法归一」，不引入新种类，故不影响匹配度与既有契约语义。
_别名 = {
    # 文本
    '字符串': '文本', '串': '文本', '文字': '文本', 'str': '文本', 'string': '文本',
    # 数（段言不区分整/浮点，统一为 数）
    '整数': '数', '浮点': '数', '浮点数': '数', '小数': '数', '数字': '数', '数值': '数',
    'int': '数', 'integer': '数', 'float': '数', 'number': '数',
    # 逻辑
    '布尔': '逻辑', '真假': '逻辑', 'bool': '逻辑', 'boolean': '逻辑',
    # 任意 / 空
    '任意类型': '任意', 'any': '任意', 'object': '任意',
    '无': '空', 'none': '空', 'null': '空', 'void': '空',
    # 容器构造子
    '数组': '列表', '序列': '列表', 'list': '列表', 'array': '列表',
    '映射': '字典', '词典': '字典', 'dict': '字典', 'map': '字典',
    'optional': '可选', 'union': '联合',
}
_渐进 = 0.60
_联合分支 = 0.95


class 类型错误(ValueError):
    pass


# ── 解析 ───────────────────────────────────────────────
def _切顶层逗号(s):
    """按顶层逗号切分，忽略方括号内部的逗号。"""
    段, 深, buf = [], 0, []
    for ch in s:
        if ch == '[':
            深 += 1
        elif ch == ']':
            深 -= 1
            if 深 < 0:
                raise 类型错误('方括号不配对：' + s)
        if ch == ',' and 深 == 0:
            段.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    段.append(''.join(buf))
    if 深 != 0:
        raise 类型错误('方括号不配对：' + s)
    return [x.strip() for x in 段]


def _切顶层竖线(s):
    段, 深, buf = [], 0, []
    for ch in s:
        if ch == '[':
            深 += 1
        elif ch == ']':
            深 -= 1
        if ch == '|' and 深 == 0:
            段.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    段.append(''.join(buf))
    return [x.strip() for x in 段]


def 归一名(s):
    """把标量/容器的常见同义写法归一到规范名。

    LLM 兜底生成与人手写契约都高频写出 `字符串`/`整数` 这类自然同义词；若直接判为
    「无法解析的类型」，冒烟会以「无法为该契约造默认实参」跳过该块，护栏进而把本来
    能跑的好块误杀（v0.28 兜底首跑实测 8/13 失败源于此）。故在此统一归一。
    """
    t = (s or '').strip()
    return _别名.get(t) or _别名.get(t.lower()) or t


def 解析(s):
    """把类型字符串解析成类型 AST。None/空串 视为 任意。"""
    if isinstance(s, tuple):
        return s
    s = (s or '').strip()
    if not s:
        return 任意

    # A|B 简写（优先级最低，先切）
    分支 = _切顶层竖线(s)
    if len(分支) > 1:
        return 归一联合([解析(x) for x in 分支])

    s = 归一名(s)  # 同义词归一（字符串→文本 / 整数→数 / 数组→列表 …）

    if s in _基础名:
        return ('基础', s)

    # 向后兼容：裸写容器
    if s == '列表':
        return ('列表', 任意)
    if s == '字典':
        return ('字典', 任意, 任意)

    if s.endswith(']') and '[' in s:
        头 = 归一名(s[:s.index('[')].strip())
        内 = s[s.index('[') + 1:-1]
        参 = _切顶层逗号(内)
        if 头 == '列表':
            if len(参) != 1:
                raise 类型错误('列表[] 需要恰好 1 个参数：' + s)
            return ('列表', 解析(参[0]))
        if 头 == '字典':
            if len(参) != 2:
                raise 类型错误('字典[] 需要恰好 2 个参数：' + s)
            return ('字典', 解析(参[0]), 解析(参[1]))
        if 头 == '可选':
            if len(参) != 1:
                raise 类型错误('可选[] 需要恰好 1 个参数：' + s)
            return 归一联合([解析(参[0]), 空])
        if 头 == '联合':
            if len(参) < 2:
                raise 类型错误('联合[] 至少需要 2 个参数：' + s)
            return 归一联合([解析(x) for x in 参])
        raise 类型错误('未知的类型构造子「%s」：%s' % (头, s))

    raise 类型错误('无法解析的类型：' + s)


def 归一联合(项):
    """展平嵌套联合、去重、排序（保证同集合的联合结构唯一，便于相等判定）。"""
    扁 = []
    for t in 项:
        if t[0] == '联合':
            扁.extend(t[1])
        else:
            扁.append(t)
    去重 = []
    for t in 扁:
        if t not in 去重:
            去重.append(t)
    if 任意 in 去重:          # 联合里出现 任意 ⇒ 整体退化为 任意
        return 任意
    if len(去重) == 1:
        return 去重[0]
    return ('联合', tuple(sorted(去重, key=格式化)))


# ── 格式化 ─────────────────────────────────────────────
def 格式化(t):
    if t is None:
        return '任意'
    if t[0] == '基础':
        return t[1]
    if t[0] == '列表':
        return '列表[%s]' % 格式化(t[1])
    if t[0] == '字典':
        return '字典[%s, %s]' % (格式化(t[1]), 格式化(t[2]))
    if t[0] == '联合':
        支 = list(t[1])
        if 空 in 支 and len(支) == 2:
            其余 = [x for x in 支 if x != 空][0]
            return '可选[%s]' % 格式化(其余)
        return '联合[%s]' % ', '.join(格式化(x) for x in 支)
    raise 类型错误('未知类型节点：%r' % (t,))


def 是可选(t):
    t = 解析(t)
    return t[0] == '联合' and 空 in t[1]


# ── 匹配 ───────────────────────────────────────────────
def 匹配度(need, have):
    """have 类型的值能否喂进 need 槽位；返回 0.0~1.0 的贴合度。"""
    need, have = 解析(need), 解析(have)
    return _匹配(need, have)


def _匹配(need, have):
    if need == have:
        return 1.0
    if need == 任意 or have == 任意:
        return _渐进

    # have 是联合：每一支都必须接得上（最坏情况才安全）
    if have[0] == '联合':
        分 = [_匹配(need, h) for h in have[1]]
        return min(分) if 分 else 0.0

    # need 是联合：命中任一支即可
    if need[0] == '联合':
        分 = [_匹配(n, have) for n in need[1]]
        best = max(分) if 分 else 0.0
        return min(best, _联合分支) if best > 0 else 0.0

    if need[0] != have[0]:
        return 0.0
    if need[0] == '列表':
        return _匹配(need[1], have[1])          # 协变
    if need[0] == '字典':
        k, v = _匹配(need[1], have[1]), _匹配(need[2], have[2])
        return min(k, v)
    return 0.0


def 可接纳(need, have):
    return 匹配度(need, have) > 0.0


def 精确(need, have):
    return 匹配度(need, have) >= 1.0


# ── 值推断 ─────────────────────────────────────────────
def 推断(值):
    """从段言字面量文本推断类型，如 "[1, 2, 3]" -> 列表[数]。"""
    s = (值 or '').strip()
    if not s:
        return 任意
    if s.startswith('[') and s.endswith(']'):
        内 = s[1:-1].strip()
        if not 内:
            return ('列表', 任意)
        元 = [推断(x) for x in _切顶层逗号(内)]
        统一 = 归一联合(元)
        return ('列表', 统一)
    if s.startswith('"') or s.startswith("'"):
        return 文本
    if s in ('真', '假'):
        return 逻辑
    try:
        float(s)
        return 数
    except ValueError:
        return 文本


# ── 契约读写辅助 ───────────────────────────────────────
def 入参类型(块, i=0):
    ins = (块 or {}).get('输入') or []
    if i >= len(ins):
        return None
    return 解析(ins[i].get('类型'))


def 出参类型(块):
    out = (块 or {}).get('输出') or {}
    if isinstance(out, list):
        out = out[0] if out else {}
    return 解析(out.get('类型') if isinstance(out, dict) else out)


def 校验契约(块):
    """检查一个索引条目的类型标注是否合法，返回问题列表（空=合法）。"""
    问题 = []
    for i, p in enumerate((块.get('输入') or [])):
        try:
            解析(p.get('类型'))
        except 类型错误 as e:
            问题.append('输入[%d] %s' % (i, e))
    out = 块.get('输出')
    if isinstance(out, dict):
        try:
            解析(out.get('类型'))
        except 类型错误 as e:
            问题.append('输出 %s' % e)
    return 问题


if __name__ == '__main__':
    用例 = [
        ('列表[数]', '列表[数]', 1.0),
        ('列表[数]', '列表[文本]', 0.0),
        ('列表[数]', '列表', 0.6),
        ('列表', '列表[数]', 0.6),
        ('数', '数', 1.0),
        ('数', '文本', 0.0),
        ('可选[数]', '数', 0.95),
        ('可选[数]', '空', 0.95),
        ('数', '可选[数]', 0.0),
        ('数|文本', '文本', 0.95),
        ('字典[文本, 数]', '字典[文本, 数]', 1.0),
        ('字典[文本, 数]', '字典[文本, 文本]', 0.0),
        ('任意', '列表[数]', 0.6),
    ]
    坏 = 0
    for need, have, want in 用例:
        got = 匹配度(need, have)
        ok = abs(got - want) < 1e-9
        坏 += 0 if ok else 1
        print('%s  匹配度(%s, %s) = %.2f  期望 %.2f' %
              ('OK ' if ok else 'FAIL', need, have, got, want))
    print('\n格式化往返：')
    for s in ('列表[数]', '可选[文本]', '字典[文本, 列表[数]]', '数|文本', '列表'):
        print('  %-18s -> %s' % (s, 格式化(解析(s))))
    print('\n推断：')
    for s in ('[1, 2, 3]', '["a", "b"]', '3.14', '"hi"', '[]', '真'):
        print('  %-12s -> %s' % (s, 格式化(推断(s))))
    raise SystemExit(1 if 坏 else 0)
