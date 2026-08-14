"""
段言标准库 - JSON 处理模块

提供 JSON 的解析、序列化、验证、查询等功能。
"""

import json
import os
import re
from typing import Any, Optional, List, Dict, Union


def 解析JSON(text: str) -> Any:
    """
    解析 JSON 字符串为段言值（列表/字典/字符串/数字/布尔/空）
    
    参数:
        text: JSON 格式字符串
    
    返回:
        解析后的值
    
    示例:
        解析JSON('{"name": "段言", "version": 1}')  # {'name': '段言', 'version': 1}
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON 解析失败: {e}")


def 序列化JSON(value: Any, 缩进: Optional[int] = None) -> str:
    """
    将段言值序列化为 JSON 字符串
    
    参数:
        value: 要序列化的值（列表、字典、字符串、数字、布尔、空）
        缩进: 缩进空格数，None 为紧凑输出
    
    返回:
        JSON 格式字符串
    
    示例:
        序列化JSON({'name': '段言'})       # '{"name": "段言"}'
        序列化JSON({'name': '段言'}, 2)    # 格式化输出
    """
    try:
        if 缩进 is not None:
            return json.dumps(value, ensure_ascii=False, indent=缩进)
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise RuntimeError(f"JSON 序列化失败: {e}")


def 美化JSON(value: Any) -> str:
    """
    美化 JSON 输出（带缩进）
    
    参数:
        value: 要格式化的值
    
    返回:
        美化后的 JSON 字符串
    """
    return 序列化JSON(value, 缩进=2)


def 读取JSON文件(path: str) -> Any:
    """
    从文件读取并解析 JSON
    
    参数:
        path: 文件路径
    
    返回:
        解析后的值
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"文件不存在: '{path}'")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON 文件解析失败 '{path}': {e}")


def 写入JSON文件(path: str, value: Any, 美化: bool = False) -> None:
    """
    将值序列化为 JSON 写入文件
    
    参数:
        path: 文件路径
        value: 要序列化的值
        美化: 是否格式化输出
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2 if 美化 else None)
    except Exception as e:
        raise RuntimeError(f"写入 JSON 文件失败 '{path}': {e}")


def JSON转Python(text: str) -> Any:
    """
    JSON字符串转Python对象（别名）
    
    参数:
        text: JSON格式字符串
    
    返回:
        Python对象
    """
    return 解析JSON(text)


def Python转JSON(value: Any, 缩进: Optional[int] = None) -> str:
    """
    Python对象转JSON字符串（别名）
    
    参数:
        value: Python对象
        缩进: 缩进空格数
    
    返回:
        JSON格式字符串
    """
    return 序列化JSON(value, 缩进)


def JSON转字典(text: str) -> dict:
    """
    JSON字符串转字典
    
    参数:
        text: JSON格式字符串
    
    返回:
        字典
    """
    result = 解析JSON(text)
    if not isinstance(result, dict):
        raise RuntimeError("JSON内容不是字典")
    return result


def JSON转列表(text: str) -> list:
    """
    JSON字符串转列表
    
    参数:
        text: JSON格式字符串
    
    返回:
        列表
    """
    result = 解析JSON(text)
    if not isinstance(result, list):
        raise RuntimeError("JSON内容不是列表")
    return result


def 验证JSON(text: str) -> bool:
    """
    验证JSON字符串是否有效
    
    参数:
        text: JSON格式字符串
    
    返回:
        有效返回True，无效返回False
    """
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def 验证JSON文件(path: str) -> bool:
    """
    验证JSON文件是否有效
    
    参数:
        path: 文件路径
    
    返回:
        有效返回True，无效返回False
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, FileNotFoundError):
        return False


def JSON合并(base: dict, *others: dict) -> dict:
    """
    合并多个JSON对象（字典）
    
    参数:
        base: 基础字典
        others: 其他字典
    
    返回:
        合并后的字典
    """
    result = dict(base)
    for other in others:
        result.update(other)
    return result


