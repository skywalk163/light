# -*- coding: utf-8 -*-
"""
光明标准库 - XML 解析与生成模块

提供 XML 的解析、生成、查询和转换功能。
基于 Python 标准库 xml.etree.ElementTree。
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Optional, List, Dict, Any, Union


def XML解析(文本: str) -> Any:
    """
    解析 XML 字符串为 Element 对象

    参数:
        文本: XML 格式字符串

    返回:
        XML Element 根节点
    """
    try:
        return ET.fromstring(文本)
    except ET.ParseError as e:
        raise RuntimeError(f"XML 解析失败: {e}")


def XML解析文件(文件路径: str) -> Any:
    """
    从文件解析 XML

    参数:
        文件路径: XML 文件路径

    返回:
        XML Element 根节点
    """
    try:
        tree = ET.parse(文件路径)
        return tree.getroot()
    except ET.ParseError as e:
        raise RuntimeError(f"XML 文件解析失败 '{文件路径}': {e}")
    except FileNotFoundError:
        raise RuntimeError(f"文件不存在: '{文件路径}'")


def XML生成(根标签: str, 属性: Dict[str, str] = None, 文本: str = None) -> Any:
    """
    创建 XML 元素

    参数:
        根标签: 元素标签名
        属性: 元素属性字典
        文本: 元素文本内容

    返回:
        XML Element 对象
    """
    elem = ET.Element(根标签, attrib=属性 or {})
    if 文本 is not None:
        elem.text = 文本
    return elem


def XML子元素(父元素: Any, 标签: str, 属性: Dict[str, str] = None, 文本: str = None) -> Any:
    """
    添加子元素

    参数:
        父元素: 父 Element 对象
        标签: 子元素标签名
        属性: 子元素属性字典
        文本: 子元素文本内容

    返回:
        子 Element 对象
    """
    sub = ET.SubElement(父元素, 标签, attrib=属性 or {})
    if 文本 is not None:
        sub.text = 文本
    return sub


def XML转字符串(元素: Any, 编码: str = 'utf-8') -> str:
    """
    将 Element 对象转换为 XML 字符串

    参数:
        元素: XML Element 对象
        编码: 编码方式

    返回:
        XML 格式字符串
    """
    try:
        rough_string = ET.tostring(元素, encoding=编码)
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding=编码).decode(编码)
    except Exception:
        return ET.tostring(元素, encoding=编码).decode(编码)


def XML美化(文本: str) -> str:
    """
    美化 XML 字符串

    参数:
        文本: XML 格式字符串

    返回:
        美化后的 XML 字符串
    """
    try:
        dom = minidom.parseString(文本)
        return dom.toprettyxml(indent="  ")
    except Exception as e:
        raise RuntimeError(f"XML 美化失败: {e}")


def XML查找(根元素: Any, 路径: str) -> List[Any]:
    """
    查找所有匹配路径的元素

    参数:
        根元素: 根 Element 对象
        路径: XPath 路径表达式

    返回:
        匹配的元素列表
    """
    return 根元素.findall(路径)


def XML查找单个(根元素: Any, 路径: str) -> Optional[Any]:
    """
    查找第一个匹配路径的元素

    参数:
        根元素: 根 Element 对象
        路径: XPath 路径表达式

    返回:
        匹配的元素，未找到返回 None
    """
    return 根元素.find(路径)


def XML获取文本(元素: Any) -> str:
    """
    获取元素的文本内容

    参数:
        元素: XML Element 对象

    返回:
        文本内容
    """
    return 元素.text or ''


def XML获取属性(元素: Any, 属性名: str, 默认值: str = None) -> Optional[str]:
    """
    获取元素的属性值

    参数:
        元素: XML Element 对象
        属性名: 属性名
        默认值: 默认值

    返回:
        属性值
    """
    return 元素.get(属性名, 默认值)


def XML获取所有属性(元素: Any) -> Dict[str, str]:
    """
    获取元素的所有属性

    参数:
        元素: XML Element 对象

    返回:
        属性字典
    """
    return dict(元素.attrib)


def XML设置文本(元素: Any, 文本: str):
    """
    设置元素的文本内容

    参数:
        元素: XML Element 对象
        文本: 文本内容
    """
    元素.text = 文本


def XML设置属性(元素: Any, 属性名: str, 值: str):
    """
    设置元素的属性

    参数:
        元素: XML Element 对象
        属性名: 属性名
        值: 属性值
    """
    元素.set(属性名, 值)


def XML删除元素(父元素: Any, 子元素: Any):
    """
    删除子元素

    参数:
        父元素: 父 Element 对象
        子元素: 要删除的子元素
    """
    父元素.remove(子元素)


def XML获取标签(元素: Any) -> str:
    """
    获取元素的标签名

    参数:
        元素: XML Element 对象

    返回:
        标签名
    """
    return 元素.tag


def XML获取子元素(元素: Any) -> List[Any]:
    """
    获取所有直接子元素

    参数:
        元素: XML Element 对象

    返回:
        子元素列表
    """
    return list(元素)


def XML遍历(元素: Any, 回调函数=None):
    """
    遍历 XML 树的所有节点

    参数:
        元素: 根 Element 对象
        回调函数: 每个节点调用的函数，默认打印
    """
    if 回调函数 is None:
        def 回调函数(elem, depth=0):
            print('  ' * depth + f"<{elem.tag}>")
        _遍历(元素, 回调函数)
    else:
        _遍历(元素, 回调函数)


def _遍历(元素, 回调函数, depth=0):
    回调函数(元素, depth)
    for child in 元素:
        _遍历(child, 回调函数, depth + 1)


def XML转字典(元素: Any) -> dict:
    """
    将 XML 元素转换为字典

    参数:
        元素: XML Element 对象

    返回:
        字典表示
    """
    result = {}
    if 元素.text and 元素.text.strip():
        result['#text'] = 元素.text.strip()
    if 元素.attrib:
        result['@attributes'] = dict(元素.attrib)
    children = list(元素)
    if children:
        child_dict = {}
        for child in children:
            cd = XML转字典(child)
            if child.tag in child_dict:
                if not isinstance(child_dict[child.tag], list):
                    child_dict[child.tag] = [child_dict[child.tag]]
                child_dict[child.tag].append(cd)
            else:
                child_dict[child.tag] = cd
        result.update(child_dict)
    return result


def 字典转XML(数据: dict, 根标签: str = 'root') -> Any:
    """
    将字典转换为 XML 元素

    参数:
        数据: 字典数据
        根标签: 根元素标签名

    返回:
        XML Element 对象
    """
    def _构建(数据, 标签):
        elem = ET.Element(标签)
        if isinstance(数据, dict):
            for key, value in 数据.items():
                if key == '@attributes':
                    elem.attrib.update(value)
                elif key == '#text':
                    elem.text = str(value)
                else:
                    elem.append(_构建(value, key))
        elif isinstance(数据, list):
            for item in 数据:
                elem.append(_构建(item, 标签[:-1] if 标签.endswith('s') else 标签))
        else:
            elem.text = str(数据)
        return elem
    return _构建(数据, 根标签)


def XML写入文件(根元素: Any, 文件路径: str, 编码: str = 'utf-8'):
    """
    将 XML 写入文件

    参数:
        根元素: XML Element 或 ElementTree 对象
        文件路径: 输出文件路径
        编码: 编码方式
    """
    if isinstance(根元素, ET.Element):
        tree = ET.ElementTree(根元素)
    else:
        tree = 根元素
    try:
        tree.write(文件路径, encoding=编码, xml_declaration=True)
    except Exception as e:
        raise RuntimeError(f"XML 写入文件失败 '{文件路径}': {e}")


__all__ = [
    'XML解析', 'XML解析文件', 'XML生成', 'XML子元素',
    'XML转字符串', 'XML美化',
    'XML查找', 'XML查找单个',
    'XML获取文本', 'XML获取属性', 'XML获取所有属性',
    'XML设置文本', 'XML设置属性',
    'XML删除元素', 'XML获取标签', 'XML获取子元素',
    'XML遍历', 'XML转字典', '字典转XML',
    'XML写入文件',
]