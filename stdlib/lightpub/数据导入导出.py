"""
数据导入导出 — lightpub 桥接模块

基于 Python csv / json / xml / yaml / configparser 库封装，函数名对齐上游 duanpub（段言时期）packages/数据导入导出/源.duan。

上游 duanpub 原始包通过 C FFI 实现多种数据格式解析，
本桥接模块用 Python 标准库替代，提供等价的读写功能。
"""

import csv as _csv
import json as _json
import io as _io
import os as _os
import xml.etree.ElementTree as _ET
import configparser as _configparser


# =============================================================================
# CSV 读取选项
# =============================================================================

class CSV读取选项:
    """CSV 读取选项"""
    def __init__(self, 分隔符=',', 引号字符='"', 转义字符=None, 有表头=True, 编码='utf-8'):
        self.分隔符 = 分隔符
        self.引号字符 = 引号字符
        self.转义字符 = 转义字符
        self.有表头 = 有表头
        self.编码 = 编码


class CSV写入选项:
    """CSV 写入选项"""
    def __init__(self, 分隔符=',', 引号字符='"', 行终止符='\r\n', 编码='utf-8'):
        self.分隔符 = 分隔符
        self.引号字符 = 引号字符
        self.行终止符 = 行终止符
        self.编码 = 编码


def 创建读取选项(分隔符=',', 引号字符='"', 转义字符=None, 有表头=True, 编码='utf-8'):
    """创建 CSV 读取选项对象"""
    return CSV读取选项(分隔符=分隔符, 引号字符=引号字符, 转义字符=转义字符, 有表头=有表头, 编码=编码)


def 创建写入选项(分隔符=',', 引号字符='"', 行终止符='\r\n', 编码='utf-8'):
    """创建 CSV 写入选项对象"""
    return CSV写入选项(分隔符=分隔符, 引号字符=引号字符, 行终止符=行终止符, 编码=编码)


def 读取CSV文本(文本, 选项=None):
    """读取 CSV 文本，返回二维列表"""
    if not 文本:
        return []
    try:
        sep = 选项.分隔符 if 选项 else ','
        reader = _csv.reader(_io.StringIO(文本), delimiter=sep)
        return [row for row in reader]
    except Exception as e:
        raise Exception("读取CSV文本失败: " + str(e))


def 写入CSV文本(数据, 选项=None):
    """将二维列表写入 CSV 文本"""
    if not 数据:
        return ''
    try:
        output = _io.StringIO()
        sep = 选项.分隔符 if 选项 else ','
        writer = _csv.writer(output, delimiter=sep, lineterminator='\n')
        for row in 数据:
            writer.writerow(row)
        return output.getvalue().rstrip('\n')
    except Exception as e:
        raise Exception("写入CSV文本失败: " + str(e))


def 读取TSV(文本, 选项=None):
    """读取 TSV 文本"""
    if not 文本:
        return []
    try:
        reader = _csv.reader(_io.StringIO(文本), delimiter='\t')
        return [row for row in reader]
    except Exception as e:
        raise Exception("读取TSV失败: " + str(e))


def 写入TSV(数据):
    """将二维列表写入 TSV 文本"""
    if not 数据:
        return ''
    try:
        output = _io.StringIO()
        writer = _csv.writer(output, delimiter='\t', lineterminator='\n')
        for row in 数据:
            writer.writerow(row)
        return output.getvalue().rstrip('\n')
    except Exception as e:
        raise Exception("写入TSV失败: " + str(e))


def skip_whitespace(文本):
    """跳过空白字符，返回非空白起始索引"""
    if not 文本:
        return 0
    for i, ch in enumerate(文本):
        if ch not in ' \t\n\r':
            return i
    return len(文本)


# =============================================================================
# JSON 解析
# =============================================================================

def parse_json_string(文本):
    """解析 JSON 字符串"""
    try:
        return _json.loads(文本)
    except _json.JSONDecodeError as e:
        raise Exception("parse_json_string失败: " + str(e))