def JSON深合并(base: dict, *others: dict) -> dict:
    """
    深度合并多个JSON对象（字典）
    
    参数:
        base: 基础字典
        others: 其他字典
    
    返回:
        深度合并后的字典
    """
    result = dict(base)
    for other in others:
        for key, value in other.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = JSON深合并(result[key], value)
            else:
                result[key] = value
    return result


def JSON提取值(data, 路径: str, 默认值: Any = None) -> Any:
    """
    从JSON对象中提取值（支持点分隔路径）
    
    参数:
        data: JSON对象（字典）或JSON字符串
        路径: 值的路径，如 "a.b.c"
        默认值: 路径不存在时的默认值
    
    返回:
        提取的值或默认值
    
    示例:
        data = {"a": {"b": {"c": 1}}}
        JSON提取值(data, "a.b.c")  # 1
        JSON提取值(data, "a.x", 0)  # 0
    """
    if isinstance(data, str):
        data = json.loads(data)
    路径列表 = 路径.split('.')
    当前 = data
    try:
        for 键 in 路径列表:
            if isinstance(当前, dict):
                当前 = 当前[键]
            elif isinstance(当前, list):
                当前 = 当前[int(键)]
            else:
                return 默认值
        return 当前
    except (KeyError, IndexError, TypeError):
        return 默认值


def JSON查找(data: dict, 键: str) -> List[Any]:
    """
    在JSON对象中递归查找所有匹配的键的值
    
    参数:
        data: JSON对象（字典）
        键: 要查找的键
    
    返回:
        匹配值的列表
    """
    结果 = []
    
    def _递归查找(当前):
        if isinstance(当前, dict):
            for k, v in 当前.items():
                if k == 键:
                    结果.append(v)
                _递归查找(v)
        elif isinstance(当前, list):
            for 元素 in 当前:
                _递归查找(元素)
    
    _递归查找(data)
    return 结果


def JSON过滤(data: list, 条件: dict) -> list:
    """
    根据条件过滤JSON列表
    
    参数:
        data: JSON列表
        条件: 过滤条件字典
    
    返回:
        过滤后的列表
    
    示例:
        data = [{"name": "甲", "age": 20}, {"name": "乙", "age": 30}]
        JSON过滤(data, {"age": 30})  # [{"name": "乙", "age": 30}]
    """
    结果 = []
    for 项 in data:
        匹配 = True
        for 键, 值 in 条件.items():
            if 项.get(键) != 值:
                匹配 = False
                break
        if 匹配:
            结果.append(项)
    return 结果


def JSON映射(data: list, 函数: callable) -> list:
    """
    对JSON列表中的每个元素应用函数
    
    参数:
        data: JSON列表
        函数: 应用的函数
    
    返回:
        映射后的列表
    """
    return [函数(项) for 项 in data]


def JSON聚合(data: list, 键: str, 聚合函数: callable = sum) -> Any:
    """
    对JSON列表中指定键的值进行聚合
    
    参数:
        data: JSON列表
        键: 要聚合的键
        聚合函数: 聚合函数，默认为sum
    
    返回:
        聚合结果
    """
    值列表 = [项.get(键) for 项 in data if 键 in 项]
    return 聚合函数(值列表)


def JSON分组(data: list, 键: str) -> dict:
    """
    根据指定键对JSON列表进行分组
    
    参数:
        data: JSON列表
        键: 分组键
    
    返回:
        分组后的字典
    
    示例:
        data = [{"name": "甲", "group": "A"}, {"name": "乙", "group": "B"}]
        JSON分组(data, "group")  # {"A": [...], "B": [...]}
    """
    结果 = {}
    for 项 in data:
        分组键 = 项.get(键)
        if 分组键 not in 结果:
            结果[分组键] = []
        结果[分组键].append(项)
    return 结果


def JSON排序(data: list, 键: str, 反向: bool = False) -> list:
    """
    根据指定键对JSON列表进行排序
    
    参数:
        data: JSON列表
        键: 排序键
        反向: 是否反向排序
    
    返回:
        排序后的列表
    """
    return sorted(data, key=lambda x: x.get(键), reverse=反向)


