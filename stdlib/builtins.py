"""
光明标准库 - 内置函数实现

提供文件I/O、路径操作、系统函数等核心功能
"""

import os
import sys
import math
import random
import statistics
import time as _time_module
from datetime import datetime as _datetime_class
from pathlib import Path
from typing import List, Optional, Union


# =============================================================================
# 文件I/O函数
# =============================================================================

# =============================================================================
# 地板转发（第九轮 S2）
# =============================================================================
# 本文件是「地板」：src/code_generator.py 会把它当 _light_builtin 注入每一份生成
# 产物，所以每个光明程序都站在它上面。它没有同名 .light，因此不进 bootstrap_rate
# 的分母 —— tools/ci/floor_bootstrap.py 专门量它。
#
# 转发的三条硬规矩（都踩过坑）：
#   1. **惰性**：`import` 必须写在函数体内。`.light` 模块由导入钩子编译执行，其产物
#      序言又会把本文件当 _light_builtin 加载回来（src/code_generator.py:735-741）；
#      顶层 import 会在「地板还没建完」时触发这条回路。写在体内，首次调用时两边都已就位。
#   2. **不静默兜底**：转发失败就让它抛。悄悄回落到 Python 会让门禁报的「已搬迁」
#      变成假话 —— 门禁只看得见函数体里有那个模块名，看不见运行期究竟跑了谁。
#   3. **先证等价再接线**：只有拿两版在同一批输入（含边界与错误路径）上对跑过、
#      逐条一致的才接。口径有差的要么显式对齐（见 分割字符串），要么不接并记账。


# 转发用的两件准备工作放在模块顶层，**故意不包成函数**：
#   `tools/ci/floor_bootstrap.py` 用 ast 数本文件的顶层函数当分母，多一个私有
#   helper 就会被判「清单漏登记」而判红，而它既不是可搬迁的地板函数、也不是
#   native_required 真边界（那份名单新增即红），清单里没有它的位置。
# 这两句本身也确实是「装地板」的动作而不是地板的一部分：
#   1. 把本目录放上 sys.path，让 `import <纯光明模块名>` 找得到；
#   2. 装上光明导入钩子（幂等，重复 install 不叠加查找器）。
# 在 `light run` 与生成产物里钩子早已装好（src/code_generator.py:714-719），
# 这两句是给「直接 import stdlib.builtins 的 Python 调用方」（测试、工具脚本）兜底。
_光明目录 = os.path.dirname(os.path.abspath(__file__))
if _光明目录 not in sys.path:
    sys.path.insert(0, _光明目录)
import _light_import_hook as _光明钩子
_光明钩子.install([_光明目录])


def 读取文件(path: str, encoding: str = 'utf-8') -> str:
    """
    读取文件内容
    
    参数:
        path: 文件路径
        encoding: 编码（默认utf-8）
    
    返回:
        文件内容
    
    异常:
        RuntimeError: 文件读取失败
    """
    try:
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        raise RuntimeError(f"文件不存在: '{path}'")
    except PermissionError:
        raise RuntimeError(f"无权限读取文件: '{path}'")
    except Exception as e:
        raise RuntimeError(f"读取文件失败 '{path}': {e}")


def _读文件(path: str) -> str:
    """内部用：读取文件内容（简化版）"""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def 写入文件(path: str, content: str, encoding: str = 'utf-8') -> None:
    """
    写入文件内容
    
    参数:
        path: 文件路径
        content: 文件内容
        encoding: 编码（默认utf-8）
    
    异常:
        RuntimeError: 文件写入失败
    """
    try:
        # 确保目录存在
        dir_path = os.path.dirname(path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
    except PermissionError:
        raise RuntimeError(f"无权限写入文件: '{path}'")
    except Exception as e:
        raise RuntimeError(f"写入文件失败 '{path}': {e}")


def 追加文件(path: str, content: str, encoding: str = 'utf-8') -> None:
    """
    追加内容到文件
    
    参数:
        path: 文件路径
        content: 追加内容
        encoding: 编码（默认utf-8）
    """
    try:
        with open(path, 'a', encoding=encoding) as f:
            f.write(content)
    except Exception as e:
        raise RuntimeError(f"追加文件失败 '{path}': {e}")


def 文件存在(path: str) -> bool:
    """检查文件是否存在"""
    return os.path.isfile(path)


def 是文件(path: str) -> bool:
    """检查是否为文件"""
    return os.path.isfile(path)


def 目录存在(path: str) -> bool:
    """检查目录是否存在"""
    return os.path.isdir(path)


def 路径存在(path: str) -> bool:
    """检查路径是否存在（文件或目录）"""
    return os.path.exists(path)


def 创建目录(path: str) -> None:
    """
    创建目录
    
    参数:
        path: 目录路径
    
    说明:
        自动创建所有父目录
    """
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"创建目录失败 '{path}': {e}")


def 删除文件(path: str) -> None:
    """删除文件"""
    try:
        os.remove(path)
    except FileNotFoundError:
        raise RuntimeError(f"文件不存在: '{path}'")
    except Exception as e:
        raise RuntimeError(f"删除文件失败 '{path}': {e}")


def 删除目录(path: str) -> None:
    """删除空目录"""
    try:
        os.rmdir(path)
    except Exception as e:
        raise RuntimeError(f"删除目录失败 '{path}': {e}")


