"""
CSV读写器模块 - 表格数据解析

提供CSV文件处理功能，包括：
- CSV文件读写
- 数据解析与格式化
- 表头处理
- 编码处理
"""
import csv
import os
from typing import List, Dict, Any, Optional


def 读取CSV(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',', 表头: bool = True) -> List[Dict[str, Any]]:
    """读取CSV文件"""
    with open(文件路径, 'r', encoding=编码) as f:
        阅读器 = csv.DictReader(f, delimiter=分隔符)
        return list(阅读器)


def 读取CSV列表(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',', 表头: bool = True) -> List[List[str]]:
    """读取CSV文件为列表列表"""
    with open(文件路径, 'r', encoding=编码) as f:
        阅读器 = csv.reader(f, delimiter=分隔符)
        return list(阅读器)


def 写入CSV(文件路径: str, 数据: List[Dict[str, Any]], 编码: str = 'utf-8', 分隔符: str = ','):
    """写入CSV文件（字典列表）"""
    if not 数据:
        return
    
    表头 = list(数据[0].keys())
    with open(文件路径, 'w', encoding=编码, newline='') as f:
        写入器 = csv.DictWriter(f, fieldnames=表头, delimiter=分隔符)
        写入器.writeheader()
        写入器.writerows(数据)


def 写入CSV列表(文件路径: str, 数据: List[List[str]], 编码: str = 'utf-8', 分隔符: str = ','):
    """写入CSV文件（列表列表）"""
    with open(文件路径, 'w', encoding=编码, newline='') as f:
        写入器 = csv.writer(f, delimiter=分隔符)
        写入器.writerows(数据)


def CSV转字典(文本: str, 分隔符: str = ',') -> List[Dict[str, Any]]:
    """CSV文本转字典列表"""
    行 = 文本.strip().split('\n')
    if not 行:
        return []
    
    表头 = 行[0].split(分隔符)
    结果 = []
    
    for 行内容 in 行[1:]:
        单元格 = _解析CSV行(行内容, 分隔符)
        结果.append(dict(zip(表头, 单元格)))
    
    return 结果


def 字典转CSV(数据: List[Dict[str, Any]], 分隔符: str = ',') -> str:
    """字典列表转CSV文本"""
    if not 数据:
        return ''
    
    表头 = list(数据[0].keys())
    行 = [分隔符.join(表头)]
    
    for 项 in 数据:
        单元格 = []
        for 列 in 表头:
            值 = 项.get(列, '')
            if isinstance(值, str) and (分隔符 in 值 or '"' in 值 or '\n' in 值):
                值 = 值.replace('"', '""')
                单元格.append(f'"{值}"')
            else:
                单元格.append(str(值))
        行.append(分隔符.join(单元格))
    
    return '\n'.join(行)


def CSV转列表(文本: str, 分隔符: str = ',') -> List[List[str]]:
    """CSV文本转列表列表"""
    行 = 文本.strip().split('\n')
    return [_解析CSV行(行内容, 分隔符) for 行内容 in 行 if 行内容.strip()]


def 列表转CSV(数据: List[List[str]], 分隔符: str = ',') -> str:
    """列表列表转CSV文本"""
    行 = []
    for 行内容 in 数据:
        单元格 = []
        for 值 in 行内容:
            值 = str(值)
            if 分隔符 in 值 or '"' in 值 or '\n' in 值:
                值 = 值.replace('"', '""')
                单元格.append(f'"{值}"')
            else:
                单元格.append(值)
        行.append(分隔符.join(单元格))
    return '\n'.join(行)


def _解析CSV行(行: str, 分隔符: str = ',') -> List[str]:
    """解析CSV单行"""
    结果 = []
    当前 = ''
    在引号内 = False
    
    i = 0
    while i < len(行):
        字符 = 行[i]
        
        if 字符 == '"':
            if 在引号内 and i + 1 < len(行) and 行[i + 1] == '"':
                当前 += '"'
                i += 2
                continue
            在引号内 = not 在引号内
            i += 1
        elif 字符 == 分隔符 and not 在引号内:
            结果.append(当前)
            当前 = ''
            i += 1
        else:
            当前 += 字符
            i += 1
    
    结果.append(当前)
    return 结果