def JSON去重(data: list, 键: str = None) -> list:
    """
    去除JSON列表中的重复元素
    
    参数:
        data: JSON列表
        键: 根据指定键去重，None为完全去重
    
    返回:
        去重后的列表
    """
    if 键 is None:
        seen = set()
        结果 = []
        for 项 in data:
            键值 = json.dumps(项, ensure_ascii=False, sort_keys=True)
            if 键值 not in seen:
                seen.add(键值)
                结果.append(项)
        return 结果
    else:
        seen = set()
        结果 = []
        for 项 in data:
            键值 = 项.get(键)
            if 键值 not in seen:
                seen.add(键值)
                结果.append(项)
        return 结果


def JSON扁平化(data: dict, 前缀: str = '') -> dict:
    """
    将嵌套的JSON对象扁平化
    
    参数:
        data: JSON对象（字典）
        前缀: 键前缀
    
    返回:
        扁平化后的字典
    
    示例:
        data = {"a": {"b": 1}}
        JSON扁平化(data)  # {"a.b": 1}
    """
    结果 = {}
    
    def _扁平化(当前, 路径):
        if isinstance(当前, dict):
            for 键, 值 in 当前.items():
                新路径 = f"{路径}.{键}" if 路径 else 键
                _扁平化(值, 新路径)
        else:
            结果[路径] = 当前
    
    _扁平化(data, 前缀)
    return 结果


def JSON展开(data: dict) -> dict:
    """
    将扁平化的JSON对象展开（反向操作）
    
    参数:
        data: 扁平化的JSON对象（字典）
    
    返回:
        展开后的嵌套字典
    
    示例:
        data = {"a.b": 1}
        JSON展开(data)  # {"a": {"b": 1}}
    """
    结果 = {}
    for 键, 值 in data.items():
        键列表 = 键.split('.')
        当前 = 结果
        for i, k in enumerate(键列表):
            if i == len(键列表) - 1:
                当前[k] = 值
            else:
                if k not in 当前:
                    当前[k] = {}
                当前 = 当前[k]
    return 结果


def JSON转CSV(data, 输出文件: str = None) -> str:
    """
    将JSON列表转换为CSV格式
    
    参数:
        data: JSON列表（字典列表）或JSON字符串
        输出文件: 输出文件路径，None返回字符串
    
    返回:
        CSV字符串或None（写入文件时）
    """
    if isinstance(data, str):
        data = json.loads(data)
    if not data:
        return ''
    
    表头 = list(data[0].keys())
    行列表 = [','.join(表头)]
    
    for 项 in data:
        行 = []
        for 键 in 表头:
            值 = 项.get(键, '')
            if isinstance(值, str):
                值 = 值.replace(',', '，').replace('\n', ' ')
            行.append(str(值))
        行列表.append(','.join(行))
    
    CSV内容 = '\n'.join(行列表)
    
    if 输出文件:
        with open(输出文件, 'w', encoding='utf-8') as f:
            f.write(CSV内容)
        return None
    return CSV内容


def CSV转JSON(csv内容: str, 表头: list = None) -> list:
    """
    将CSV内容转换为JSON列表
    
    参数:
        csv内容: CSV格式字符串
        表头: 表头列表，None使用第一行作为表头
    
    返回:
        JSON列表（字典列表）
    """
    行列表 = csv内容.strip().split('\n')
    if not 行列表:
        return []
    
    if 表头 is None:
        表头 = 行列表[0].split(',')
        行列表 = 行列表[1:]
    
    结果 = []
    for 行 in 行列表:
        if not 行.strip():
            continue
        列列表 = 行.split(',')
        项 = {}
        for i, 键 in enumerate(表头):
            项[键] = 列列表[i] if i < len(列列表) else ''
        结果.append(项)
    
    return 结果


def JSON键列表(data: dict) -> list:
    """
    获取JSON对象的所有键（递归）
    
    参数:
        data: JSON对象（字典）
    
    返回:
        所有键的列表
    """
    结果 = []
    
    def _获取键(当前, 路径):
        if isinstance(当前, dict):
            for 键, 值 in 当前.items():
                新路径 = f"{路径}.{键}" if 路径 else 键
                结果.append(新路径)
                _获取键(值, 新路径)
        elif isinstance(当前, list):
            for i, 元素 in enumerate(当前):
                新路径 = f"{路径}[{i}]" if 路径 else f"[{i}]"
                _获取键(元素, 新路径)
    
    _获取键(data, '')
    return 结果