def 列出目录(path: str = '.') -> List[str]:
    """
    列出目录内容
    
    参数:
        path: 目录路径（默认当前目录）
    
    返回:
        文件名列表
    """
    try:
        return os.listdir(path)
    except Exception as e:
        raise RuntimeError(f"列出目录失败 '{path}': {e}")


def 列出文件(path: str = '.') -> List[str]:
    """
    列出目录中的文件（不包含子目录）
    
    参数:
        path: 目录路径（默认当前目录）
    
    返回:
        文件名列表（仅文件）
    """
    try:
        return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    except Exception as e:
        raise RuntimeError(f"列出文件失败 '{path}': {e}")


def 文件大小(path: str) -> int:
    """
    获取文件大小（字节）
    
    参数:
        path: 文件路径
    
    返回:
        文件大小（字节）
    """
    try:
        return os.path.getsize(path)
    except Exception as e:
        raise RuntimeError(f"获取文件大小失败 '{path}': {e}")


# =============================================================================
# 路径操作函数
# =============================================================================

def 绝对路径(path: str) -> str:
    """获取绝对路径"""
    return os.path.abspath(path)


def 连接路径(*paths: str) -> str:
    """连接多个路径

    **替身已就位但刻意未转发。** 纯光明实现在 `stdlib/内置核心路径.light:24`，
    与 `posixpath` 逐条等价（差分测试 tests/unit/test_地板搬迁_路径_S2.py，466 条）。
    不转发的原因是实测出来的硬阻断，不是没写完：
    `stdlib/操作系统.light:26-31 本机平台` 把「`连接路径("甲","乙")` 里有没有反斜杠」
    当作**平台判定的唯一探针**。换成只认 `/` 的 POSIX 语义后，Windows 上
    `本机平台()` 返回 `posix`，`路径护栏` / `代理工具集` / `路径运算` / harness 沙箱
    连带 46 条测试转红（实测数字，见交付报告 §12.4）。
    要转发，得先给平台判定换一个不依赖本函数的原语 —— 那是另一条待裁决的口径。
    """
    return os.path.join(*paths)


def 目录名(path: str) -> str:
    """获取路径的目录部分（替身在 stdlib/内置核心路径.light:48，未转发，理由见 连接路径）"""
    return os.path.dirname(path)


def 文件名(path: str) -> str:
    """获取路径的文件名部分（替身在 stdlib/内置核心路径.light:59，未转发，理由见 连接路径）"""
    return os.path.basename(path)


def 扩展名(path: str) -> str:
    """获取文件扩展名（替身在 stdlib/内置核心路径.light:95，未转发，理由见 连接路径）"""
    _, ext = os.path.splitext(path)
    return ext


def 分割路径(path: str) -> tuple:
    """分割路径为(目录, 文件名)（替身在 stdlib/内置核心路径.light:66，未转发，理由见 连接路径）"""
    return os.path.split(path)


def 分割扩展名(path: str) -> tuple:
    """分割路径为(主名, 扩展名)（替身在 stdlib/内置核心路径.light:82，未转发，理由见 连接路径）"""
    return os.path.splitext(path)




# =============================================================================
# 系统函数
# =============================================================================

def 环境变量(name: str, default: str = None) -> Optional[str]:
    """
    获取环境变量
    
    参数:
        name: 环境变量名
        default: 默认值
    
    返回:
        环境变量值或默认值
    """
    return os.environ.get(name, default)


def 设置环境变量(name: str, value: str) -> None:
    """设置环境变量"""
    os.environ[name] = value


def 参数列表() -> List[str]:
    """获取命令行参数列表"""
    return sys.argv


def 退出程序(code: int = 0) -> None:
    """退出程序"""
    sys.exit(code)


def 当前目录() -> str:
    """获取当前工作目录"""
    return os.getcwd()


def 切换目录(path: str) -> None:
    """切换工作目录"""
    try:
        os.chdir(path)
    except Exception as e:
        raise RuntimeError(f"切换目录失败 '{path}': {e}")


def 执行命令(command: str) -> int:
    """
    执行系统命令
    
    参数:
        command: 命令字符串
    
    返回:
        退出码
    """
    return os.system(command)


def 移动文件系统(source: str, target: str) -> None:
    """
    移动文件或目录
    
    参数:
        source: 源路径
        target: 目标路径
    """
    import shutil
    shutil.move(source, target)


# =============================================================================
# 标准输入输出（stdio）
# =============================================================================

def 读取行() -> str:
    """
    从标准输入读取一行

    返回:
        读取的字符串（不含换行符）
    """
    # 注意：Windows subprocess 在 text 模式下会将 \r\n 转换为 \r\r\n
    # 因此需要同时去除 \r 和 \n
    return sys.stdin.readline().rstrip('\r\n')


def 读取N字节(字节数: int) -> str:
    """
    从标准输入读取指定数量的字节
    
    参数:
        字节数: 要读取的字节数
    
    返回:
        读取的字符串
    """
    return sys.stdin.read(字节数)


def 写入输出(text: str) -> None:
    """
    向标准输出写入文本（不含换行）
    
    参数:
        text: 要写入的文本
    """
    sys.stdout.write(text)
    sys.stdout.flush()


