"""
JSON — duanpub 桥接模块

基于 Python json 库封装，函数名对齐 duanpub/packages/JSON/源.duan。

duanpub 原始包通过 C FFI 实现自研 JSON 解析器，
本桥接模块用 Python json 模块替代，提供等价的 JSON 解析与序列化功能。
函数签名与 duanpub 包保持一致。
"""

import json as _json


# =============================================================================
# 核心解析/序列化函数（对齐 duanpub 源.duan 的 API 设计）
# =============================================================================

def 解析JSON(文本):
    """解析 JSON 字符串，返回 dict/list/str/number/bool/None"""
    if not 文本:
        raise Exception("解析JSON失败: 文本为空")
    try:
        return _json.loads(文本)
    except _json.JSONDecodeError as e:
        raise Exception("解析JSON失败: " + str(e))


def 安全解析JSON(文本):
    """安全解析 JSON 字符串，失败返回 None"""
    if not 文本:
        return None
    try:
        return _json.loads(文本)
    except (ValueError, TypeError):
        return None


def 解析JSON文件(文件路径):
    """从文件读取并解析 JSON，返回解析后的值"""
    if not 文件路径:
        raise Exception("解析JSON文件失败: 文件路径为空")
    try:
        with open(文件路径, 'r', encoding='utf-8') as f:
            return _json.load(f)
    except FileNotFoundError:
        raise Exception("解析JSON文件失败: 文件不存在 " + 文件路径)
    except _json.JSONDecodeError as e:
        raise Exception("解析JSON文件失败: " + str(e))


def 序列化JSON(值, 缩进=None, 确保ASCII=False):
    """将值序列化为 JSON 字符串"""
    try:
        return _json.dumps(值, indent=缩进, ensure_ascii=确保ASCII)
    except (TypeError, ValueError) as e:
        raise Exception("序列化JSON失败: " + str(e))


def 序列化JSON文件(文件路径, 值, 缩进=None, 确保ASCII=False):
    """将值序列化为 JSON 并写入文件"""
    if not 文件路径:
        raise Exception("序列化JSON文件失败: 文件路径为空")
    try:
        with open(文件路径, 'w', encoding='utf-8') as f:
            _json.dump(值, f, indent=缩进, ensure_ascii=确保ASCII)
    except (TypeError, ValueError, OSError) as e:
        raise Exception("序列化JSON文件失败: " + str(e))


# =============================================================================
# 格式化与压缩
# =============================================================================

def JSON美化(值, 缩进=2):
    """美化 JSON 输出（带缩进）"""
    return _json.dumps(值, indent=缩进, ensure_ascii=False)


def JSON压缩(文本):
    """压缩 JSON 字符串（去除空白）"""
    data = 解析JSON(文本)
    return _json.dumps(data, ensure_ascii=False, separators=(',', ':'))


# =============================================================================
# 合并与比较
# =============================================================================

def JSON合并(基础, *其他):
    """合并多个 JSON 对象（浅合并），返回新 dict"""
    if not isinstance(基础, dict):
        raise Exception("JSON合并失败: 基础值不是对象")
    result = dict(基础)
    for other in 其他:
        if not isinstance(other, dict):
            raise Exception("JSON合并失败: 待合并值不是对象")
        result.update(other)
    return result


def 深合并(基础, *其他):
    """深度合并多个 JSON 对象，返回新 dict"""
    if not isinstance(基础, dict):
        raise Exception("深合并失败: 基础值不是对象")
    result = dict(基础)
    for other in 其他:
        if not isinstance(other, dict):
            raise Exception("深合并失败: 待合并值不是对象")
        for key, value in other.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = 深合并(result[key], value)
            else:
                result[key] = value
    return result


def JSON深度相等(值1, 值2):
    """比较两个 JSON 值是否深度相等"""
    return _json.dumps(值1, sort_keys=True, ensure_ascii=False) == \
           _json.dumps(值2, sort_keys=True, ensure_ascii=False)


# =============================================================================
# 类型判断
# =============================================================================