def JSON值列表(data: dict, 键: str = None) -> list:
    """
    获取JSON对象的所有值（递归）
    
    参数:
        data: JSON对象（字典）
        键: 过滤键，None获取所有值
    
    返回:
        所有值的列表
    """
    结果 = []
    
    def _获取值(当前):
        if isinstance(当前, dict):
            for k, v in 当前.items():
                if 键 is None or k == 键:
                    结果.append(v)
                _获取值(v)
        elif isinstance(当前, list):
            for 元素 in 当前:
                _获取值(元素)
    
    _获取值(data)
    return 结果


def JSON长度(data: Any) -> int:
    """
    获取JSON数据的长度
    
    参数:
        data: JSON数据
    
    返回:
        长度（字典键数或列表元素数）
    """
    if isinstance(data, (dict, list)):
        return len(data)
    return 0


def JSON类型(data: Any) -> str:
    """
    获取JSON数据的类型
    
    参数:
        data: JSON数据
    
    返回:
        类型名称（对象、数组、字符串、数字、布尔、空）
    """
    if isinstance(data, dict):
        return '对象'
    elif isinstance(data, list):
        return '数组'
    elif isinstance(data, str):
        return '字符串'
    elif isinstance(data, (int, float)):
        return '数字'
    elif isinstance(data, bool):
        return '布尔'
    elif data is None:
        return '空'
    return '未知'


def JSON转字符串(data: Any, 缩进: int = 2) -> str:
    """
    JSON对象转格式化字符串（别名）
    
    参数:
        data: JSON对象
        缩进: 缩进空格数
    
    返回:
        格式化的JSON字符串
    """
    return 美化JSON(data)


def 字符串转JSON(text: str) -> Any:
    """
    字符串转JSON对象（别名）
    
    参数:
        text: JSON格式字符串
    
    返回:
        JSON对象
    """
    return 解析JSON(text)


def JSON文件转字典(path: str) -> dict:
    """
    从文件读取JSON并转为字典
    
    参数:
        path: 文件路径
    
    返回:
        字典
    """
    return JSON转字典(读取文件内容(path))


def 字典转JSON文件(数据: dict, path: str, 美化: bool = False) -> None:
    """
    将字典写入JSON文件
    
    参数:
        数据: 字典
        path: 文件路径
        美化: 是否格式化输出
    """
    写入JSON文件(path, 数据, 美化)


def 读取文件内容(path: str) -> str:
    """
    读取文件内容（内部辅助函数）
    
    参数:
        path: 文件路径
    
    返回:
        文件内容
    """
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def JSON格式化(text: str, 缩进: int = 2) -> str:
    """
    格式化JSON字符串
    
    参数:
        text: JSON格式字符串
        缩进: 缩进空格数
    
    返回:
        格式化后的JSON字符串
    """
    data = 解析JSON(text)
    return 序列化JSON(data, 缩进)


def JSON压缩(text: str) -> str:
    """
    压缩JSON字符串（去除空格）
    
    参数:
        text: JSON格式字符串
    
    返回:
        压缩后的JSON字符串
    """
    data = 解析JSON(text)
    return 序列化JSON(data)


def JSON比较(data1: Any, data2: Any) -> bool:
    """
    比较两个JSON对象是否相等
    
    参数:
        data1: 第一个JSON对象
        data2: 第二个JSON对象
    
    返回:
        是否相等
    """
    return json.dumps(data1, sort_keys=True) == json.dumps(data2, sort_keys=True)