def 打印输出(text: str) -> None:
    """
    向标准输出打印文本并换行
    
    参数:
        text: 要打印的文本
    """
    print(text, flush=True)


def 刷新输出() -> None:
    """强制刷新标准输出缓冲区"""
    sys.stdout.flush()


def 写入错误(text: str) -> None:
    """向标准错误写入文本"""
    sys.stderr.write(text)
    sys.stderr.flush()


def 打印错误(text: str) -> None:
    """向标准错误打印文本并换行"""
    print(text, file=sys.stderr, flush=True)


# =============================================================================
# JSON 处理
# =============================================================================

def 解析JSON(text: str) -> object:
    """解析 JSON 字符串为光明值（地板已搬迁：真身 stdlib/JSON.light:13 → JSON核心.light 纯光明递归下降）

    不需要在这里包 try/except：JSON核心.light 的 14 个解析抛点已统一成
    `抛出 运行时错误("JSON 解析失败: …")`，异常类型（RuntimeError）与消息前缀
    与搬迁前逐字一致。只有消息尾部不同（中文描述 vs CPython 扫描器的英文串 + 行列号）。
    """
    import JSON
    return JSON.解析JSON(text)


def 序列化JSON(value: object, 缩进: Optional[int] = None) -> str:
    """将光明值序列化为 JSON 字符串（地板已搬迁：真身 stdlib/JSON.light:19）

    `缩进=None` 这个默认值只能留在本签名里：光明侧的 `接收 值, 缩进 = 空` 表达的是
    同一语义，但 None 与 0 必须区分（None=紧凑、0=换行零缩进），交由光明门面判定。
    """
    import JSON
    return JSON.序列化JSON(value, 缩进)


def 美化JSON(value: object) -> str:
    """美化 JSON 输出（带缩进）（地板已搬迁：真身 stdlib/JSON.light:25）"""
    import JSON
    return JSON.美化JSON(value)



# =============================================================================
# 字符串工具函数
# =============================================================================

def 转整数(text: str) -> int:
    """将字符串转换为整数（地板已搬迁：真身 stdlib/内置核心转换.light:15）"""
    import 内置核心转换
    return 内置核心转换.转整数(text)


def 转浮点(text: str) -> float:
    """将字符串转换为浮点数（地板已搬迁：真身 stdlib/内置核心转换.light:22）"""
    import 内置核心转换
    return 内置核心转换.转浮点(text)


def 转字符串(value) -> str:
    """将值转换为字符串（地板已搬迁：真身 stdlib/内置核心转换.light:29）"""
    import 内置核心转换
    return 内置核心转换.转字符串(value)


def 字符串长度(text: str) -> int:
    """获取字符串长度（地板已搬迁：真身 stdlib/字符串工具轻量.light:137）"""
    import 字符串工具轻量
    return 字符串工具轻量.字符串长度(text)


def 显示宽度(text) -> int:
    """
    返回字符串在等宽终端中的显示宽度。

    中文、日文、韩文及全角字符占 2 个单元格，ASCII 及半角字符占 1 个。
    用于终端边框、表格的对齐（用「显示宽度」替代「字符串长度」算填充）。

    示例:
        显示宽度("中文abc")  -> 7   (中=2, 文=2, a/b/c=1)
        显示宽度("hello")    -> 5
    """
    import unicodedata
    _WIDE_RANGES = (
        (0x1100, 0x115F),   # Hangul Jamo
        (0x2E80, 0xA4CF),   # CJK 部首补充 / 康熙部首 / 表意文字描述符 / 中日韩符号和标点
        (0xAC00, 0xD7A3),   # Hangul 音节
        (0xF900, 0xFAFF),   # CJK 兼容象形文字
        (0xFE30, 0xFE4F),   # CJK 兼容形式
        (0xFF00, 0xFF60),   # 全角 ASCII
        (0xFFE0, 0xFFE6),   # 全角符号
        (0x3000, 0x303F),   # CJK 符号和标点
        (0x3040, 0x30FF),   # 平假名 / 片假名
        (0x3400, 0x4DBF),   # CJK 扩展 A
        (0x4E00, 0x9FFF),   # CJK 统一表意文字
        (0x20000, 0x2FFFF), # CJK 扩展 B+
    )
    width = 0
    for ch in str(text):
        o = ord(ch)
        wide = any(lo <= o <= hi for lo, hi in _WIDE_RANGES)
        if not wide:
            try:
                wide = unicodedata.east_asian_width(ch) in ('W', 'F')
            except Exception:
                wide = False
        width += 2 if wide else 1
    return width


def 字符串获取(text: str, index: int) -> str:
    """获取字符串中指定位置的字符（地板已搬迁：真身 stdlib/内置核心字符串.light:10）"""
    import 内置核心字符串
    return 内置核心字符串.字符串获取(text, index)


def 截取(text: str, start: int, end: int) -> str:
    """截取字符串的一部分（地板已搬迁：真身 stdlib/内置核心字符串.light:14）"""
    import 内置核心字符串
    return 内置核心字符串.截取(text, start, end)


