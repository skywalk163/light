"""
正则工具增强模块 - 对 stdlib/正则表达式.light 的中文场景补充
新增能力：
1. 身份证校验（GB 11643-1999：18 位 + 校验位算法 + 15 位升级到 18 位 + 性别/生日/地区提取）
2. 中国车牌号码校验（民用车牌/新能源车牌/教练车/警车/使馆车 基本格式 + 校验位可选）
3. 银行卡号校验（Luhn 算法：所有通用信用卡/借记卡通用模 10 校验）
4. 文本抽取：批量抽取中文姓名 / 手机号 / 邮箱 / 身份证 / URL / 车牌 / 银行卡号
"""
from __future__ import annotations
import re as _re
from typing import List, Dict, Any, Optional

# ==========================================================
# 1. 身份证 (GB11643-1999) — 18位含校验码算法；15位自动升级18位并校验
# ==========================================================

_ID18_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_ID18_CHECK = ('1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2')
# 中国省级 + 直辖市 + 自治区 + 港澳台常用前缀（简化版，6位完整 GB/T 2260 太全；这里只覆盖首两位）
_ID_PROV_PREFIXES = frozenset(
    '11,12,13,14,15,21,22,23,31,32,33,34,35,36,37,41,42,43,44,45,46,'
    '50,51,52,53,54,61,62,63,64,65,71,81,82,91'.split(',')
)
_ID18_PAT = _re.compile(r'^\d{17}[\dXx]$')
_ID15_PAT = _re.compile(r'^\d{15}$')


def _id18_checksum(body17: str) -> str:
    assert len(body17) == 17 and body17.isdigit()
    s = sum(int(body17[i]) * _ID18_WEIGHTS[i] for i in range(17))
    return _ID18_CHECK[s % 11]


def 升级15位到18位(id15: str) -> str:
    # 别名：升级15位身份证到18位（在文件末尾定义）
    id15 = id15.strip()
    if not _ID15_PAT.match(id15):
        raise ValueError("15位身份证格式错误")
    body = id15[:6] + '19' + id15[6:]  # 19xx（老身份证几乎都是 19xx 出生）
    return body + _id18_checksum(body)


def 校验身份证(id_card: str, 严格地区: bool = True) -> Dict[str, Any]:
    """返回 dict：{是否合法, 原因, 版本, 地区码前2位, 生日YYYYMMDD, 性别:'男'/'女', 校验位}"""
    s = id_card.strip().upper()
    out: Dict[str, Any] = {'是否合法': False, '原因': '', '版本': 0, '地区前缀': '',
                           '生日': '', '性别': '', '校验位': '', '原始': s}
    if not _ID18_PAT.match(s):
        if _ID15_PAT.match(s):
            try:
                s = 升级15位到18位(s)
                out['版本'] = 15
            except Exception as e:
                out['原因'] = '15位身份证升级失败: ' + str(e)
                return out
        else:
            out['原因'] = '格式不匹配（18位数字或17位+X）'
            return out
    else:
        out['版本'] = 18
    # 1) 地区码前两位
    prov = s[:2]
    out['地区前缀'] = prov
    if 严格地区 and prov not in _ID_PROV_PREFIXES:
        out['原因'] = f'地区前缀 {prov} 不属于已知省级代码'
        return out
    # 2) 生日
    ymd = s[6:14]
    y, mo, d = int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8])
    try:
        from datetime import date as _date
        _date(y, mo, d)
        out['生日'] = f'{y:04d}-{mo:02d}-{d:02d}'
    except ValueError:
        out['原因'] = f'生日不合法: {y}-{mo}-{d}'
        return out
    # 3) 校验位
    expect = _id18_checksum(s[:17])
    out['校验位'] = s[-1]
    if s[-1] != expect:
        out['原因'] = f'校验位应为 {expect}，实际 {s[-1]}'
        return out
    # 4) 性别：第17位奇数=男，偶数=女
    out['性别'] = '男' if int(s[16]) % 2 == 1 else '女'
    out['是否合法'] = True
    return out


# ==========================================================
# 2. 中国车牌号码
# ==========================================================

# 民用: 京A·12345  新能源: 京AD12345 / 京A12345D  教练车: 京A·1234学  警车: 京·A1234警  使馆: 使123·4567
_PLATE_PAT = _re.compile(
    r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{4,6}[学警港澳挂使领]?$'
)
# 更宽松的匹配（允许没有 · 分隔符）——实际校验里先去掉分隔符再处理
_PLATE_SEP = _re.compile(r'[·\-.\s]')


def 校验车牌(plate: str) -> Dict[str, Any]:
    out = {'是否合法': False, '类型': '未知', '省份简称': '', '字母': '', '号码': '', '原因': ''}
    p = _PLATE_SEP.sub('', plate.strip()).upper()
    if len(p) < 7 or len(p) > 9:
        out['原因'] = f'长度应为 7~9（实际 {len(p)}）'
        return out
    if not _PLATE_PAT.match(p):
        out['原因'] = '格式不匹配车牌规则'
        return out
    prov = p[0]
    letter = p[1]
    num = p[2:]
    out['省份简称'] = prov
    out['字母'] = letter
    out['号码'] = num
    # 分类
    if prov == '使' or num.endswith('使') or num.endswith('领'):
        out['类型'] = '使领馆'
    elif num.endswith('警'):
        out['类型'] = '警用'
    elif num.endswith('学'):
        out['类型'] = '教练'
    elif len(p) == 8:
        out['类型'] = '新能源小型'
    else:
        out['类型'] = '民用小型'
    out['是否合法'] = True
    return out


# ==========================================================
# 3. 银行卡号 Luhn 校验
# ==========================================================