def JSON差异(data1: dict, data2: dict) -> dict:
    """
    获取两个JSON对象的差异
    
    参数:
        data1: 第一个JSON对象（字典）
        data2: 第二个JSON对象（字典）
    
    返回:
        差异字典
    """
    差异 = {}
    所有键 = set(data1.keys()).union(set(data2.keys()))
    
    for 键 in 所有键:
        if 键 not in data1:
            差异[键] = {'类型': '新增', '值': data2[键]}
        elif 键 not in data2:
            差异[键] = {'类型': '删除', '值': data1[键]}
        elif data1[键] != data2[键]:
            差异[键] = {'类型': '修改', '原值': data1[键], '新值': data2[键]}
    
    return 差异


def JSONSchema验证(data: Any, schema: dict) -> bool:
    """
    使用JSON Schema验证数据（简化版）
    
    参数:
        data: 待验证数据
        schema: JSON Schema定义
    
    返回:
        是否通过验证
    
    示例:
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        JSONSchema验证({"name": "段言"}, schema)  # True
    """
    try:
        return _验证Schema(data, schema)
    except:
        return False


def _验证Schema(data: Any, schema: dict) -> bool:
    """内部验证函数"""
    类型 = schema.get('type')
    
    if 类型 == 'object':
        if not isinstance(data, dict):
            return False
        属性 = schema.get('properties', {})
        for 键, 属性Schema in 属性.items():
            if 键 in data and not _验证Schema(data[键], 属性Schema):
                return False
        必填 = schema.get('required', [])
        for 键 in 必填:
            if 键 not in data:
                return False
        return True
    
    elif 类型 == 'array':
        if not isinstance(data, list):
            return False
        元素类型 = schema.get('items')
        if 元素类型:
            for 元素 in data:
                if not _验证Schema(元素, 元素类型):
                    return False
        return True
    
    elif 类型 == 'string':
        return isinstance(data, str)
    
    elif 类型 == 'number':
        return isinstance(data, (int, float))
    
    elif 类型 == 'integer':
        return isinstance(data, int)
    
    elif 类型 == 'boolean':
        return isinstance(data, bool)
    
    elif 类型 == 'null':
        return data is None
    
    elif 类型 == 'any':
        return True
    
    elif isinstance(类型, list):
        return any(_验证Schema(data, {'type': t}) for t in 类型)
    
    return True


def JSON转XML(data: Any, 根元素: str = 'root') -> str:
    """
    将JSON转换为XML格式（简化版）
    
    参数:
        data: JSON数据
        根元素: 根元素名称
    
    返回:
        XML字符串
    """
    def _转XML(数据, 标签):
        if isinstance(数据, dict):
            内容 = []
            for 键, 值 in 数据.items():
                内容.append(_转XML(值, 键))
            return f"<{标签}>{''.join(内容)}</{标签}>"
        elif isinstance(数据, list):
            内容 = []
            for 元素 in 数据:
                内容.append(_转XML(元素, 'item'))
            return f"<{标签}>{''.join(内容)}</{标签}>"
        elif 数据 is None:
            return f"<{标签}/>"
        else:
            return f"<{标签}>{数据}</{标签}>"
    
    return f"<?xml version='1.0' encoding='utf-8'?>{_转XML(data, 根元素)}"


# 合并自JSON解析器.py的独有函数


def 生成JSON(对象: Any, 缩进: int = None, 确保ASCII: bool = True) -> str:
    """生成JSON字符串"""
    return json.dumps(对象, indent=缩进, ensure_ascii=确保ASCII)


def 字典转JSON(字典: Dict[str, Any], 缩进: int = None) -> str:
    """字典转JSON字符串"""
    return json.dumps(字典, indent=缩进, ensure_ascii=False)


def 列表转JSON(列表: List[Any], 缩进: int = None) -> str:
    """列表转JSON字符串"""
    return json.dumps(列表, indent=缩进, ensure_ascii=False)


def JSON验证(字符串: str) -> bool:
    """验证JSON格式是否正确"""
    try:
        json.loads(字符串)
        return True
    except ValueError:
        return False


def JSON深拷贝(对象: Any) -> Any:
    """深拷贝JSON对象"""
    return json.loads(json.dumps(对象))