def 分割字符串(text: str, separator: str = None) -> List[str]:
    """分割字符串（地板已搬迁：真身 stdlib/字符串工具轻量.light:50）

    两版口径差必须显式对齐，不能直接透传：
      - 本函数 `separator=None` 表示「按空白切」，光明版用 `""` 表示同一件事；
      - 本函数 `separator=""` 应当抛 `ValueError: empty separator`（这是 Python
        的 `str.split("")` 语义，调用方写空分隔符就是写错了），而光明版会把 `""`
        当成「按空白切」静默返回结果。这里保留原语义，不让搬迁顺手放宽错误检查。
    """
    if separator == "":
        return text.split(separator)
    import 字符串工具轻量
    return 字符串工具轻量.分割字符串(text, "" if separator is None else separator)


def 连接字符串(parts: List[str], separator: str = '') -> str:
    """连接字符串列表（地板已搬迁：真身 stdlib/字符串工具轻量.light:74）

    光明侧已按主线裁决收严到 str.join 口径：非 str 元素抛 TypeError，
    消息逐字为 `sequence item <下标>: expected str instance, <类型名> found`。
    搬迁前的光明替身对非字符串元素做 转字符串 兜底，会把 TypeError 变成静默拼接。
    """
    import 字符串工具轻量
    return 字符串工具轻量.连接字符串(parts, separator)



def 替换字符串(text: str, old: str, new: str) -> str:
    """替换字符串（地板已搬迁：真身 stdlib/字符串工具轻量.light:90）"""
    import 字符串工具轻量
    return 字符串工具轻量.替换字符串(text, old, new)


def 去除空白(text: str) -> str:
    """去除首尾空白（地板已搬迁：真身 stdlib/内置核心字符串.light:18）"""
    import 内置核心字符串
    return 内置核心字符串.去除空白(text)


def 转大写(text: str) -> str:
    """转换为大写（地板已搬迁：真身 stdlib/字符串工具轻量.light:21）"""
    import 字符串工具轻量
    return 字符串工具轻量.转大写(text)


def 转小写(text: str) -> str:
    """转换为小写（地板已搬迁：真身 stdlib/字符串工具轻量.light:24）"""
    import 字符串工具轻量
    return 字符串工具轻量.转小写(text)


def 字符串包含(text: str, substring: str) -> bool:
    """检查字符串是否包含子串（地板已搬迁：真身 stdlib/内置核心字符串.light:22）"""
    import 内置核心字符串
    return 内置核心字符串.字符串包含(text, substring)


def 开头(text: str, prefix: str) -> bool:
    """检查字符串是否以指定前缀开头（地板已搬迁：真身 stdlib/内置核心字符串.light:26）"""
    import 内置核心字符串
    return 内置核心字符串.开头(text, prefix)


def 结尾(text: str, suffix: str) -> bool:
    """检查字符串是否以指定后缀结尾（地板已搬迁：真身 stdlib/内置核心字符串.light:30）"""
    import 内置核心字符串
    return 内置核心字符串.结尾(text, suffix)


def 查找子串(text: str, substring: str) -> int:
    """查找子串位置，未找到返回-1（地板已搬迁：真身 stdlib/内置核心字符串.light:34）"""
    import 内置核心字符串
    return 内置核心字符串.查找子串(text, substring)


def 最后索引(text: str, substring: str) -> int:
    """查找子串最后出现位置，未找到返回-1（地板已搬迁：真身 stdlib/内置核心字符串.light:38）"""
    import 内置核心字符串
    return 内置核心字符串.最后索引(text, substring)


def 替换字符串次数(text: str, old: str, new: str, count: int = -1) -> str:
    """替换字符串，指定替换次数（地板已搬迁：真身 stdlib/内置核心字符串.light:43）

    `count=-1` 这个默认值只能留在本签名里：光明侧写不了负数默认参数
    （`接收 x, y=-1:` 解析失败），所以光明段落收满 4 个参，由这里显式传下去。
    """
    import 内置核心字符串
    return 内置核心字符串.替换字符串次数(text, old, new, count)


def 截取到末尾(text: str, start: int) -> str:
    """从指定位置截取到字符串末尾（地板已搬迁：真身 stdlib/内置核心字符串.light:49）"""
    import 内置核心字符串
    return 内置核心字符串.截取到末尾(text, start)


def 字符串计数(text: str, substring: str) -> int:
    """统计子串出现次数（地板已搬迁：真身 stdlib/内置核心字符串.light:53）"""
    import 内置核心字符串
    return 内置核心字符串.字符串计数(text, substring)


def 字符串重复(text: str, times: int) -> str:
    """重复字符串指定次数（地板已搬迁：真身 stdlib/内置核心字符串.light:57）"""
    import 内置核心字符串
    return 内置核心字符串.字符串重复(text, times)


def 字符串反转(text: str) -> str:
    """反转字符串（地板已搬迁：真身 stdlib/内置核心字符串.light:62）"""
    import 内置核心字符串
    return 内置核心字符串.字符串反转(text)


def 转标题(text: str) -> str:
    """转换为标题格式（首字母大写）（地板已搬迁：真身 stdlib/内置核心字符串.light:71）"""
    import 内置核心字符串
    return 内置核心字符串.转标题(text)


def 去除左侧空白(text: str) -> str:
    """去除左侧空白（地板已搬迁：真身 stdlib/字符串工具轻量.light:96）"""
    import 字符串工具轻量
    return 字符串工具轻量.去除左侧空白(text)


