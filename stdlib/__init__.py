"""
光明标准库

三层架构：
  1. 原生标准库（.light）：纯光明语法编写，体现语言特色
  2. 核心运行时（builtins.py）：Python 实现的内置函数，无需 import
  3. FFI 直通层（.py + .light）：透传 Python/第三方库，方法名不翻译

高级/领域模块已移至 contrib/ 目录，按需显式导入。

使用方式（光明代码）：
    内置函数直接可用：打印("你好"), 随机整数(1, 100)
    模块导入：从 JSON 导入 解析JSON, 生成JSON。
    contrib：从 contrib.HTTP客户端 导入 获取。
"""

from .builtins import *

# ============================================================
# 核心运行时模块（无外部依赖的纯 Python 封装）
# ============================================================

try:
    from .日期时间 import *
except ImportError:
    pass

try:
    from .JSON import *
except ImportError:
    pass

try:
    from .哈希 import *
except ImportError:
    pass

try:
    from .正则表达式 import *
except ImportError:
    pass

try:
    from .数学 import *
except ImportError:
    pass

try:
    from .字符串处理 import *
except ImportError:
    pass

try:
    from .字符串工具 import *
except ImportError:
    pass

try:
    from .字符串常量 import *
except ImportError:
    pass

try:
    from .集合 import *
except ImportError:
    pass

try:
    from .集合工具 import *
except ImportError:
    pass

try:
    from .集合操作 import *
except ImportError:
    pass

try:
    from .数据结构 import *
except ImportError:
    pass

try:
    from .装饰器 import *
except ImportError:
    pass

try:
    from .断言工具 import *
except ImportError:
    pass

# ============================================================
# FFI 直通层模块（透传 Python 标准库/第三方库）
# ============================================================

try:
    from .文件系统 import *
except ImportError:
    pass

try:
    from .文件匹配 import *
except ImportError:
    pass

try:
    from .临时文件 import *
except ImportError:
    pass

try:
    from .CSV读写器 import *
except ImportError:
    pass

try:
    from .编码 import *
except ImportError:
    pass

try:
    from .编码解码 import *
except ImportError:
    pass

try:
    from .加密 import *
except ImportError:
    pass

try:
    from .时间管理 import *
except ImportError:
    pass

try:
    from .日志系统增强 import *
except ImportError:
    pass

try:
    from .对象池缓存 import *
except ImportError:
    pass

try:
    from .系统接口 import *
except ImportError:
    pass

try:
    from .外部命令 import *
except ImportError:
    pass

try:
    from .参数解析 import *
except ImportError:
    pass

try:
    from .FFI import *
except ImportError:
    pass

# ============================================================
# 特色标准库（光明语言特色，纯中文 API）
# ============================================================

try:
    from .中文文本 import *
except ImportError:
    pass

try:
    from .历法 import *
except ImportError:
    pass

try:
    from .排版 import *
except ImportError:
    pass

# ============================================================
# 新增补齐模块（第8周标准库补齐）
# ============================================================

try:
    from .Base64 import *
except ImportError:
    pass

try:
    from .CSV import *
except ImportError:
    pass

try:
    from .HTTP import *
except ImportError:
    pass

try:
    from .网络 import *
except ImportError:
    pass

try:
    from .颜色 import *
except ImportError:
    pass

try:
    from .进程 import *
except ImportError:
    pass

try:
    from .环境 import *
except ImportError:
    pass

try:
    from .信号 import *
except ImportError:
    pass

try:
    from .线程 import *
except ImportError:
    pass

try:
    from .测试 import *
except ImportError:
    pass

try:
    from .性能 import *
except ImportError:
    pass

try:
    from .日志 import *
except ImportError:
    pass

try:
    from .配置 import *
except ImportError:
    pass

try:
    from .统计 import *
except ImportError:
    pass

try:
    from .随机 import *
except ImportError:
    pass

try:
    from .复数 import *
except ImportError:
    pass

try:
    from .向量 import *
except ImportError:
    pass

try:
    from .排序 import *
except ImportError:
    pass

try:
    from .分词 import *
except ImportError:
    pass

try:
    from .格式化 import *
except ImportError:
    pass

try:
    from .模板 import *
except ImportError:
    pass

# ============================================================
# 第8周新增补齐模块（缓存、进度条、数据验证）
# ============================================================

try:
    from .缓存 import *
except ImportError:
    pass

try:
    from .进度条 import *
except ImportError:
    pass

try:
    from .数据验证 import *
except ImportError:
    pass

try:
    from .中文NLP import *
except ImportError:
    pass