def 获取CSV表头(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> List[str]:
    """获取CSV表头"""
    with open(文件路径, 'r', encoding=编码) as f:
        第一行 = f.readline()
        return _解析CSV行(第一行.strip(), 分隔符)


def 获取CSV行数(文件路径: str, 编码: str = 'utf-8') -> int:
    """获取CSV行数"""
    with open(文件路径, 'r', encoding=编码) as f:
        return sum(1 for _ in f if _.strip())


def 获取CSV列数(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> int:
    """获取CSV列数"""
    表头 = 获取CSV表头(文件路径, 编码, 分隔符)
    return len(表头)


def CSV添加行(文件路径: str, 行: List[Any], 编码: str = 'utf-8', 分隔符: str = ','):
    """向CSV文件添加行"""
    with open(文件路径, 'a', encoding=编码, newline='') as f:
        写入器 = csv.writer(f, delimiter=分隔符)
        写入器.writerow(行)


def CSV添加字典行(文件路径: str, 字典: Dict[str, Any], 编码: str = 'utf-8', 分隔符: str = ','):
    """向CSV文件添加字典行"""
    表头 = 获取CSV表头(文件路径, 编码, 分隔符)
    
    行 = []
    for 列 in 表头:
        行.append(字典.get(列, ''))
    
    CSV添加行(文件路径, 行, 编码, 分隔符)


def CSV筛选(文件路径: str, 条件函数: callable, 编码: str = 'utf-8', 分隔符: str = ',') -> List[Dict[str, Any]]:
    """筛选CSV数据"""
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    return [行 for 行 in 数据 if 条件函数(行)]


def CSV排序(文件路径: str, 键: str, 升序: bool = True, 编码: str = 'utf-8', 分隔符: str = ',') -> List[Dict[str, Any]]:
    """排序CSV数据"""
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    return sorted(数据, key=lambda x: x.get(键, ''), reverse=not 升序)


def CSV分组(文件路径: str, 键: str, 编码: str = 'utf-8', 分隔符: str = ',') -> Dict[str, List[Dict[str, Any]]]:
    """分组CSV数据"""
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    结果 = {}
    
    for 行 in 数据:
        分组键 = 行.get(键, '')
        if 分组键 not in 结果:
            结果[分组键] = []
        结果[分组键].append(行)
    
    return 结果


def CSV聚合(文件路径: str, 分组键: str, 聚合键: str, 聚合函数: callable, 编码: str = 'utf-8', 分隔符: str = ',') -> Dict[str, Any]:
    """聚合CSV数据"""
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    分组 = {}
    
    for 行 in 数据:
        键 = 行.get(分组键, '')
        值 = 行.get(聚合键, '')
        
        try:
            值 = float(值)
        except ValueError:
            值 = 0
        
        if 键 not in 分组:
            分组[键] = []
        分组[键].append(值)
    
    return {键: 聚合函数(值列表) for 键, 值列表 in 分组.items()}


def CSV转JSON(文件路径: str, 输出文件: str = None, 编码: str = 'utf-8', 分隔符: str = ',') -> str:
    """CSV转JSON"""
    import json
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    
    JSON内容 = json.dumps(数据, indent=2, ensure_ascii=False)
    
    if 输出文件:
        with open(输出文件, 'w', encoding='utf-8') as f:
            f.write(JSON内容)
    
    return JSON内容


def JSON转CSV(文件路径: str, 输出文件: str = None, 编码: str = 'utf-8', 分隔符: str = ',') -> str:
    """JSON转CSV"""
    import json
    
    with open(文件路径, 'r', encoding='utf-8') as f:
        数据 = json.load(f)
    
    if not isinstance(数据, list):
        raise ValueError('JSON必须是数组格式')
    
    CSV内容 = 字典转CSV(数据, 分隔符)
    
    if 输出文件:
        with open(输出文件, 'w', encoding=编码) as f:
            f.write(CSV内容)
    
    return CSV内容


def CSV合并(*文件路径列表: str, 输出文件: str = None, 编码: str = 'utf-8', 分隔符: str = ',') -> str:
    """合并多个CSV文件"""
    合并数据 = []
    表头 = None
    
    for 文件路径 in 文件路径列表:
        数据 = 读取CSV(文件路径, 编码, 分隔符)
        if not 表头:
            表头 = list(数据[0].keys()) if 数据 else []
        合并数据.extend(数据)
    
    if not 合并数据:
        return ''
    
    CSV内容 = 字典转CSV(合并数据, 分隔符)
    
    if 输出文件:
        with open(输出文件, 'w', encoding=编码) as f:
            f.write(CSV内容)
    
    return CSV内容


def CSV分割(文件路径: str, 每文件行数: int = 1000, 输出前缀: str = 'split_', 编码: str = 'utf-8', 分隔符: str = ',') -> List[str]:
    """分割CSV文件"""
    数据 = 读取CSV列表(文件路径, 编码, 分隔符)
    表头 = 数据[0] if 数据 else []
    数据行 = 数据[1:] if len(数据) > 1 else []
    
    输出文件列表 = []
    文件索引 = 0
    
    for i in range(0, len(数据行), 每文件行数):
        分割数据 = [表头] + 数据行[i:i + 每文件行数]
        输出文件 = f'{输出前缀}{文件索引}.csv'
        写入CSV列表(输出文件, 分割数据, 编码, 分隔符)
        输出文件列表.append(输出文件)
        文件索引 += 1
    
    return 输出文件列表


def CSV验证(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> bool:
    """验证CSV文件格式"""
    try:
        数据 = 读取CSV(文件路径, 编码, 分隔符)
        return len(数据) >= 0
    except Exception:
        return False


def CSV统计(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> Dict[str, Any]:
    """统计CSV文件信息"""
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    
    统计 = {
        '行数': len(数据),
        '列数': len(数据[0].keys()) if 数据 else 0,
        '表头': list(数据[0].keys()) if 数据 else [],
    }
    
    for 列 in 统计['表头']:
        数值列 = []
        非空计数 = 0
        
        for 行 in 数据:
            值 = 行.get(列, '')
            if 值:
                非空计数 += 1
                try:
                    数值列.append(float(值))
                except ValueError:
                    pass
        
        if 数值列:
            统计[f'{列}_最小值'] = min(数值列)
            统计[f'{列}_最大值'] = max(数值列)
            统计[f'{列}_均值'] = sum(数值列) / len(数值列)
        统计[f'{列}_非空数'] = 非空计数
    
    return 统计


def CSV删除列(文件路径: str, 列名: str, 输出文件: str = None, 编码: str = 'utf-8', 分隔符: str = ',') -> str:
    """删除CSV列"""
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    
    for 行 in 数据:
        if 列名 in 行:
            del 行[列名]
    
    CSV内容 = 字典转CSV(数据, 分隔符)
    
    if 输出文件:
        with open(输出文件, 'w', encoding=编码) as f:
            f.write(CSV内容)
    else:
        写入CSV(文件路径, 数据, 编码, 分隔符)
    
    return CSV内容


def CSV重命名列(文件路径: str, 旧列名: str, 新列名: str, 输出文件: str = None, 编码: str = 'utf-8', 分隔符: str = ',') -> str:
    """重命名CSV列"""
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    
    for 行 in 数据:
        if 旧列名 in 行:
            行[新列名] = 行.pop(旧列名)
    
    CSV内容 = 字典转CSV(数据, 分隔符)
    
    if 输出文件:
        with open(输出文件, 'w', encoding=编码) as f:
            f.write(CSV内容)
    else:
        写入CSV(文件路径, 数据, 编码, 分隔符)
    
    return CSV内容


def CSV去重(文件路径: str, 键: str = None, 输出文件: str = None, 编码: str = 'utf-8', 分隔符: str = ',') -> str:
    """CSV去重"""
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    
    if 键:
        已见 = set()
        结果 = []
        for 行 in 数据:
            值 = 行.get(键, '')
            if 值 not in 已见:
                已见.add(值)
                结果.append(行)
        数据 = 结果
    else:
        已见 = set()
        结果 = []
        for 行 in 数据:
            键值 = tuple(sorted(行.items()))
            if 键值 not in 已见:
                已见.add(键值)
                结果.append(行)
        数据 = 结果
    
    CSV内容 = 字典转CSV(数据, 分隔符)
    
    if 输出文件:
        with open(输出文件, 'w', encoding=编码) as f:
            f.write(CSV内容)
    else:
        写入CSV(文件路径, 数据, 编码, 分隔符)
    
    return CSV内容


def CSV填充缺失值(文件路径: str, 填充值: Any = '', 输出文件: str = None, 编码: str = 'utf-8', 分隔符: str = ',') -> str:
    """填充CSV缺失值"""
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    
    for 行 in 数据:
        for 列 in 行:
            if 行[列] == '' or 行[列] is None:
                行[列] = 填充值
    
    CSV内容 = 字典转CSV(数据, 分隔符)
    
    if 输出文件:
        with open(输出文件, 'w', encoding=编码) as f:
            f.write(CSV内容)
    else:
        写入CSV(文件路径, 数据, 编码, 分隔符)
    
    return CSV内容


def CSV转HTML表格(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> str:
    """CSV转HTML表格"""
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    
    if not 数据:
        return '<table></table>'
    
    表头 = list(数据[0].keys())
    表头行 = ''.join(f'<th>{列}</th>' for 列 in 表头)
    
    行内容 = []
    for 行 in 数据:
        单元格 = ''.join(f'<td>{行.get(列, "")}</td>' for 列 in 表头)
        行内容.append(f'<tr>{单元格}</tr>')
    
    return f'<table>\n<thead><tr>{表头行}</tr></thead>\n<tbody>\n{"".join(行内容)}\n</tbody>\n</table>'


def CSV转Markdown表格(文件路径: str, 编码: str = 'utf-8', 分隔符: str = ',') -> str:
    """CSV转Markdown表格"""
    数据 = 读取CSV(文件路径, 编码, 分隔符)
    
    if not 数据:
        return ''
    
    表头 = list(数据[0].keys())
    对齐线 = '|' + '|'.join(['---'] * len(表头)) + '|'
    
    行 = [f"|{'|'.join(表头)}|", 对齐线]
    
    for 行内容 in 数据:
        单元格 = []
        for 列 in 表头:
            值 = str(行内容.get(列, ''))
            值 = 值.replace('|', '\\|')
            单元格.append(值)
        行.append(f"|{'|'.join(单元格)}|")
    
    return '\n'.join(行)


# =============================================================================
# 合并自CSV.py的独有函数
# =============================================================================

def 读取TSV(文件路径: str, 编码: str = 'utf-8') -> List[Dict[str, str]]:
    """读取TSV文件（制表符分隔）"""
    return 读取CSV(文件路径, 编码=编码, 分隔符='\t')


def 写入TSV(文件路径: str, 数据: List[Dict[str, Any]], 表头: List[str] = None, 编码: str = 'utf-8') -> None:
    """写入TSV文件（制表符分隔）"""
    写入CSV(文件路径, 数据, 编码=编码, 分隔符='\t')