def 去除右侧空白(text: str) -> str:
    """去除右侧空白（地板已搬迁：真身 stdlib/字符串工具轻量.light:99）"""
    import 字符串工具轻量
    return 字符串工具轻量.去除右侧空白(text)


def 字符串对齐居中(text: str, width: int, fillchar: str = ' ') -> str:
    """居中对齐字符串（地板已搬迁：真身 stdlib/内置核心字符串.light:75）"""
    import 内置核心字符串
    return 内置核心字符串.字符串对齐居中(text, width, fillchar)


def 字符串对齐左(text: str, width: int, fillchar: str = ' ') -> str:
    """左对齐字符串（地板已搬迁：真身 stdlib/内置核心字符串.light:79）"""
    import 内置核心字符串
    return 内置核心字符串.字符串对齐左(text, width, fillchar)


def 字符串对齐右(text: str, width: int, fillchar: str = ' ') -> str:
    """右对齐字符串（地板已搬迁：真身 stdlib/内置核心字符串.light:83）"""
    import 内置核心字符串
    return 内置核心字符串.字符串对齐右(text, width, fillchar)


# =============================================================================
# 列表工具函数
# =============================================================================

def 列(*args) -> list:
    """创建包含指定元素的列表（地板已搬迁：真身 stdlib/内置核心列表.light:17）"""
    import 内置核心列表
    return 内置核心列表.列(*args)


def 列表创建() -> list:
    """创建空列表（地板已搬迁：真身 stdlib/内置核心列表.light:21）"""
    import 内置核心列表
    return 内置核心列表.列表创建()


def 列表长度(列表) -> int:
    """获取列表长度（地板已搬迁：真身 stdlib/内置核心列表.light:26）"""
    import 内置核心列表
    return 内置核心列表.列表长度(列表)


def 列表获取(列表, 索引):
    """获取列表中指定索引的元素（地板已搬迁：真身 stdlib/内置核心列表.light:30）"""
    import 内置核心列表
    return 内置核心列表.列表获取(列表, 索引)


def 列表追加(列表, 元素) -> None:
    """向列表追加元素（地板已搬迁：真身 stdlib/内置核心列表.light:34）"""
    import 内置核心列表
    return 内置核心列表.列表追加(列表, 元素)


def 列表弹出(列表, 索引: int = -1):
    """从列表弹出元素（地板已搬迁：真身 stdlib/内置核心列表.light:38）

    `索引=-1` 只能留在本签名里：光明侧写不了负数默认参数，光明段落收满 2 个参。
    """
    import 内置核心列表
    return 内置核心列表.列表弹出(列表, 索引)


def 列表插入(列表, 索引, 元素) -> None:
    """在指定索引处插入元素（地板已搬迁：真身 stdlib/内置核心列表.light:42）"""
    import 内置核心列表
    return 内置核心列表.列表插入(列表, 索引, 元素)


def 列表排序(列表, 反向: bool = False) -> None:
    """排序列表（原地修改）（地板已搬迁：真身 stdlib/内置核心列表.light:46）"""
    import 内置核心列表
    return 内置核心列表.列表排序(列表, 反向)


def 列表反转(列表) -> None:
    """反转列表（原地修改）（地板已搬迁：真身 stdlib/内置核心列表.light:50）"""
    import 内置核心列表
    return 内置核心列表.列表反转(列表)


def 列表包含(列表, 元素) -> bool:
    """检查列表是否包含元素（地板已搬迁：真身 stdlib/内置核心列表.light:54）"""
    import 内置核心列表
    return 内置核心列表.列表包含(列表, 元素)


# =============================================================================
# 字典工具函数
# =============================================================================

def 字典创建() -> dict:
    """创建空字典（地板已搬迁：真身 stdlib/内置核心字典.light:13）"""
    import 内置核心字典
    return 内置核心字典.字典创建()


def 字典设置(字典, 键, 值) -> None:
    """设置字典键值（地板已搬迁：真身 stdlib/内置核心字典.light:19）"""
    import 内置核心字典
    return 内置核心字典.字典设置(字典, 键, 值)


def 字典删除(字典, 键) -> None:
    """删除字典键值（地板已搬迁：真身 stdlib/内置核心字典.light:23）"""
    import 内置核心字典
    return 内置核心字典.字典删除(字典, 键)


def 字典键列表(字典) -> list:
    """获取字典的所有键（地板已搬迁：真身 stdlib/内置核心字典.light:28）"""
    import 内置核心字典
    return 内置核心字典.字典键列表(字典)


def 字典值列表(字典) -> list:
    """获取字典的所有值（地板已搬迁：真身 stdlib/内置核心字典.light:32）"""
    import 内置核心字典
    return 内置核心字典.字典值列表(字典)


def 字典项列表(字典) -> list:
    """获取字典的所有键值对（地板已搬迁：真身 stdlib/内置核心字典.light:36）"""
    import 内置核心字典
    return 内置核心字典.字典项列表(字典)


def 字典包含键(字典, 键) -> bool:
    """检查字典是否包含键（地板已搬迁：真身 stdlib/内置核心字典.light:40）"""
    import 内置核心字典
    return 内置核心字典.字典包含键(字典, 键)


def 字典获取(字典, 键, 默认值=None):
    """从字典获取值，不存在则返回默认值（地板已搬迁：真身 stdlib/内置核心字典.light:44）

    `默认值=None` 留在本签名里，光明段落收满 3 个参并由这里显式传下去。
    """
    import 内置核心字典
    return 内置核心字典.字典获取(字典, 键, 默认值)


