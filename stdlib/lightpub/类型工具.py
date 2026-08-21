"""
类型工具 — lightpub 桥接模块

基于 Python 内置类型系统封装，函数名对齐上游 duanpub（段言时期）packages/类型工具/源.duan。

上游 duanpub 原始包通过 C FFI 实现运行时类型检查，
本桥接模块用 Python 内置 isinstance/type 等替代，提供等价的类型检查与转换功能。
"""


# =============================================================================
# 字符映射
# =============================================================================

def 获取数字字符映射():
    """获取数字字符到数值的映射字典"""
    return {str(i): i for i in range(10)}


def 获取数字到字符():
    """获取数值到字符的映射字典"""
    return {i: str(i) for i in range(10)}


# =============================================================================
# 类型检查
# =============================================================================

def 型别检查(值):
    """获取值的类型名称"""
    t = type(值)
    return t.__name__


def 是整数(值):
    """判断是否为整数"""
    return isinstance(值, int) and not isinstance(值, bool)


def 是浮点数(值):
    """判断是否为浮点数"""
    return isinstance(值, float)


def 是字符串(值):
    """判断是否为字符串"""
    return isinstance(值, str)


def 是布尔(值):
    """判断是否为布尔值"""
    return isinstance(值, bool)


def 是列表(值):
    """判断是否为列表"""
    return isinstance(值, list)


def 是字典(值):
    """判断是否为字典"""
    return isinstance(值, dict)


def 是空(值):
    """判断值是否为空（None, 空字符串, 空列表, 空字典）"""
    if 值 is None:
        return True
    if isinstance(值, (str, list, dict, tuple, set)):
        return len(值) == 0
    return False


# =============================================================================
# 类型转换
# =============================================================================

def 转整数(值):
    """将值转为整数"""
    try:
        return int(值)
    except (ValueError, TypeError) as e:
        raise Exception("转整数失败: " + str(e))


def 字符串转整数(字符串, 基数=10):
    """将字符串转为整数，支持指定基数"""
    try:
        return int(字符串, base=基数)
    except (ValueError, TypeError) as e:
        raise Exception("字符串转整数失败: " + str(e))


def 转浮点数(值):
    """将值转为浮点数"""
    try:
        return float(值)
    except (ValueError, TypeError) as e:
        raise Exception("转浮点数失败: " + str(e))


def 字符串转浮点数(字符串):
    """将字符串转为浮点数"""
    try:
        return float(字符串)
    except (ValueError, TypeError) as e:
        raise Exception("字符串转浮点数失败: " + str(e))


def 转字符串(值):
    """将值转为字符串"""
    try:
        return str(值)
    except Exception as e:
        raise Exception("转字符串失败: " + str(e))


def 整数转字符串(整数):
    """将整数转为字符串"""
    try:
        return str(整数)
    except Exception as e:
        raise Exception("整数转字符串失败: " + str(e))


def 浮点数转字符串(浮点数):
    """将浮点数转为字符串"""
    try:
        return str(浮点数)
    except Exception as e:
        raise Exception("浮点数转字符串失败: " + str(e))


def 转布尔(值):
    """将值转为布尔值"""
    return bool(值)


# =============================================================================
# 可空类型
# =============================================================================

class _Nullable:
    """可空类型"""
    def __init__(self, value=None, has_value=False):
        self._value = value
        self._has_value = has_value

    def has_value(self):
        return self._has_value

    def get_value(self):
        return self._value


def 可空(值=None):
    """创建一个可空值"""
    if 值 is None:
        return _Nullable(has_value=False)
    return _Nullable(value=值, has_value=True)


def 可空_有值(nullable):
    """检查可空是否有值"""
    if not isinstance(nullable, _Nullable):
        raise Exception("可空_有值失败: 输入不是可空类型")
    return nullable.has_value()


def 可空_取值(nullable, 默认值=None):
    """获取可空的值，无值时返回默认值"""
    if not isinstance(nullable, _Nullable):
        return 默认值
    if nullable.has_value():
        return nullable.get_value()
    return 默认值


def 可空_或缺省(nullable, 默认值):
    """可空取值或返回默认值"""
    return 可空_取值(nullable, 默认值)


def 可空_或计算(nullable, 计算函数):
    """可空取值或执行计算函数"""
    if not isinstance(nullable, _Nullable):
        return 计算函数()
    if nullable.has_value():
        return nullable.get_value()
    return 计算函数()


# =============================================================================
# 类型匹配
# =============================================================================

def 型别配(值, 类型映射):
    """
    根据值的类型匹配执行对应的处理函数。
    类型映射: {类型名: 处理函数, ...}
    """
    type_name = type(值).__name__
    handler = 类型映射.get(type_name)
    if handler:
        return handler(值)
    # 尝试匹配 'default'
    handler = 类型映射.get('default')
    if handler:
        return handler(值)
    raise Exception("型别配失败: 未找到匹配的类型 " + type_name + " 和默认处理")