def parse_json_number(文本):
    """解析 JSON 数字"""
    try:
        return _json.loads(文本)
    except (_json.JSONDecodeError, ValueError) as e:
        raise Exception("parse_json_number失败: " + str(e))


def parse_json_bool(文本):
    """解析 JSON 布尔值"""
    s = 文本.strip().lower()
    if s == 'true':
        return True
    elif s == 'false':
        return False
    raise Exception("parse_json_bool失败: 无效的布尔值 " + 文本)


def parse_json_null(文本):
    """解析 JSON null"""
    if 文本.strip() == 'null':
        return None
    raise Exception("parse_json_null失败: 无效的null值")


def parse_json_array(文本):
    """解析 JSON 数组"""
    try:
        result = _json.loads(文本)
        if not isinstance(result, list):
            raise Exception("parse_json_array失败: 不是数组")
        return result
    except _json.JSONDecodeError as e:
        raise Exception("parse_json_array失败: " + str(e))


def parse_json_object(文本):
    """解析 JSON 对象"""
    try:
        result = _json.loads(文本)
        if not isinstance(result, dict):
            raise Exception("parse_json_object失败: 不是对象")
        return result
    except _json.JSONDecodeError as e:
        raise Exception("parse_json_object失败: " + str(e))


def parse_json_value(文本):
    """解析 JSON 值"""
    try:
        return _json.loads(文本)
    except _json.JSONDecodeError as e:
        raise Exception("parse_json_value失败: " + str(e))


def 读取JSON文本(文本):
    """读取 JSON 文本"""
    return parse_json_value(文本)