def 校验银行卡(card_no: str) -> Dict[str, Any]:
    s = _re.sub(r'\D', '', card_no)
    out = {'是否合法': False, '长度': len(s), '号': s, '校验和通过': False, '品牌': '未知', '原因': ''}
    n = len(s)
    if n < 12 or n > 19:
        out['原因'] = f'银行卡号长度应为 12~19（实际 {n}）'
        return out
    if not s.isdigit():
        out['原因'] = '不是纯数字'
        return out
    # Luhn 模 10
    total = 0
    reverse = s[::-1]
    for i, ch in enumerate(reverse):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d >= 10:
                d -= 9
        total += d
    ok = (total % 10 == 0)
    out['校验和通过'] = ok
    if not ok:
        out['原因'] = 'Luhn 校验和失败（常见于手输/号码错误）'
        return out
    # 常见卡组织前缀
    head = s[:6]
    h1, h2, h3 = s[:1], s[:2], s[:4]
    if h2 in ('62',):
        out['品牌'] = '银联 UnionPay'
    elif h2 in ('34', '37'):
        out['品牌'] = '美国运通 AMEX'
    elif h3 in ('4026', '4508', '4844', '4913', '4917') or head[:2] in ('41', '42'):
        out['品牌'] = 'Visa Electron / Visa'
    elif h1 == '4':
        out['品牌'] = 'Visa'
    elif ('51' <= h2 <= '55') or h3 in ('222', '272') or (h3.startswith('22') or h3.startswith('23') or h3.startswith('24') or h3.startswith('25') or h3.startswith('26') or h3.startswith('27')):
        out['品牌'] = '万事达 Mastercard'
    elif h3 in ('6011', '644', '645', '646', '647', '648', '649', '65'):
        out['品牌'] = '发现 Discover'
    out['是否合法'] = True
    return out


# ==========================================================
# 4. 文本抽取
# ==========================================================

_MOBILE_PAT = _re.compile(r'(?<!\d)(1[3-9]\d{9})(?!\d)')
_EMAIL_PAT = _re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
_ID18_FIND = _re.compile(r'(?<!\d)(\d{17}[\dXx]|\d{15})(?!\d)')
_URL_PAT = _re.compile(r'https?://[^\s\u4e00-\u9fa5，。；、"<>]+|www\.[^\s\u4e00-\u9fa5，。；、"<>]+')
# 中文姓名：2~4 个中文汉字（不包含生僻字覆盖，通常够用）
_NAME_PAT = _re.compile(r'[\u4e00-\u9fa5]{2,3}')
# 车牌（宽松）：1汉字 + 1字母 + 5~7位字母数字，允许末尾 学/警/港/澳
_PLATE_FIND = _re.compile(r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{4,7}[学警港澳]?')
# 银行卡号（宽松 12~19 位数字，允许 4 位分组空格）
_BANKCARD_FIND = _re.compile(r'(?<!\d)(?:\d[ ]?){11,20}\d(?!\d)')


def _extract(pat: _re.Pattern, text: str) -> List[str]:
    return [m for m in pat.findall(text or '') if m]


def 抽取手机号(text: str) -> List[str]:
    return _extract(_MOBILE_PAT, text)


def 抽取邮箱(text: str) -> List[str]:
    return _extract(_EMAIL_PAT, text)


def 抽取身份证(text: str, 需校验: bool = True) -> List[Dict[str, Any]]:
    cands = _extract(_ID18_FIND, text)
    out = []
    for c in cands:
        info = 校验身份证(c, 严格地区=False)
        if not 需校验 or info['是否合法']:
            info['原文'] = c
            out.append(info)
    return out


def 抽取URL(text: str) -> List[str]:
    return _extract(_URL_PAT, text)


def 抽取姓名(text: str, 排除停用词: Optional[List[str]] = None) -> List[str]:
    """简单姓名抽取：2~3字中文。会排除「但是/因为/所以/公司/政府」这类停用词组合。"""
    stop = set(排除停用词 or [])
    default_stop = {'但是', '因为', '所以', '如果', '或者', '而且', '并且', '虽然', '然后', '就是',
                    '已经', '知道', '什么', '怎么', '公司', '政府', '北京', '上海', '深圳', '广州',
                    '中国', '大家', '自己', '然后', '现在', '可以', '需要', '问题', '时间', '时候',
                    '今天', '昨天', '明天', '地方', '东西', '人民', '国家', '工作', '学习', '生活'}
    stop |= default_stop
    res = []
    for m in _NAME_PAT.findall(text or ''):
        # 从每个匹配中提取所有 2-3 字子串，避免贪婪匹配吞掉 2 字姓名
        for i in range(len(m)):
            for j in range(i + 2, min(i + 4, len(m) + 1)):
                sub = m[i:j]
                if sub in stop:
                    continue
                if sub not in res:
                    res.append(sub)
    return res


def 抽取车牌(text: str, 必须合法: bool = True) -> List[Dict[str, Any]]:
    cands = _PLATE_FIND.findall(text or '')
    out = []
    for c in cands:
        info = 校验车牌(c)
        if not 必须合法 or info['是否合法']:
            info['原文'] = c
            out.append(info)
    return out


def 抽取银行卡(text: str, 必须Luhn合法: bool = True) -> List[Dict[str, Any]]:
    cands = _BANKCARD_FIND.findall(text or '')
    out = []
    for c in cands:
        info = 校验银行卡(c)
        if not 必须Luhn合法 or info['是否合法']:
            info['原文'] = c
            out.append(info)
    return out


# 别名 — 与 .light 文件导出名保持一致
升级15位身份证到18位 = 升级15位到18位
