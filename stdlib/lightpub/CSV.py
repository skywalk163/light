"""
CSV — duanpub 桥接模块

基于 Python csv 库封装，函数名对齐 duanpub/packages/CSV/源.duan。

duanpub 原始包通过 C FFI 实现自研 CSV 解析器，
本桥接模块用 Python csv 模块替代，提供等价的 CSV/TSV 读写功能。
支持类型推断、方言自动检测。
"""

import csv as _csv
import io as _io


# =============================================================================
# 类型推断（对齐 duanpub 源.duan）
# =============================================================================

def inferCellType(值):
    """推断单元格值类型，返回 'int'/'float'/'bool'/'string'"""
    if 值 is None:
        return 'string'
    s = str(值).strip()
    if s == '':
        return 'string'
    # 布尔
    if s.lower() in ('true', 'false'):
        return 'bool'
    # 整数
    try:
        int(s)
        return 'int'
    except ValueError:
        pass
    # 浮点
    try:
        float(s)
        return 'float'
    except ValueError:
        pass
    return 'string'


def convertCellValue(值):
    """将单元格字符串转换为推断后的类型值"""
    类型 = inferCellType(值)
    s = str(值).strip() if 值 is not None else ''
    if 类型 == 'bool':
        return s.lower() == 'true'
    if 类型 == 'int':
        return int(s)
    if 类型 == 'float':
        return float(s)
    return s


# =============================================================================
# 解析函数
# =============================================================================

def parseCSV(文本, 分隔符=',', 有表头=True):
    """解析 CSV 文本，返回二维列表（含表头）"""
    if not 文本:
        return []
    reader = _csv.reader(_io.StringIO(文本), delimiter=分隔符)
    return [row for row in reader]


def parseCSVFile(文件路径, 分隔符=',', 有表头=True):
    """解析 CSV 文件，返回二维列表"""
    if not 文件路径:
        raise Exception("parseCSVFile失败: 文件路径为空")
    try:
        with open(文件路径, 'r', encoding='utf-8', newline='') as f:
            reader = _csv.reader(f, delimiter=分隔符)
            return [row for row in reader]
    except FileNotFoundError:
        raise Exception("parseCSVFile失败: 文件不存在 " + 文件路径)
    except Exception as e:
        raise Exception("parseCSVFile失败: " + str(e))


def parseCSVStream(文件对象, 分隔符=','):
    """从文件流解析 CSV，返回二维列表"""
    reader = _csv.reader(文件对象, delimiter=分隔符)
    return [row for row in reader]


def autoDetectDelimiter(文本):
    """自动检测 CSV 分隔符，返回分隔符字符"""
    if not 文本:
        return ','
    候选 = [',', '\t', ';', '|']
    最佳 = ','
    最佳得分 = -1
    第一行 = 文本.split('\n')[0] if '\n' in 文本 else 文本
    for d in 候选:
        得分 = 第一行.count(d)
        if 得分 > 最佳得分:
            最佳得分 = 得分
            最佳 = d
    return 最佳


# =============================================================================
# 转换函数
# =============================================================================

def toDictList(数据, 有表头=True):
    """将二维列表转为字典列表（第一行作为表头）"""
    if not 数据:
        return []
    if 有表头:
        表头 = 数据[0]
        行 = 数据[1:]
    else:
        表头 = ['列' + str(i) for i in range(len(数据[0]))]
        行 = 数据
    结果 = []
    for row in 行:
        项 = {}
        for i, col in enumerate(表头):
            项[col] = row[i] if i < len(row) else ''
        结果.append(项)
    return 结果


def to2DArray(字典列表, 表头=None):
    """将字典列表转为二维列表（含表头行）"""
    if not 字典列表:
        return []
    if 表头 is None:
        表头 = list(字典列表[0].keys())
    结果 = [表头[:]]
    for 项 in 字典列表:
        行 = [str(项.get(col, '')) for col in 表头]
        结果.append(行)
    return 结果


def getColumn(数据, 列名或索引):
    """获取指定列的所有值（支持列名或索引）"""
    if not 数据:
        return []
    # 如果是字典列表
    if 数据 and isinstance(数据[0], dict):
        return [项.get(列名或索引) for 项 in 数据]
    # 如果是二维列表，列名或索引为整数索引
    if isinstance(列名或索引, int):
        return [row[列名或索引] if 列名或索引 < len(row) else '' for row in 数据]
    return []


# =============================================================================
# 序列化函数
# =============================================================================

def serializeCSV(数据, 分隔符=',', 有表头=True):
    """将二维列表序列化为 CSV 文本"""
    if not 数据:
        return ''
    output = _io.StringIO()
    writer = _csv.writer(output, delimiter=分隔符, lineterminator='\n')
    for row in 数据:
        writer.writerow(row)
    return output.getvalue().rstrip('\n')


def serializeCSVFile(文件路径, 数据, 分隔符=',', 有表头=True):
    """将二维列表序列化并写入 CSV 文件"""
    if not 文件路径:
        raise Exception("serializeCSVFile失败: 文件路径为空")
    try:
        with open(文件路径, 'w', encoding='utf-8', newline='') as f:
            writer = _csv.writer(f, delimiter=分隔符, lineterminator='\n')
            for row in 数据:
                writer.writerow(row)
    except OSError as e:
        raise Exception("serializeCSVFile失败: " + str(e))


# =============================================================================
# 便捷函数（中文名）
# =============================================================================

def 解析CSV(文本, 分隔符=','):
    """解析 CSV 文本，返回二维列表"""
    return parseCSV(文本, 分隔符=分隔符)


def 解析CSV文件(文件路径, 分隔符=','):
    """解析 CSV 文件，返回二维列表"""
    return parseCSVFile(文件路径, 分隔符=分隔符)


def 序列化CSV(数据, 分隔符=','):
    """将二维列表序列化为 CSV 文本"""
    return serializeCSV(数据, 分隔符=分隔符)


def 序列化CSV文件(文件路径, 数据, 分隔符=','):
    """将二维列表序列化并写入 CSV 文件"""
    return serializeCSVFile(文件路径, 数据, 分隔符=分隔符)


def 自动检测分隔符(文本):
    """自动检测 CSV 分隔符"""
    return autoDetectDelimiter(文本)


def 转字典列表(数据, 有表头=True):
    """将二维列表转为字典列表"""
    return toDictList(数据, 有表头=有表头)


def 转二维数组(字典列表, 表头=None):
    """将字典列表转为二维列表"""
    return to2DArray(字典列表, 表头=表头)


def 获取列(数据, 列名或索引):
    """获取指定列的所有值"""
    return getColumn(数据, 列名或索引)


def 推断单元格类型(值):
    """推断单元格值类型"""
    return inferCellType(值)


def 转换单元格值(值):
    """将单元格字符串转换为推断后的类型值"""
    return convertCellValue(值)
