"""
光明标准库 - 对象序列化模块

封装 pickle 模块，提供对象的序列化和反序列化功能。
"""

import pickle
import json
import base64
from typing import Any, Optional


def 序列化(对象: Any, 协议: int = pickle.HIGHEST_PROTOCOL) -> bytes:
    """
    序列化对象为字节
    
    参数:
        对象: 要序列化的对象
        协议: pickle协议版本
    
    返回:
        字节数据
    """
    return pickle.dumps(对象, protocol=协议)


def 反序列化(数据: bytes) -> Any:
    """
    反序列化字节为对象
    
    参数:
        数据: 字节数据
    
    返回:
        反序列化后的对象
    """
    return pickle.loads(数据)


def 保存到文件(对象: Any, 文件路径: str, 协议: int = pickle.HIGHEST_PROTOCOL) -> None:
    """
    将对象序列化后保存到文件
    
    参数:
        对象: 要序列化的对象
        文件路径: 文件路径
        协议: pickle协议版本
    """
    with open(文件路径, 'wb') as f:
        pickle.dump(对象, f, protocol=协议)


def 从文件加载(文件路径: str) -> Any:
    """
    从文件加载并反序列化对象
    
    参数:
        文件路径: 文件路径
    
    返回:
        反序列化后的对象
    """
    with open(文件路径, 'rb') as f:
        return pickle.load(f)


def 序列化为字符串(对象: Any) -> str:
    """
    序列化为Base64编码的字符串（便于文本传输）
    
    参数:
        对象: 要序列化的对象
    
    返回:
        Base64编码的字符串
    """
    字节数据 = 序列化(对象)
    return base64.b64encode(字节数据).decode('ascii')


def 从字符串反序列化(字符串: str) -> Any:
    """
    从Base64字符串反序列化对象
    
    参数:
        字符串: Base64编码的字符串
    
    返回:
        反序列化后的对象
    """
    字节数据 = base64.b64decode(字符串.encode('ascii'))
    return 反序列化(字节数据)


def 深复制(对象: Any) -> Any:
    """
    通过序列化实现深复制
    
    参数:
        对象: 要复制的对象
    
    返回:
        深复制的对象
    """
    return pickle.loads(pickle.dumps(对象))


def JSON序列化(对象: Any, 缩进: int = None, 确保ASCII: bool = False) -> str:
    """
    JSON序列化（仅支持可JSON序列化的对象）
    
    参数:
        对象: 要序列化的对象
        缩进: 缩进空格数
        确保ASCII: 是否确保ASCII
    
    返回:
        JSON字符串
    """
    return json.dumps(对象, indent=缩进, ensure_ascii=确保ASCII)


def JSON反序列化(JSON字符串: str) -> Any:
    """
    JSON反序列化
    
    参数:
        JSON字符串: JSON字符串
    
    返回:
        反序列化后的对象
    """
    return json.loads(JSON字符串)


__all__ = [
    '序列化',
    '反序列化',
    '保存到文件',
    '从文件加载',
    '序列化为字符串',
    '从字符串反序列化',
    '深复制',
    'JSON序列化',
    'JSON反序列化',
]
