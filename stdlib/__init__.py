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

# ============================================================
# 纯光明模块惰性回退（R144-C）
# ============================================================
# 背景：上面每个「相对 star-import」只认同名 `.py`（钩子对带点的 fullname 一律
# 让位给标准机制，标准机制只找 `.py`）。R144-C 把一批「.light 首两行已声明
# 『纯光明实现』」的 `.py` 影子清掉之后，这些块会静默 ImportError
# （`except ImportError: pass`），于是 `stdlib.快速排序` 这类名字
# 从包命名空间里消失，`from stdlib import 排序` 与
# tests/test_stdlib_comprehensive.py::TestStdlibAllModules::test_stdlib_init
# 打红。
#
# 这里补一条 PEP 562（模块级 __getattr__）惰性出口：包命名空间里**查不到**的
# 名字，才到「无同名 .py 的 .light」里找。三点纪律：
#   1. 索引只正则扫 `导出` 行建「符号名 -> 模块名」，**不编译**任何 .light；
#   2. 真正用到某个名字时，才经 `_light_import_hook` 编译**那一个**模块；
#   3. `__getattr__` 只在属性缺失时触发，因此不会改变任何原本就取得到的名字的
#      语义——之前能取到什么，现在还是取到什么。
_纯光明索引 = None


def _建纯光明索引():
    """符号名 -> 模块名；只收「无同名 .py」的 .light（有 .py 的由相对导入负责）。"""
    import os
    import re

    idx = {}
    _dir = os.path.dirname(os.path.abspath(__file__))
    for fn in sorted(os.listdir(_dir)):
        if not fn.endswith('.light'):
            continue
        模块名 = fn[:-len('.light')]
        if os.path.isfile(os.path.join(_dir, 模块名 + '.py')):
            continue
        try:
            with open(os.path.join(_dir, fn), encoding='utf-8') as fh:
                for line in fh:
                    m = re.match(r'^导出\s+(.+?)[\s。]*$', line.strip())
                    if not m:
                        continue
                    for sym in m.group(1).split():
                        idx.setdefault(sym.strip('。，、;；'), 模块名)
        except OSError:
            continue
    return idx


def __getattr__(名):
    """包级惰性回退（PEP 562）：仅当包命名空间里确实没有该名字时触发。"""
    global _纯光明索引
    if 名.startswith('_'):
        raise AttributeError("module 'stdlib' has no attribute %r" % 名)
    if _纯光明索引 is None:
        _纯光明索引 = _建纯光明索引()
    模块名 = _纯光明索引.get(名)
    if 模块名 is None:
        raise AttributeError("module 'stdlib' has no attribute %r" % 名)
    import importlib
    import os
    try:
        import _light_import_hook
        _light_import_hook.install([os.path.dirname(os.path.abspath(__file__))])
    except Exception:
        pass
    try:
        模块 = importlib.import_module(模块名)
        值 = getattr(模块, 名)
    except Exception as exc:
        raise AttributeError(
            "module 'stdlib' has no attribute %r（纯光明回退 %s 取不到：%s）"
            % (名, 模块名, exc))
    globals()[名] = 值          # 命中后固化，后续走普通属性查找
    return 值