# =============================================================================
# 类型检查函数
# =============================================================================

def 是整数(值) -> bool:
    """检查是否为整数（地板已搬迁：真身 stdlib/内置核心判型.light:21）"""
    import 内置核心判型
    return 内置核心判型.是整数(值)


def 是浮点(值) -> bool:
    """检查是否为浮点数（地板已搬迁：真身 stdlib/内置核心判型.light:27）"""
    import 内置核心判型
    return 内置核心判型.是浮点(值)


def 是字符串(值) -> bool:
    """检查是否为字符串（地板已搬迁：真身 stdlib/内置核心判型.light:31）"""
    import 内置核心判型
    return 内置核心判型.是字符串(值)


def 是列表(值) -> bool:
    """检查是否为列表（地板已搬迁：真身 stdlib/内置核心判型.light:35）"""
    import 内置核心判型
    return 内置核心判型.是列表(值)


def 是字典(值) -> bool:
    """检查是否为字典（地板已搬迁：真身 stdlib/内置核心判型.light:39）"""
    import 内置核心判型
    return 内置核心判型.是字典(值)


def 是空(值) -> bool:
    """检查是否为空值（地板已搬迁：真身 stdlib/内置核心判型.light:43）

    光明侧用 `类型(值) == 类型(空)` 表达 `值 is None`：`is None` 在光明里生成
    非法 Python，而 `值 == 空` 会被自定义 `__eq__` 恒真的对象骗过（放宽口径）。
    """
    import 内置核心判型
    return 内置核心判型.是空(值)


def 是字母(char: str) -> bool:
    """检查字符是否为字母（地板已搬迁：真身 stdlib/内置核心判型.light:47）"""
    import 内置核心判型
    return 内置核心判型.是字母(char)


def 是数字(char: str) -> bool:
    """检查字符是否为数字（地板已搬迁：真身 stdlib/内置核心判型.light:51）"""
    import 内置核心判型
    return 内置核心判型.是数字(char)


def 是空白(char: str) -> bool:
    """检查字符是否为空格或空白字符（地板已搬迁：真身 stdlib/内置核心判型.light:55）"""
    import 内置核心判型
    return 内置核心判型.是空白(char)


# =============================================================================
# 日期时间函数
# =============================================================================

def 时间戳() -> float:
    """
    获取当前 Unix 时间戳（秒）
    
    返回:
        浮点数时间戳
    """
    return _time_module.time()


