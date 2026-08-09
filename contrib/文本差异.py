"""
光明标准库 - 文本差异模块

封装 difflib 模块，提供文本比较和差异计算功能。
"""

import difflib
from typing import List, Optional, Tuple


def 比较文本(文本1: str, 文本2: str, 名称1: str = "原文件", 名称2: str = "新文件") -> List[str]:
    """
    比较两个文本，返回统一差异格式（unified diff）
    
    参数:
        文本1: 原始文本
        文本2: 新文本
        名称1: 原始文件名
        名称2: 新文件名
    
    返回:
        差异行列表
    """
    行列表1 = 文本1.splitlines(keepends=True)
    行列表2 = 文本2.splitlines(keepends=True)
    
    diff = difflib.unified_diff(行列表1, 行列表2, fromfile=名称1, tofile=名称2)
    return list(diff)


def 差异字符串(文本1: str, 文本2: str, 名称1: str = "原文件", 名称2: str = "新文件") -> str:
    """
    比较两个文本，返回差异字符串
    
    参数:
        文本1: 原始文本
        文本2: 新文本
        名称1: 原始文件名
        名称2: 新文件名
    
    返回:
        差异字符串
    """
    return "".join(比较文本(文本1, 文本2, 名称1, 名称2))


def 上下文差异(文本1: str, 文本2: str, 名称1: str = "原文件", 名称2: str = "新文件", 上下文行数: int = 3) -> List[str]:
    """
    上下文格式差异
    
    参数:
        文本1: 原始文本
        文本2: 新文本
        名称1: 原始文件名
        名称2: 新文件名
        上下文行数: 上下文行数
    
    返回:
        差异行列表
    """
    行列表1 = 文本1.splitlines(keepends=True)
    行列表2 = 文本2.splitlines(keepends=True)
    
    diff = difflib.context_diff(行列表1, 行列表2, fromfile=名称1, tofile=名称2, n=上下文行数)
    return list(diff)


def HTML差异(文本1: str, 文本2: str, 名称1: str = "原文件", 名称2: str = "新文件") -> str:
    """
    生成HTML格式的差异报告
    
    参数:
        文本1: 原始文本
        文本2: 新文本
        名称1: 原始文件名
        名称2: 新文件名
    
    返回:
        HTML字符串
    """
    行列表1 = 文本1.splitlines()
    行列表2 = 文本2.splitlines()
    
    html_diff = difflib.HtmlDiff()
    return html_diff.make_file(行列表1, 行列表2, fromdesc=名称1, todesc=名称2)


def 相似度(文本1: str, 文本2: str) -> float:
    """
    计算两个文本的相似度
    
    参数:
        文本1: 文本1
        文本2: 文本2
    
    返回:
        相似度（0.0 - 1.0）
    """
    matcher = difflib.SequenceMatcher(None, 文本1, 文本2)
    return matcher.ratio()


def 行相似度(行列表1: List[str], 行列表2: List[str]) -> float:
    """
    计算两行列表的相似度
    
    参数:
        行列表1: 行列表1
        行列表2: 行列表2
    
    返回:
        相似度（0.0 - 1.0）
    """
    matcher = difflib.SequenceMatcher(None, 行列表1, 行列表2)
    return matcher.ratio()


def 查找最相似(目标: str, 候选列表: List[str], 阈值: float = 0.6, 数量: int = 3) -> List[Tuple[str, float]]:
    """
    在候选列表中查找最相似的项
    
    参数:
        目标: 目标字符串
        候选列表: 候选字符串列表
        阈值: 最小相似度阈值
        数量: 返回数量
    
    返回:
        [(字符串, 相似度), ...] 按相似度降序排列
    """
    结果 = []
    for 候选 in 候选列表:
        相似度值 = 相似度(目标, 候选)
        if 相似度值 >= 阈值:
            结果.append((候选, 相似度值))
    
    结果.sort(key=lambda x: x[1], reverse=True)
    return 结果[:数量]


def 字符串最相似(目标: str, 候选列表: List[str]) -> Optional[str]:
    """
    查找最相似的字符串
    
    参数:
        目标: 目标字符串
        候选列表: 候选列表
    
    返回:
        最相似的字符串，无匹配返回None
    """
    结果 = 查找最相似(目标, 候选列表, 阈值=0.0, 数量=1)
    return 结果[0][0] if 结果 else None


def 比较行(行列表1: List[str], 行列表2: List[str]) -> List[Tuple[str, str, Optional[int], Optional[int]]]:
    """
    逐行比较
    
    返回:
        [(操作类型, 内容, 行号1, 行号2), ...]
        操作类型: '相等', '替换', '删除', '插入'
    """
    matcher = difflib.SequenceMatcher(None, 行列表1, 行列表2)
    结果 = []
    
    for 操作码 in matcher.get_opcodes():
        标签, i1, i2, j1, j2 = 操作码
        if 标签 == 'equal':
            for k in range(i2 - i1):
                结果.append(('相等', 行列表1[i1 + k], i1 + k + 1, j1 + k + 1))
        elif 标签 == 'replace':
            for k in range(max(i2 - i1, j2 - j1)):
                旧行 = 行列表1[i1 + k] if i1 + k < i2 else ''
                新行 = 行列表2[j1 + k] if j1 + k < j2 else ''
                结果.append(('替换', f"{旧行} -> {新行}", i1 + k + 1 if i1 + k < i2 else None, j1 + k + 1 if j1 + k < j2 else None))
        elif 标签 == 'delete':
            for k in range(i2 - i1):
                结果.append(('删除', 行列表1[i1 + k], i1 + k + 1, None))
        elif 标签 == 'insert':
            for k in range(j2 - j1):
                结果.append(('插入', 行列表2[j1 + k], None, j1 + k + 1))
    
    return 结果


def 快速比较(文本1: str, 文本2: str) -> dict:
    """
    快速比较文本，返回统计信息
    
    参数:
        文本1: 文本1
        文本2: 文本2
    
    返回:
        统计信息字典
    """
    行列表1 = 文本1.splitlines()
    行列表2 = 文本2.splitlines()
    
    matcher = difflib.SequenceMatcher(None, 行列表1, 行列表2)
    
    新增 = 0
    删除 = 0
    修改 = 0
    相同 = 0
    
    for 操作码 in matcher.get_opcodes():
        标签, i1, i2, j1, j2 = 操作码
        if 标签 == 'equal':
            相同 += i2 - i1
        elif 标签 == 'replace':
            修改 += max(i2 - i1, j2 - j1)
        elif 标签 == 'delete':
            删除 += i2 - i1
        elif 标签 == 'insert':
            新增 += j2 - j1
    
    return {
        '相似度': matcher.ratio(),
        '原文件行数': len(行列表1),
        '新文件行数': len(行列表2),
        '相同行数': 相同,
        '新增行数': 新增,
        '删除行数': 删除,
        '修改行数': 修改,
    }


__all__ = [
    '比较文本',
    '差异字符串',
    '上下文差异',
    'HTML差异',
    '相似度',
    '行相似度',
    '查找最相似',
    '字符串最相似',
    '比较行',
    '快速比较',
]
