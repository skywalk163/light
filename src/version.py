"""
光明（LightLang）版本信息集中管理

本模块提供统一的版本号、发布日期、版本名称等信息。
所有需要版本号的模块应从此处导入，而非各自定义。
"""

# 版本号
__version__ = "7.0.0"
VERSION = "7.0.0"
VERSION_MAJOR = 7
VERSION_MINOR = 0
VERSION_PATCH = 0

# 版本名称
VERSION_NAME = "v7.0 双线合并与品牌统一版"

# 发布日期
RELEASE_DATE = "2026-08-14"

# 版本阶段: dev / alpha / beta / rc / stable
RELEASE_STAGE = "stable"

# 开发分支标志（True 表示当前为开发分支，非正式发布）
DEV_BRANCH = False

# 支持的语法层级
SUPPORTED_LEVELS = ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"]

# 支持的编译器后端
COMPILER_BACKENDS = ["python", "llvm", "c", "wasm"]

# 版本描述
VERSION_DESCRIPTION = """
光明 v7.0 是段言（Duan）与光明（Light）双线合并后的首个统一版本。

核心亮点：
- 品牌统一：全面统一为「光明 / Light」，源文件后缀 .light，CLI 为 light / lightc
- 双线合并：段言 v6.3 与光明 v6.0 的编译器内核逐块融合，保留双方超集能力
- 类型系统：泛型、联合类型（整数|浮点）、可空类型、模式匹配
- 三套并行实现：手写 src/、ANTLR4 antlrparser/、自举 bootstrap/（Level 3–7）
- 积木库：约 10010 个积木，零 token 离线代码生成
- 编译器后端：Python / LLVM / C / WASM
- 包生态：light.json + light.lock，包注册表、版本管理、依赖循环检测
"""

# 最低 Python 版本要求
MINIMUM_PYTHON_VERSION = (3, 10)

# 推荐 Python 版本
RECOMMENDED_PYTHON_VERSION = (3, 12)


def get_version_info() -> dict:
    """获取版本信息字典"""
    return {
        "version": VERSION,
        "major": VERSION_MAJOR,
        "minor": VERSION_MINOR,
        "patch": VERSION_PATCH,
        "name": VERSION_NAME,
        "release_date": RELEASE_DATE,
        "stage": RELEASE_STAGE,
        "supported_levels": SUPPORTED_LEVELS,
        "compiler_backends": COMPILER_BACKENDS,
        "min_python": MINIMUM_PYTHON_VERSION,
        "recommended_python": RECOMMENDED_PYTHON_VERSION,
    }


def get_version_string() -> str:
    """获取人类可读的版本字符串"""
    stage = f"-{RELEASE_STAGE}" if RELEASE_STAGE != "stable" else ""
    return f"{VERSION}{stage} ({RELEASE_DATE})"


def get_full_version_string() -> str:
    """获取完整版本字符串"""
    return f"光明 LightLang v{VERSION}「{VERSION_NAME}」— {RELEASE_DATE}"


def get_dev_version_string() -> str:
    """获取开发分支版本字符串"""
    return f"光明 LightLang v{VERSION}dev (开发分支) — {RELEASE_DATE}"


def is_dev_branch() -> bool:
    """判断当前是否为开发分支"""
    return DEV_BRANCH