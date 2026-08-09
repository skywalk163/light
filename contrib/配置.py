"""光明标准库 - 配置模块"""

import json
import configparser
from typing import Any


def 读取配置(文件路径: str) -> dict:
    """读取 JSON 配置文件"""
    with open(文件路径, "r", encoding="utf-8") as f:
        return json.load(f)


def 写入配置(文件路径: str, 配置: dict) -> None:
    """写入 JSON 配置文件"""
    with open(文件路径, "w", encoding="utf-8") as f:
        json.dump(配置, f, ensure_ascii=False, indent=2)


def 读取JSON(文件路径: str) -> dict:
    """读取 JSON 文件"""
    with open(文件路径, "r", encoding="utf-8") as f:
        return json.load(f)


def 写入JSON(文件路径: str, 数据: dict, 缩进: int = 2) -> None:
    """写入 JSON 文件"""
    with open(文件路径, "w", encoding="utf-8") as f:
        json.dump(数据, f, ensure_ascii=False, indent=缩进)


def 读取INI(文件路径: str) -> dict:
    """读取 INI 配置文件（返回 {section: {key: value}}）"""
    parser = configparser.ConfigParser()
    parser.read(文件路径, encoding="utf-8")
    结果 = {}
    for section in parser.sections():
        结果[section] = dict(parser.items(section))
    return 结果


def 写入INI(文件路径: str, 配置: dict) -> None:
    """写入 INI 配置文件"""
    parser = configparser.ConfigParser()
    for section, items in 配置.items():
        parser.add_section(section)
        for key, value in items.items():
            parser.set(section, key, str(value))
    with open(文件路径, "w", encoding="utf-8") as f:
        parser.write(f)