def JSON设置值(字符串: str, 路径: str, 值: Any) -> str:
    """设置JSON中的值（支持点分隔路径）"""
    对象 = json.loads(字符串)
    当前 = 对象
    键列表 = 路径.split('.')
    
    for i, 键 in enumerate(键列表[:-1]):
        if isinstance(当前, dict) and 键 in 当前:
            当前 = 当前[键]
        elif isinstance(当前, list) and 键.isdigit():
            当前 = 当前[int(键)]
        else:
            return 字符串
    
    最后键 = 键列表[-1]
    if isinstance(当前, dict):
        当前[最后键] = 值
    elif isinstance(当前, list) and 最后键.isdigit():
        当前[int(最后键)] = 值
    
    return json.dumps(对象, indent=2, ensure_ascii=False)


def JSON删除键(字符串: str, 路径: str) -> str:
    """删除JSON中的键（支持点分隔路径）"""
    对象 = json.loads(字符串)
    当前 = 对象
    键列表 = 路径.split('.')
    
    for i, 键 in enumerate(键列表[:-1]):
        if isinstance(当前, dict) and 键 in 当前:
            当前 = 当前[键]
        elif isinstance(当前, list) and 键.isdigit():
            当前 = 当前[int(键)]
        else:
            return 字符串
    
    最后键 = 键列表[-1]
    if isinstance(当前, dict) and 最后键 in 当前:
        del 当前[最后键]
    elif isinstance(当前, list) and 最后键.isdigit():
        del 当前[int(最后键)]
    
    return json.dumps(对象, indent=2, ensure_ascii=False)


def JSON遍历(字符串: str, 回调函数: callable):
    """遍历JSON对象"""
    对象 = json.loads(字符串)
    
    def 递归遍历(当前, 路径=''):
        if isinstance(当前, dict):
            for 键, 值 in 当前.items():
                回调函数(f'{路径}.{键}' if 路径 else 键, 值)
                递归遍历(值, f'{路径}.{键}' if 路径 else 键)
        elif isinstance(当前, list):
            for i, 值 in enumerate(当前):
                回调函数(f'{路径}[{i}]', 值)
                递归遍历(值, f'{路径}[{i}]')
    
    递归遍历(对象)


def JSON计数(字符串: str) -> Dict[str, int]:
    """统计JSON中各类型的数量"""
    对象 = json.loads(字符串)
    计数 = {'dict': 0, 'list': 0, 'str': 0, 'int': 0, 'float': 0, 'bool': 0, 'null': 0}
    
    def 递归计数(当前):
        if isinstance(当前, dict):
            计数['dict'] += 1
            for 值 in 当前.values():
                递归计数(值)
        elif isinstance(当前, list):
            计数['list'] += 1
            for 值 in 当前:
                递归计数(值)
        elif isinstance(当前, str):
            计数['str'] += 1
        elif isinstance(当前, int):
            计数['int'] += 1
        elif isinstance(当前, float):
            计数['float'] += 1
        elif isinstance(当前, bool):
            计数['bool'] += 1
        elif 当前 is None:
            计数['null'] += 1
    
    递归计数(对象)
    return 计数


def JSON转换XML(字符串: str, 根节点: str = 'root') -> str:
    """将JSON转换为XML"""
    对象 = json.loads(字符串)
    
    def 转换(数据, 父标签):
        if isinstance(数据, dict):
            结果 = []
            for 键, 值 in 数据.items():
                结果.append(f'<{键}>')
                结果.append(转换(值, 键))
                结果.append(f'</{键}>')
            return '\n'.join(结果)
        elif isinstance(数据, list):
            结果 = []
            for i, 项 in enumerate(数据):
                结果.append(f'<item index="{i}">')
                结果.append(转换(项, 'item'))
                结果.append('</item>')
            return '\n'.join(结果)
        else:
            return str(data)
    
    return f'<{根节点}>\n{转换(对象, 根节点)}\n</{根节点}>'


def JSON转Python对象(字符串: str, 类映射: Dict[str, type] = None) -> Any:
    """JSON转Python对象（支持自定义类）"""
    对象 = json.loads(字符串)
    
    if 类映射 and isinstance(对象, dict) and '__class__' in 对象:
        类名 = 对象['__class__']
        if 类名 in 类映射:
            实例 = 类映射[类名].__new__(类映射[类名])
            实例.__dict__.update(对象['__data__'])
            return 实例
    
    return 对象