def 格式化时间(时间对象: Union[str, float], 格式: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    将时间戳或时间字符串格式化为指定格式
    
    参数:
        时间对象: Unix 时间戳（浮点数）或 'YYYY-MM-DD HH:MM:SS' 格式字符串
        格式: 目标格式模板
    
    返回:
        格式化后的时间字符串
    """
    if isinstance(时间对象, (int, float)):
        dt = _datetime_class.fromtimestamp(时间对象)
    else:
        # 尝试多种格式解析
        for fmt in [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d',
        ]:
            try:
                dt = _datetime_class.strptime(时间对象, fmt)
                break
            except ValueError:
                continue
        else:
            raise RuntimeError(f"无法解析时间字符串: '{时间对象}'")
    
    return dt.strftime(格式)


# =============================================================================
# 数学/统计/随机函数
# =============================================================================

def 随机整数(最小: int, 最大: int) -> int:
    """
    生成范围内的随机整数
    
    参数:
        最小: 最小值（包含）
        最大: 最大值（包含）
    
    返回:
        随机整数
    """
    return random.randint(最小, 最大)


def 随机浮点() -> float:
    """
    生成 [0.0, 1.0) 范围内的随机浮点数
    
    返回:
        随机浮点数
    """
    return random.random()


def 随机选择(列表) -> Optional[object]:
    """
    从列表中随机选择一个元素
    
    参数:
        列表: 源列表
    
    返回:
        随机选中的元素，列表为空返回空
    """
    if not 列表:
        return None
    return random.choice(列表)


def 阶乘(n: int) -> int:
    """
    计算 n 的阶乘
    
    参数:
        n: 非负整数
    
    返回:
        n!
    """
    if n < 0:
        raise RuntimeError("阶乘参数不能为负数")
    return math.factorial(n)


def 平均数(数据: list) -> float:
    """
    计算列表的平均值
    
    参数:
        数据: 数值列表
    
    返回:
        平均值
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    return statistics.mean(数据)


def 中位数(数据: list) -> float:
    """
    计算列表的中位数
    
    参数:
        数据: 数值列表
    
    返回:
        中位数
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    return statistics.median(数据)


def 众数(数据: list):
    """
    计算列表的众数（出现次数最多的值）
    
    参数:
        数据: 数值列表
    
    返回:
        众数
    """
    if not 数据:
        raise RuntimeError("数据列表为空")
    try:
        return statistics.mode(数据)
    except statistics.StatisticsError:
        raise RuntimeError("无法确定众数（多个值出现次数相同）")


def 方差(数据: list) -> float:
    """
    计算总体方差
    
    参数:
        数据: 数值列表
    
    返回:
        方差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.pvariance(数据)


def 标准差(数据: list) -> float:
    """
    计算总体标准差
    
    参数:
        数据: 数值列表
    
    返回:
        标准差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.pstdev(数据)


def 样本方差(数据: list) -> float:
    """
    计算样本方差（分母 n-1）
    
    参数:
        数据: 数值列表
    
    返回:
        样本方差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.variance(数据)


def 样本标准差(数据: list) -> float:
    """
    计算样本标准差（分母 n-1）
    
    参数:
        数据: 数值列表
    
    返回:
        样本标准差
    """
    if len(数据) < 2:
        raise RuntimeError("数据点太少（至少需要2个）")
    return statistics.stdev(数据)


def 求和(数据: list) -> float:
    """
    计算列表中所有数值的和（地板已搬迁：真身 stdlib/列表工具.light:69）

    参数:
        数据: 数值列表

    返回:
        总和

    第二参 `长整上限` 只能由本侧算出来后显式传进去：CPython 的 sum() 整数快路径
    用 C long 判溢出，宽度是平台相关的（LP64 是 2**63-1，Windows/LLP64 是 2**31-1），
    而光明侧问不到 sizeof(long)（那需要 struct/ctypes 直调，列表工具.light 里不许有）。
    不传就会在 Windows 上于「|int 元素| ≥ 2**31 且其后有会抵消的浮点」这个窗口里
    与本机 sum() 分叉，例如 [2**31, 1e16, 1.0, -1e16]。

    第三参 `启用补偿` 同理，只不过它是**版本相关**而不是平台相关：CPython 自 3.12
    （gh-100425）起 sum() 对浮点走 Neumaier 补偿，3.11 及更早是朴素累加。本侧按
    `sys.version_info >= (3, 12)` 算出来显式传，所以本函数在 3.11 宿主（CI runner
    就是 3.11）和 3.14 宿主上都与该宿主的 sum() 逐位等价。
    """
    import struct
    import sys
    import 列表工具
    return 列表工具.求和(数据,
                       (1 << (8 * struct.calcsize("l") - 1)) - 1,
                       sys.version_info >= (3, 12))



def 累积和(数据: list) -> list:
    """
    计算列表的累积和
    
    参数:
        数据: 数值列表
    
    返回:
        累积和列表
    
    示例:
        累积和([1, 2, 3, 4])  # [1, 3, 6, 10]
    """
    result = []
    total = 0
    for v in 数据:
        total += v
        result.append(total)
    return result


def 圆周率() -> float:
    """返回圆周率 π 的近似值"""
    return math.pi


def 自然常数() -> float:
    """返回自然常数 e 的近似值"""
    return math.e


def 角度转弧度(角度: float) -> float:
    """角度转弧度"""
    return math.radians(角度)


def 弧度转角度(弧度: float) -> float:
    """弧度转角度"""
    return math.degrees(弧度)


# =============================================================================
# 系统原语（第九轮 S2 · 外发任务_内置与直调S2）
# =============================================================================
# 这 20 条对应 任务书/缺失内置清单.json 的「缺失内置」档，全部 native_required：
# 本质是系统调用（os / time / hmac），光明写不出来，只能转发。
#
# 三条硬规矩沿用地板转发（本文件头部）：
#   1. 惰性：对「光明模块」的 import 放函数体内；os 已在顶部（:7）导入、time
#      以别名 _time_module（:12）注入，这里直接复用，不新增顶层 import。
#   2. 不静默兜底：转发失败就抛。唯一的「返回默认值」是跨平台常量语义本身——
#      二进制（O_BINARY 仅 Windows）/ 不跟随符号链接（O_NOFOLLOW 仅 POSIX）
#      在对应平台上本就无此概念，返回 0 是文档语义，不是掩错。
#   3. 等价性：全部直译 os.* / time.* / hmac.*，与调用点原 os 用法逐字等价。
#
# 常量以「零参函数」形态落地（`_light_builtin.只读()`）而不是模块级整型标量：
#   光明侧裸写 `只读` 会被解析器当零参调用（src/code_generator.py:2781 注释），
#   发射成 `_light_builtin.只读()`；若是 int 标量运行期就 TypeError。做成函数
#   与既有发射机制零冲突。跨平台守卫也自然落在函数体内，不污染模块顶层。
#   语义上仍是「常量」：每次调用返回同一个固定旗标整数。


def 真实路径(路径: str) -> str:
    """解析符号链接 / junction / .. / 8.3 短名，返回规范化真实路径（os.path.realpath）"""
    return os.path.realpath(路径)


def 文件状态(路径):
    """按路径取文件元数据（os.stat）。取不到（不存在/无权限）返回空，不抛。

    状态对象即 Python 的 os.stat_result，透明暴露 硬链接数(st_nlink) /
    设备号(st_dev) / 节点号(st_ino) / 大小 / 是目录，供护栏 TOCTOU 身份比对。
    """
    try:
        return os.stat(路径)
    except Exception:
        return None


def 句柄状态(句柄):
    """按已打开的文件描述符取元数据（os.fstat）。取不到返回空，不抛。

    与 文件状态 的区别全在于「从已持有的句柄回查」，避免再开一个 TOCTOU 窗口。
    """
    try:
        return os.fstat(句柄)
    except Exception:
        return None


def 低级打开(路径: str, 标志位: int, 模式: int) -> int:
    """按标志位打开文件，返回整数文件描述符（os.open）。失败抛错。"""
    return os.open(路径, 标志位, 模式)


def 低级读(句柄: int, 字节数: int) -> bytes:
    """从描述符读至多 字节数 个字节，返回字节串（os.read）；读到末尾返回空字节串。"""
    return os.read(句柄, 字节数)


def 低级写(句柄: int, 字节) -> int:
    """向描述符写字节串，返回实际写入字节数（os.write）。"""
    return os.write(句柄, 字节)


def 低级关闭(句柄: int) -> None:
    """关闭描述符（os.close）。"""
    os.close(句柄)


def 随机字节(个数: int) -> bytes:
    """返回 个数 个密码学安全的随机字节（os.urandom）。"""
    return os.urandom(个数)


def 原子替换(源: str, 目标: str) -> None:
    """同卷内原子改名，目标已存在则原子覆盖（os.replace）。"""
    os.replace(源, 目标)


def 环境枚举():
    """列出当前进程全部环境变量，返回 [[名, 值], ...]（os.environ.items()）。"""
    return [[名, 值] for 名, 值 in os.environ.items()]


def 单调时钟() -> float:
    """返回只增不减、不受系统时钟调整影响的秒数（time.monotonic）。绝对值无意义，只用于求差。"""
    return _time_module.monotonic()


def 常量时间比较(甲, 乙) -> bool:
    """以不随输入内容变化的时间比较两个字符串/字节是否相等（hmac.compare_digest），防时序侧信道。"""
    import hmac
    return hmac.compare_digest(甲, 乙)


# ---- 8 个打开标志常量（跨平台，以零参函数形态落地） ----

def 只读() -> int:
    """打开标志：只读（os.O_RDONLY）。"""
    return os.O_RDONLY


def 只写() -> int:
    """打开标志：只写（os.O_WRONLY）。"""
    return os.O_WRONLY


def 新建() -> int:
    """打开标志：不存在则创建（os.O_CREAT）。"""
    return os.O_CREAT


def 截断() -> int:
    """打开标志：已存在则清空到零长度（os.O_TRUNC）。"""
    return os.O_TRUNC


def 追加() -> int:
    """打开标志：每次写都定位到文件末尾（os.O_APPEND）。"""
    return os.O_APPEND


def 独占() -> int:
    """打开标志：与 新建 合用时目标已存在则失败（os.O_EXCL）。"""
    return os.O_EXCL


def 二进制() -> int:
    """打开标志：字节透传不做换行转换。仅 Windows 存在（os.O_BINARY），POSIX 上无此概念、返回 0。"""
    return os.O_BINARY if hasattr(os, "O_BINARY") else 0


def 不跟随符号链接() -> int:
    """打开标志：末段是符号链接则直接失败。仅 POSIX 存在（os.O_NOFOLLOW），Windows 上返回 0。"""
    return os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0


# =============================================================================
# 导出所有函数
# =============================================================================

__all__ = [
    # 文件I/O
    '读取文件', '写入文件', '追加文件',
    '文件存在', '目录存在', '路径存在',
    '创建目录', '删除文件', '删除目录',
    '列出目录', '文件大小',
    
    # 路径操作
    '绝对路径', '连接路径', '目录名', '文件名',
    '扩展名', '分割路径', '分割扩展名',
    
    # 系统函数
    '环境变量', '设置环境变量', '参数列表',
    '退出程序', '当前目录', '切换目录', '执行命令',

    # 标准输入输出
    '读取行', '读取N字节', '写入输出',
    '打印输出', '刷新输出', '写入错误', '打印错误',

    # JSON 处理
    '解析JSON', '序列化JSON', '美化JSON',

    # 字符串工具

    # 字符串工具
    '转整数', '转浮点', '转字符串',
    '字符串长度', '字符串获取', '分割字符串', '连接字符串',
    '替换字符串', '去除空白',
    '字符串包含', '开头', '结尾', '查找子串',
    '替换字符串次数', '截取到末尾', '字符串计数',
    '字符串重复', '字符串反转', '转标题',
    '去除左侧空白', '去除右侧空白',
    '字符串对齐居中', '字符串对齐左', '字符串对齐右',
    
    # 列表工具
    '列', '列表长度', '列表追加', '列表弹出', '列表插入',
    '列表排序', '列表反转', '列表包含',
    
    # 字典工具
    '字典创建', '字典设置', '字典删除',
    '字典键列表', '字典值列表', '字典项列表',
    '字典包含键', '字典获取',
    
    # 类型检查
    '是整数', '是浮点', '是字符串',
    '是列表', '是字典', '是空',
    '是字母', '是数字', '是空白',
    
    # 数学/统计/随机
    '随机整数', '随机浮点', '随机选择',
    '阶乘', '平均数', '中位数', '众数',
    '方差', '标准差', '样本方差', '样本标准差',
    '求和', '累积和',
    '圆周率', '自然常数',
    '角度转弧度', '弧度转角度',

    # 系统原语（第九轮 S2）
    '真实路径', '文件状态', '句柄状态',
    '低级打开', '低级读', '低级写', '低级关闭',
    '随机字节', '原子替换', '环境枚举',
    '单调时钟', '常量时间比较',
    '只读', '只写', '新建', '截断', '追加', '独占',
    '二进制', '不跟随符号链接',
]
