"""
光明标准库 - 随机数据模块

提供随机数据生成函数：字符串、整数、UUID、密码、姓名、邮箱
"""

import random as _random
import string as _string
import uuid as _uuid


# 常见中文姓氏
_姓氏库 = [
    '王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
    '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗',
    '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧',
    '程', '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕',
    '苏', '卢', '蒋', '蔡', '贾', '丁', '魏', '薛', '叶', '阎',
    '余', '潘', '杜', '戴', '夏', '钟', '汪', '田', '任', '姜',
    '范', '方', '石', '姚', '谭', '廖', '邹', '熊', '金', '陆',
    '郝', '孔', '白', '崔', '康', '毛', '邱', '秦', '江', '史',
]

# 常见中文名字用字
_名字库 = [
    '伟', '芳', '娜', '秀英', '敏', '静', '丽', '强', '磊', '军',
    '洋', '勇', '艳', '杰', '娟', '涛', '明', '超', '秀兰', '霞',
    '平', '刚', '桂英', '兰', '鹏', '辉', '玲', '志强', '波', '静',
    '建国', '建华', '志强', '建军', '国华', '国英', '国平', '国栋',
    '秀珍', '秀英', '秀芳', '凤英', '凤兰', '金兰', '玉兰', '玉珍',
    '丹', '华', '红', '梅', '兰', '菊', '莲', '莉', '萍', '颖',
    '辉', '锋', '钢', '铮', '鑫', '鹏', '飞', '翔', '龙', '凤',
    '浩然', '浩宇', '博文', '博宇', '子轩', '子涵', '思远', '思雨',
    '欣怡', '欣悦', '梦琪', '梦瑶', '梓涵', '梓萱', '一诺', '依诺',
]

# 常用邮箱域名
_邮箱域名库 = [
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
    'qq.com', '163.com', '126.com', 'sina.com', 'sohu.com',
]


def 随机字符串(长度: int = 8, 字符集: str = '字母数字') -> str:
    """
    生成随机字符串

    参数:
        长度: 字符串长度
        字符集: '字母数字' / '字母' / '数字' / 'ascii'

    返回:
        随机字符串
    """
    if 字符集 == '字母数字':
        chars = _string.ascii_letters + _string.digits
    elif 字符集 == '字母':
        chars = _string.ascii_letters
    elif 字符集 == '数字':
        chars = _string.digits
    elif 字符集 == 'ascii':
        chars = _string.printable
    else:
        chars = 字符集

    return ''.join(_random.choice(chars) for _ in range(长度))


def 随机整数(最小值: int, 最大值: int) -> int:
    """
    生成随机整数 [最小值, 最大值]

    参数:
        最小值: 下界
        最大值: 上界

    返回:
        随机整数
    """
    return _random.randint(最小值, 最大值)


def 随机UUID() -> str:
    """
    生成 UUID

    返回:
        UUID 字符串
    """
    return str(_uuid.uuid4())


def 随机密码(长度: int = 16) -> str:
    """
    生成随机密码（包含大小写字母、数字、特殊字符）

    参数:
        长度: 密码长度

    返回:
        随机密码
    """
    if 长度 < 4:
        raise RuntimeError("密码长度至少为 4")

    # 确保包含每种字符
    chars = (
        _string.ascii_lowercase +
        _string.ascii_uppercase +
        _string.digits +
        _string.punctuation
    )

    # 随机生成密码
    password = [
        _random.choice(_string.ascii_lowercase),
        _random.choice(_string.ascii_uppercase),
        _random.choice(_string.digits),
        _random.choice(_string.punctuation),
    ]

    # 填充剩余长度
    for _ in range(长度 - 4):
        password.append(_random.choice(chars))

    # 打乱顺序
    _random.shuffle(password)
    return ''.join(password)


def 随机姓名() -> str:
    """
    生成随机姓名

    返回:
        随机中文姓名
    """
    姓 = _random.choice(_姓氏库)

    # 30% 概率生成双字名
    if _random.random() < 0.3:
        名 = _random.choice(_名字库) + _random.choice(_名字库)
    else:
        名 = _random.choice(_名字库)

    return 姓 + 名


def 随机邮箱(域名: str = None) -> str:
    """
    生成随机邮箱

    参数:
        域名: 指定域名，None 时随机选择

    返回:
        随机邮箱地址
    """
    if 域名 is None:
        域名 = _random.choice(_邮箱域名库)

    # 生成随机用户名
    长度 = _random.randint(6, 12)
    用户名 = 随机字符串(长度, '字母数字')

    return f"{用户名}@{域名}"


__all__ = [
    '随机字符串',
    '随机整数',
    '随机UUID',
    '随机密码',
    '随机姓名',
    '随机邮箱',
]