def Python对象转JSON(对象: Any) -> str:
    """Python对象转JSON（支持自定义类）"""
    def 默认处理(obj):
        if hasattr(obj, '__dict__'):
            return {'__class__': obj.__class__.__name__, '__data__': obj.__dict__}
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')
    
    return json.dumps(对象, default=默认处理, indent=2, ensure_ascii=False)


def JSON格式化美化(字符串: str) -> str:
    """美化JSON字符串（带语法高亮）"""
    对象 = json.loads(字符串)
    
    颜色 = {
        'key': '\033[94m',
        'string': '\033[92m',
        'number': '\033[93m',
        'bool': '\033[95m',
        'null': '\033[91m',
        'end': '\033[0m'
    }
    
    def 美化(数据, 缩进=0):
        if isinstance(数据, dict):
            结果 = ['{']
            缩进 += 2
            项 = []
            for 键, 值 in 数据.items():
                项.append(f'{" " * 缩进}{颜色["key"]}"{键}"{颜色["end"]}: {美化(值, 缩进)}')
            结果.append(',\n'.join(项))
            缩进 -= 2
            结果.append(f'{" " * 缩进}}}',)
            return '\n'.join(结果)
        elif isinstance(数据, list):
            结果 = ['[']
            缩进 += 2
            项 = [f'{" " * 缩进}{美化(值, 缩进)}' for 值 in 数据]
            结果.append(',\n'.join(项))
            缩进 -= 2
            结果.append(f'{" " * 缩进}]')
            return '\n'.join(结果)
        elif isinstance(数据, str):
            return f'{颜色["string"]}"{数据}"{颜色["end"]}'
        elif isinstance(数据, (int, float)):
            return f'{颜色["number"]}{数据}{颜色["end"]}'
        elif isinstance(数据, bool):
            return f'{颜色["bool"]}{数据}{颜色["end"]}'
        elif 数据 is None:
            return f'{颜色["null"]}null{颜色["end"]}'
    
    return 美化(对象)


def JSON获取大小(字符串: str) -> int:
    """获取JSON字符串大小（字节数）"""
    return len(字符串.encode('utf-8'))


def JSON版本() -> str:
    """获取JSON模块版本"""
    return json.__name__


def JSON编码器(对象: Any) -> str:
    """JSON编码器"""
    return json.dumps(对象)


def JSON解码器(字符串: str) -> Any:
    """JSON解码器"""
    return json.loads(字符串)


__all__ = [
    '解析JSON', '序列化JSON', '美化JSON',
    '读取JSON文件', '写入JSON文件',
    'JSON转Python', 'Python转JSON',
    'JSON转字典', 'JSON转列表',
    '验证JSON', '验证JSON文件',
    'JSON合并', 'JSON深合并',
    'JSON提取值', 'JSON查找',
    'JSON过滤', 'JSON映射',
    'JSON聚合', 'JSON分组',
    'JSON排序', 'JSON去重',
    'JSON扁平化', 'JSON展开',
    'JSON转CSV', 'CSV转JSON',
    'JSON键列表', 'JSON值列表',
    'JSON长度', 'JSON类型',
    'JSON转字符串', '字符串转JSON',
    'JSON文件转字典', '字典转JSON文件',
    'JSON格式化', 'JSON压缩',
    'JSON比较', 'JSON差异',
    'JSONSchema验证',
    'JSON转XML',
    # 合并自JSON解析器.py的独有函数
    '生成JSON', '字典转JSON', '列表转JSON',
    'JSON验证', 'JSON深拷贝',
    'JSON设置值', 'JSON删除键',
    'JSON遍历', 'JSON计数',
    'JSON转换XML',
    'JSON转Python对象', 'Python对象转JSON',
    'JSON格式化美化',
    'JSON获取大小', 'JSON版本',
    'JSON编码器', 'JSON解码器',
]