# -*- coding: utf-8 -*-
"""
光明标准库 - 配置文件解析模块

提供 INI/JSON/YAML 配置文件的解析和生成功能。
"""

import json
import configparser
import os
from typing import Any, Dict, Optional


def 读取配置(文件路径: str) -> dict:
    """
    自动检测配置文件类型并读取

    支持 JSON、INI、YAML 格式

    参数:
        文件路径: 配置文件路径

    返回:
        配置字典
    """
    if not os.path.exists(文件路径):
        raise RuntimeError(f"配置文件不存在: '{文件路径}'")

    扩展名 = os.path.splitext(文件路径)[1].lower()

    if 扩展名 in ('.json',):
        return 读取JSON(文件路径)
    elif 扩展名 in ('.ini', '.cfg', '.conf'):
        return 读取INI(文件路径)
    elif 扩展名 in ('.yaml', '.yml'):
        return 读取YAML(文件路径)
    else:
        # 尝试多种格式
        try:
            return 读取JSON(文件路径)
        except Exception:
            try:
                return 读取INI(文件路径)
            except Exception:
                try:
                    return 读取YAML(文件路径)
                except Exception:
                    raise RuntimeError(f"无法识别的配置文件格式: '{文件路径}'")


def 写入配置(文件路径: str, 配置: dict):
    """
    写入配置文件（自动根据扩展名判断格式）

    参数:
        文件路径: 输出文件路径
        配置: 配置字典
    """
    扩展名 = os.path.splitext(文件路径)[1].lower()

    if 扩展名 in ('.json',):
        写入JSON(文件路径, 配置)
    elif 扩展名 in ('.ini', '.cfg', '.conf'):
        写入INI(文件路径, 配置)
    elif 扩展名 in ('.yaml', '.yml'):
        写入YAML(文件路径, 配置)
    else:
        # 默认使用 JSON 格式
        写入JSON(文件路径, 配置)


def 读取JSON(文件路径: str) -> dict:
    """
    读取 JSON 配置文件

    参数:
        文件路径: JSON 文件路径

    返回:
        配置字典
    """
    try:
        with open(文件路径, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"JSON 文件不存在: '{文件路径}'")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON 解析失败 '{文件路径}': {e}")


def 写入JSON(文件路径: str, 数据: dict, 缩进: int = 2):
    """
    写入 JSON 配置文件

    参数:
        文件路径: 输出文件路径
        数据: 配置字典
        缩进: 缩进空格数
    """
    try:
        dir_path = os.path.dirname(文件路径)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        with open(文件路径, 'w', encoding='utf-8') as f:
            json.dump(数据, f, ensure_ascii=False, indent=缩进)
    except Exception as e:
        raise RuntimeError(f"写入 JSON 文件失败 '{文件路径}': {e}")


def 读取INI(文件路径: str) -> dict:
    """
    读取 INI 配置文件

    参数:
        文件路径: INI 文件路径

    返回:
        配置字典 {section: {key: value}}
    """
    try:
        parser = configparser.ConfigParser()
        parser.read(文件路径, encoding='utf-8')
        结果 = {}
        for section in parser.sections():
            结果[section] = dict(parser.items(section))
        return 结果
    except Exception as e:
        raise RuntimeError(f"INI 文件解析失败 '{文件路径}': {e}")


def 写入INI(文件路径: str, 配置: dict):
    """
    写入 INI 配置文件

    参数:
        文件路径: 输出文件路径
        配置: 配置字典 {section: {key: value}}
    """
    try:
        parser = configparser.ConfigParser()
        for section, items in 配置.items():
            parser.add_section(section)
            for key, value in items.items():
                parser.set(section, key, str(value))
        dir_path = os.path.dirname(文件路径)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        with open(文件路径, 'w', encoding='utf-8') as f:
            parser.write(f)
    except Exception as e:
        raise RuntimeError(f"写入 INI 文件失败 '{文件路径}': {e}")


def 读取YAML(文件路径: str) -> dict:
    """
    读取 YAML 配置文件

    参数:
        文件路径: YAML 文件路径

    返回:
        配置字典
    """
    try:
        import yaml
        with open(文件路径, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        raise RuntimeError("YAML 支持需要安装 PyYAML: pip install pyyaml")
    except FileNotFoundError:
        raise RuntimeError(f"YAML 文件不存在: '{文件路径}'")
    except Exception as e:
        raise RuntimeError(f"YAML 解析失败 '{文件路径}': {e}")


def 写入YAML(文件路径: str, 数据: dict):
    """
    写入 YAML 配置文件

    参数:
        文件路径: 输出文件路径
        数据: 配置字典
    """
    try:
        import yaml
        dir_path = os.path.dirname(文件路径)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        with open(文件路径, 'w', encoding='utf-8') as f:
            yaml.dump(数据, f, allow_unicode=True, default_flow_style=False)
    except ImportError:
        raise RuntimeError("YAML 支持需要安装 PyYAML: pip install pyyaml")
    except Exception as e:
        raise RuntimeError(f"写入 YAML 文件失败 '{文件路径}': {e}")


def 配置获取(配置: dict, 键路径: str, 默认值: Any = None) -> Any:
    """
    从配置字典中按点分隔路径获取值

    参数:
        配置: 配置字典
        键路径: 点分隔的键路径，如 'database.host'
        默认值: 路径不存在时的默认值

    返回:
        配置值
    """
    当前 = 配置
    键列表 = 键路径.split('.')
    for 键 in 键列表:
        if isinstance(当前, dict) and 键 in 当前:
            当前 = 当前[键]
        else:
            return 默认值
    return 当前


def 配置设置(配置: dict, 键路径: str, 值: Any):
    """
    按点分隔路径设置配置值

    参数:
        配置: 配置字典
        键路径: 点分隔的键路径，如 'database.host'
        值: 要设置的值
    """
    当前 = 配置
    键列表 = 键路径.split('.')
    for 键 in 键列表[:-1]:
        if 键 not in 当前:
            当前[键] = {}
        当前 = 当前[键]
    当前[键列表[-1]] = 值


def 配置合并(基础配置: dict, 新配置: dict) -> dict:
    """
    合并两个配置字典（深度合并）

    参数:
        基础配置: 基础配置
        新配置: 新配置（覆盖基础配置）

    返回:
        合并后的配置字典
    """
    结果 = dict(基础配置)
    for 键, 值 in 新配置.items():
        if 键 in 结果 and isinstance(结果[键], dict) and isinstance(值, dict):
            结果[键] = 配置合并(结果[键], 值)
        else:
            结果[键] = 值
    return 结果


__all__ = [
    '读取配置', '写入配置',
    '读取JSON', '写入JSON',
    '读取INI', '写入INI',
    '读取YAML', '写入YAML',
    '配置获取', '配置设置', '配置合并',
]