def json_to_string(值, 缩进=None):
    """将 JSON 值转换为字符串"""
    try:
        return _json.dumps(值, indent=缩进, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise Exception("json_to_string失败: " + str(e))


def 写入JSON文本(值, 缩进=None):
    """将值写入为 JSON 文本"""
    return json_to_string(值, 缩进=缩进)


def 读取JSON行(文本):
    """读取 JSON Lines 格式（每行一个 JSON 对象）"""
    if not 文本:
        return []
    try:
        result = []
        for line in 文本.strip().split('\n'):
            line = line.strip()
            if line:
                result.append(_json.loads(line))
        return result
    except _json.JSONDecodeError as e:
        raise Exception("读取JSON行失败: " + str(e))


def 写入JSON行(数据):
    """写入 JSON Lines 格式"""
    if not 数据:
        return ''
    try:
        lines = [_json.dumps(item, ensure_ascii=False) for item in 数据]
        return '\n'.join(lines)
    except (TypeError, ValueError) as e:
        raise Exception("写入JSON行失败: " + str(e))


# =============================================================================
# XML 解析
# =============================================================================

class XMLNode:
    """XML 节点"""
    def __init__(self, elem=None):
        self._elem = elem

    def 获取属性(self, 名称):
        if self._elem is not None:
            return self._elem.get(名称, '')
        return ''

    def 获取子节点(self, 名称):
        if self._elem is not None:
            child = self._elem.find(名称)
            if child is not None:
                return XMLNode(child)
        return None

    def 获取所有子节点(self):
        if self._elem is not None:
            return [XMLNode(child) for child in self._elem]
        return []

    def 获取文本(self):
        if self._elem is not None:
            return self._elem.text or ''
        return ''


def parse_xml(文本):
    """解析 XML 文本，返回 XMLNode 对象"""
    if not 文本:
        raise Exception("parse_xml失败: 文本为空")
    try:
        root = _ET.fromstring(文本)
        return XMLNode(root)
    except _ET.ParseError as e:
        raise Exception("parse_xml失败: " + str(e))


def XMLNode_获取属性(node, 名称):
    """获取 XML 节点属性"""
    return node.获取属性(名称) if node else ''


def XMLNode_获取子节点(node, 名称):
    """获取 XML 子节点"""
    return node.获取子节点(名称) if node else None


def XMLNode_获取所有子节点(node):
    """获取所有 XML 子节点"""
    return node.获取所有子节点() if node else []


def XMLNode_获取文本(node):
    """获取 XML 节点文本"""
    return node.获取文本() if node else ''


def 读取XML文本(文本):
    """读取 XML 文本，返回 XMLNode"""
    return parse_xml(文本)


# =============================================================================
# YAML 解析
# =============================================================================

def parse_yaml(文本):
    """解析 YAML 文本（回退到 JSON 解析，YAML 是 JSON 超集）"""
    if not 文本:
        return None
    try:
        # 尝试作为 JSON 解析
        return _json.loads(文本)
    except _json.JSONDecodeError:
        pass
    # 简单 YAML 键值对解析
    try:
        result = {}
        for line in 文本.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                key, _, val = line.partition(':')
                key = key.strip()
                val = val.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val == 'true':
                    val = True
                elif val == 'false':
                    val = False
                elif val == 'null' or val == '~':
                    val = None
                else:
                    try:
                        if '.' in val:
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        pass
                result[key] = val
        return result if result else 文本
    except Exception as e:
        raise Exception("parse_yaml失败: " + str(e))


def 读取YAML文本(文本):
    """读取 YAML 文本"""
    return parse_yaml(文本)


def 写入YAML文本(数据):
    """将数据写入 YAML 格式"""
    if data is None:
        return 'null\n'
    if isinstance(data, bool):
        return 'true\n' if data else 'false\n'
    if isinstance(data, (int, float)):
        return str(data) + '\n'
    if isinstance(data, str):
        if '\n' in data:
            return '|\n  ' + data.replace('\n', '\n  ') + '\n'
        return data + '\n'
    if isinstance(data, dict):
        lines = []
        for key, val in data.items():
            val_str = 写入YAML文本(val).strip()
            if '\n' in val_str:
                lines.append(f"{key}: {val_str}")
            else:
                lines.append(f"{key}: {val_str}")
        return '\n'.join(lines) + '\n' if lines else '{}\n'
    if isinstance(data, (list, tuple)):
        lines = []
        for item in data:
            val_str = 写入YAML文本(item).strip()
            for line in val_str.split('\n'):
                lines.append(f"- {line}")
        return '\n'.join(lines) + '\n' if lines else '[]\n'
    return str(data) + '\n'


# =============================================================================
# Excel 读写
# =============================================================================

class ExcelWorkbook:
    """Excel 工作簿"""
    def __init__(self):
        self._sheets = {}

    def 添加工作表(self, 名称, 数据):
        self._sheets[名称] = 数据

    def 获取工作表(self, 名称):
        return self._sheets.get(名称, [])

    def 获取工作表名称列表(self):
        return list(self._sheets.keys())


def 读取Excel(文件路径, 工作表名=None):
    """读取 Excel 文件（回退到 CSV 解析）"""
    if not 文件路径:
        raise Exception("读取Excel失败: 文件路径为空")
    try:
        # 尝试作为 CSV 读取
        with open(文件路径, 'r', encoding='utf-8') as f:
            reader = _csv.reader(f)
            return [row for row in reader]
    except FileNotFoundError:
        raise Exception("读取Excel失败: 文件不存在 " + 文件路径)
    except Exception as e:
        raise Exception("读取Excel失败: " + str(e))


def 读取Excel多工作表(文件路径):
    """读取 Excel 文件的多工作表"""
    if not 文件路径:
        raise Exception("读取Excel多工作表失败: 文件路径为空")
    try:
        workbook = ExcelWorkbook()
        with open(文件路径, 'r', encoding='utf-8') as f:
            reader = _csv.reader(f)
            data = [row for row in reader]
        workbook.添加工作表('Sheet1', data)
        return workbook
    except FileNotFoundError:
        raise Exception("读取Excel多工作表失败: 文件不存在 " + 文件路径)
    except Exception as e:
        raise Exception("读取Excel多工作表失败: " + str(e))


def 写入Excel(文件路径, 数据, 工作表名='Sheet1'):
    """写入 Excel 文件（以 CSV 格式写入）"""
    if not 文件路径:
        raise Exception("写入Excel失败: 文件路径为空")
    try:
        with open(文件路径, 'w', encoding='utf-8', newline='') as f:
            writer = _csv.writer(f)
            for row in 数据:
                writer.writerow(row)
    except OSError as e:
        raise Exception("写入Excel失败: " + str(e))


def 创建工作簿():
    """创建 Excel 工作簿对象"""
    return ExcelWorkbook()


def ExcelWorkbook_添加工作表(wb, 名称, 数据):
    """向工作簿添加工作表"""
    if wb:
        wb.添加工作表(名称, 数据)


def ExcelWorkbook_获取工作表(wb, 名称):
    """获取工作簿中的工作表"""
    if wb:
        return wb.获取工作表(名称)
    return []


def ExcelWorkbook_获取工作表名称列表(wb):
    """获取工作簿中所有工作表名称"""
    if wb:
        return wb.获取工作表名称列表()
    return []


# =============================================================================
# 固定宽度文本
# =============================================================================

def 读取固定宽度(文本, 宽度列表):
    """读取固定宽度文本"""
    if not 文本 or not 宽度列表:
        return []
    try:
        result = []
        for line in 文本.split('\n'):
            line = line.rstrip('\r')
            if not line:
                continue
            row = []
            pos = 0
            for w in 宽度列表:
                row.append(line[pos:pos + w].strip())
                pos += w
            result.append(row)
        return result
    except Exception as e:
        raise Exception("读取固定宽度失败: " + str(e))


def 写入固定宽度(数据, 宽度列表):
    """写入固定宽度文本"""
    if not 数据 or not 宽度列表:
        return ''
    try:
        lines = []
        for row in 数据:
            parts = []
            for i, w in enumerate(宽度列表):
                val = str(row[i]) if i < len(row) else ''
                if len(val) > w:
                    val = val[:w]
                parts.append(val.ljust(w))
            lines.append(''.join(parts))
        return '\n'.join(lines)
    except Exception as e:
        raise Exception("写入固定宽度失败: " + str(e))


# =============================================================================
# INI 配置
# =============================================================================

def 读取INI(文本):
    """读取 INI 格式文本，返回字典"""
    if not 文本:
        return {}
    try:
        config = _configparser.ConfigParser()
        config.read_string(文本)
        result = {}
        for section in config.sections():
            result[section] = dict(config[section])
        return result
    except _configparser.Error as e:
        raise Exception("读取INI失败: " + str(e))


def 写入INI(数据):
    """将字典写入 INI 格式文本"""
    if not 数据:
        return ''
    try:
        config = _configparser.ConfigParser()
        for section, values in 数据.items():
            config[section] = {}
            for key, val in values.items():
                config[section][key] = str(val)
        output = _io.StringIO()
        config.write(output)
        return output.getvalue()
    except Exception as e:
        raise Exception("写入INI失败: " + str(e))


# =============================================================================
# 属性文件（Java .properties）
# =============================================================================

def 读取属性文件(文本):
    """读取属性文件（key=value 格式）"""
    if not 文本:
        return {}
    try:
        result = {}
        for line in 文本.split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('!'):
                continue
            if '=' in line:
                key, _, val = line.partition('=')
            elif ':' in line:
                key, _, val = line.partition(':')
            else:
                continue
            result[key.strip()] = val.strip()
        return result
    except Exception as e:
        raise Exception("读取属性文件失败: " + str(e))


def 写入属性文件(数据):
    """将字典写入属性文件格式"""
    if not 数据:
        return ''
    try:
        lines = []
        for key, val in 数据.items():
            lines.append(f"{key}={val}")
        return '\n'.join(lines)
    except Exception as e:
        raise Exception("写入属性文件失败: " + str(e))


# =============================================================================
# Markdown 表格
# =============================================================================

def 读取Markdown表格(文本):
    """读取 Markdown 表格，返回二维列表"""
    if not 文本:
        return []
    try:
        lines = [line.strip() for line in 文本.split('\n') if line.strip()]
        if not lines:
            return []
        # 跳过分隔行（|---|）
        data_lines = [line for line in lines if not line.startswith('|') or not line.replace('|', '').replace('-', '').replace(':', '').strip() == '' or line.count('|') > 2]
        # 过滤真正的数据行
        data_lines = []
        for line in lines:
            if line.startswith('|') and line.endswith('|'):
                # 检查是否分隔行
                content = line[1:-1].replace('|', '').strip()
                if content and not all(c in '-:' for c in content):
                    data_lines.append(line)
        result = []
        for line in data_lines:
            row = [cell.strip() for cell in line.strip('|').split('|')]
            result.append(row)
        return result
    except Exception as e:
        raise Exception("读取Markdown表格失败: " + str(e))


def 写入Markdown表格(数据):
    """将二维列表写入 Markdown 表格格式"""
    if not 数据:
        return ''
    try:
        lines = []
        if 数据:
            # 表头
            lines.append('| ' + ' | '.join(str(cell) for cell in 数据[0]) + ' |')
            # 分隔行
            lines.append('| ' + ' | '.join('---' for _ in 数据[0]) + ' |')
            # 数据行
            for row in 数据[1:]:
                lines.append('| ' + ' | '.join(str(cell) for cell in row) + ' |')
        return '\n'.join(lines)
    except Exception as e:
        raise Exception("写入Markdown表格失败: " + str(e))


# =============================================================================
# 格式检测
# =============================================================================

def 检测文件格式(文件路径):
    """检测文件格式，返回格式名称"""
    if not 文件路径:
        raise Exception("检测文件格式失败: 文件路径为空")
    try:
        _, ext = _os.path.splitext(文件路径)
        ext = ext.lower()
        格式映射 = {
            '.csv': 'csv', '.tsv': 'tsv', '.json': 'json',
            '.xml': 'xml', '.yaml': 'yaml', '.yml': 'yaml',
            '.ini': 'ini', '.properties': 'properties',
            '.md': 'markdown', '.xlsx': 'excel', '.xls': 'excel',
            '.txt': 'text',
        }
        return 格式映射.get(ext, 'unknown')
    except Exception as e:
        raise Exception("检测文件格式失败: " + str(e))


def 检测CSV分隔符(文本):
    """检测 CSV 分隔符"""
    if not 文本:
        return ','
    try:
        候选 = [',', '\t', ';', '|']
        最佳 = ','
        最佳得分 = -1
        first_line = 文本.split('\n')[0] if '\n' in 文本 else 文本
        for d in 候选:
            得分 = first_line.count(d)
            if 得分 > 最佳得分:
                最佳得分 = 得分
                最佳 = d
        return 最佳
    except Exception:
        return ','


def 检测编码(文件路径):
    """检测文件编码"""
    if not 文件路径:
        raise Exception("检测编码失败: 文件路径为空")
    try:
        with open(文件路径, 'rb') as f:
            raw = f.read(4)
        # BOM 检测
        if raw[:3] == b'\xef\xbb\xbf':
            return 'utf-8-sig'
        if raw[:4] == b'\xff\xfe\x00\x00' or raw[:4] == b'\x00\x00\xfe\xff':
            return 'utf-32'
        if raw[:2] == b'\xff\xfe' or raw[:2] == b'\xfe\xff':
            return 'utf-16'
        return 'utf-8'
    except Exception as e:
        raise Exception("检测编码失败: " + str(e))


def 获取文件信息(文件路径):
    """获取文件信息"""
    if not 文件路径:
        raise Exception("获取文件信息失败: 文件路径为空")
    try:
        stat = _os.stat(文件路径)
        return {
            '大小': stat.st_size,
            '修改时间': stat.st_mtime,
            '创建时间': stat.st_ctime,
            '格式': 检测文件格式(文件路径),
        }
    except FileNotFoundError:
        raise Exception("获取文件信息失败: 文件不存在 " + 文件路径)
    except Exception as e:
        raise Exception("获取文件信息失败: " + str(e))