def JSON类型(值):
    """获取 JSON 值的类型名称（对象/数组/字符串/数字/布尔/空）"""
    if isinstance(值, dict):
        return '对象'
    elif isinstance(值, list):
        return '数组'
    elif isinstance(值, str):
        return '字符串'
    elif isinstance(值, bool):
        return '布尔'
    elif isinstance(值, (int, float)):
        return '数字'
    elif 值 is None:
        return '空'
    return '未知'


def 取值形态(值):
    """取值形态（同 JSON类型，返回类型名称）"""
    return JSON类型(值)


def 是JSON对象(值):
    """判断是否为 JSON 对象（dict）"""
    return isinstance(值, dict)


def 是JSON数组(值):
    """判断是否为 JSON 数组（list）"""
    return isinstance(值, list)


def 是JSON字符串(值):
    """判断是否为 JSON 字符串"""
    return isinstance(值, str)


def 是JSON数字(值):
    """判断是否为 JSON 数字"""
    return isinstance(值, (int, float)) and not isinstance(值, bool)


def 是JSON布尔(值):
    """判断是否为 JSON 布尔值"""
    return isinstance(值, bool)


# =============================================================================
# JSON Pointer（简化实现）
# =============================================================================

def JSON指针获取(数据, 指针):
    """按 JSON Pointer 路径获取值，路径如 /a/b/0"""
    if not 指针:
        return 数据
    if 指针.startswith('/'):
        指针 = 指针[1:]
    if not 指针:
        return 数据
    tokens = 指针.split('/')
    当前 = 数据
    for token in tokens:
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(当前, dict):
            if token not in 当前:
                raise Exception("JSON指针获取失败: 路径不存在 " + token)
            当前 = 当前[token]
        elif isinstance(当前, list):
            try:
                idx = int(token)
            except ValueError:
                raise Exception("JSON指针获取失败: 数组索引无效 " + token)
            if idx < 0 or idx >= len(当前):
                raise Exception("JSON指针获取失败: 数组索引越界 " + token)
            当前 = 当前[idx]
        else:
            raise Exception("JSON指针获取失败: 无法穿透非容器值")
    return 当前


def JSON指针设置(数据, 指针, 值):
    """按 JSON Pointer 路径设置值，返回修改后的数据"""
    if not 指针:
        return 值
    if 指针.startswith('/'):
        指针 = 指针[1:]
    tokens = 指针.split('/')
    if not tokens or tokens == ['']:
        return 值
    _set_pointer(数据, tokens, 值)
    return 数据


def _set_pointer(当前, tokens, 值):
    """内部：递归设置指针值"""
    token = tokens[0].replace('~1', '/').replace('~0', '~')
    if len(tokens) == 1:
        if isinstance(当前, dict):
            当前[token] = 值
        elif isinstance(当前, list):
            当前[int(token)] = 值
        return
    if isinstance(当前, dict):
        if token not in 当前:
            当前[token] = {}
        _set_pointer(当前[token], tokens[1:], 值)
    elif isinstance(当前, list):
        _set_pointer(当前[int(token)], tokens[1:], 值)


def JSON指针删除(数据, 指针):
    """按 JSON Pointer 路径删除值，返回修改后的数据"""
    if not 指针:
        return 数据
    if 指针.startswith('/'):
        指针 = 指针[1:]
    tokens = 指针.split('/')
    if not tokens or tokens == ['']:
        return 数据
    _del_pointer(数据, tokens)
    return 数据


def _del_pointer(当前, tokens):
    """内部：递归删除指针值"""
    token = tokens[0].replace('~1', '/').replace('~0', '~')
    if len(tokens) == 1:
        if isinstance(当前, dict) and token in 当前:
            del 当前[token]
        elif isinstance(当前, list):
            idx = int(token)
            if 0 <= idx < len(当前):
                del 当前[idx]
        return
    if isinstance(当前, dict) and token in 当前:
        _del_pointer(当前[token], tokens[1:])
    elif isinstance(当前, list):
        _del_pointer(当前[int(token)], tokens[1:])
