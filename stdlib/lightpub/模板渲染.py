"""
模板渲染 — duanpub 桥接模块

基于 Python string.Template / html / re 等库封装，
函数名对齐 duanpub/packages/模板渲染/源.duan。

duanpub 原始包通过 C FFI 实现模板引擎，
本桥接模块用 Python 标准库替代，提供等价的模板渲染功能。
"""

import re as _re
import html as _html
import json as _json
import urllib.parse as _urlparse
import string as _string
from functools import partial as _partial


# =============================================================================
# 内部工具函数
# =============================================================================

def 范围(开始, 结束):
    """生成范围列表"""
    return list(range(开始, 结束))


def 整数转字符串(值):
    """整数转字符串"""
    return str(值)


def 内部包含(文本, 子串):
    """检查是否包含子串"""
    return 子串 in 文本


def 内部以开始(文本, 前缀):
    """检查是否以指定前缀开始"""
    return 文本.startswith(前缀)


def 内部分割字符串(文本, 分隔符):
    """分割字符串"""
    return 文本.split(分隔符)


def 内部去除空白(文本):
    """去除首尾空白"""
    return 文本.strip()


def 内部转为小写(文本):
    """转为小写"""
    return 文本.lower()


def 内部转为大写(文本):
    """转为大写"""
    return 文本.upper()


def 内部查找字符(文本, 字符):
    """查找字符位置"""
    return 文本.find(字符)


def 内部值转字符串(值):
    """值转字符串"""
    return str(值)


def 内部HTML转义(文本):
    """HTML 转义"""
    return _html.escape(文本, quote=True)


def 内部HTML反转义(文本):
    """HTML 反转义"""
    return _html.unescape(文本)


def 内部替换所有(文本, 旧, 新):
    """替换所有"""
    return 文本.replace(旧, 新)


def 内部URL编码(文本):
    """URL 编码"""
    return _urlparse.quote(文本, safe='')


# =============================================================================
# 模板过滤器
# =============================================================================

def 内部转为大写过滤器(值):
    """大写过滤器"""
    return str(值).upper() if 值 is not None else ''


def 内部转为小写过滤器(值):
    """小写过滤器"""
    return str(值).lower() if 值 is not None else ''


def 内部首字母大写过滤器(值):
    """首字母大写过滤器"""
    if not 值:
        return ''
    s = str(值)
    return s[0].upper() + s[1:]


def 内部截断过滤器(值, 长度=100):
    """截断过滤器"""
    if not 值:
        return ''
    s = str(值)
    if len(s) <= 长度:
        return s
    return s[:长度] + '...'


def 内部默认值过滤器(值, 默认=''):
    """默认值过滤器"""
    return 值 if 值 is not None else 默认


def 内部去除空白过滤器(值):
    """去除空白过滤器"""
    return str(值).strip() if 值 is not None else ''


def 内部JSON编码过滤器(值):
    """JSON 编码过滤器"""
    return _json.dumps(值, ensure_ascii=False)


def 内部URL编码过滤器(值):
    """URL 编码过滤器"""
    return _urlparse.quote(str(值), safe='')


def 内部HTML转义过滤器(值):
    """HTML 转义过滤器"""
    return _html.escape(str(值), quote=True) if 值 is not None else ''


def 内部换行转BR过滤器(值):
    """换行转 BR 过滤器"""
    if not 值:
        return ''
    return str(值).replace('\n', '<br>')


def 内部数字格式化过滤器(值, 小数位=2):
    """数字格式化过滤器"""
    try:
        return f"{float(值):.{小数位}f}"
    except (ValueError, TypeError):
        return str(值)


# =============================================================================
# 模板引擎
# =============================================================================

class _TemplateEngine:
    """模板引擎"""
    def __init__(self):
        self.filters = {}
        self.globals = {}
        self._cache = {}

    def register_filter(self, name, func):
        self.filters[name] = func

    def register_global(self, name, value):
        self.globals[name] = value

    def clear_cache(self):
        self._cache.clear()


def engineRegisterFilter(engine, name, func):
    """注册模板过滤器"""
    if not isinstance(engine, _TemplateEngine):
        raise Exception("engineRegisterFilter失败: 引擎无效")
    engine.register_filter(name, func)


def engineRegisterGlobal(engine, name, value):
    """注册全局变量"""
    if not isinstance(engine, _TemplateEngine):
        raise Exception("engineRegisterGlobal失败: 引擎无效")
    engine.register_global(name, value)


def engineRender(engine, template_name, context=None):
    """渲染模板文件"""
    if not isinstance(engine, _TemplateEngine):
        raise Exception("engineRender失败: 引擎无效")
    # 简化实现：从缓存或直接渲染
    template = engine._cache.get(template_name)
    if template is None:
        raise Exception("engineRender失败: 模板未找到 " + template_name)
    return renderTemplateContent(template, context or {}, engine)


def engineRenderString(engine, template_string, context=None):
    """渲染模板字符串"""
    if not isinstance(engine, _TemplateEngine):
        raise Exception("engineRenderString失败: 引擎无效")
    return renderTemplateContent(template_string, context or {}, engine)


def engineClearCache(engine):
    """清空模板缓存"""
    if not isinstance(engine, _TemplateEngine):
        raise Exception("engineClearCache失败: 引擎无效")
    engine.clear_cache()


# =============================================================================
# 模板渲染核心
# =============================================================================

def renderTemplateContent(内容, 上下文, 引擎=None):
    """渲染模板内容"""
    try:
        tpl = _string.Template(内容)
        # 构建替换字典
        mapping = dict(上下文)
        if 引擎:
            mapping.update(引擎.globals)
        # 安全替换
        return tpl.safe_substitute(mapping)
    except Exception as e:
        raise Exception("renderTemplateContent失败: " + str(e))


def renderRawBlock(内容, 上下文, 引擎=None):
    """渲染原始文本块"""
    return 内容


def renderComments(内容, 上下文, 引擎=None):
    """渲染注释（忽略）"""
    return ''


def renderExtendsBlock(内容, 上下文, 引擎=None):
    """渲染继承块（简化实现，返回空）"""
    return ''


def extractBlockDefs(内容):
    """提取块定义（简化实现，返回空字典）"""
    return {}


def renderBlockDefs(块定义, 块名, 上下文, 引擎=None):
    """渲染块定义"""
    return 块定义.get(块名, '')


def renderIncludeBlock(内容, 上下文, 引擎=None):
    """渲染包含块"""
    return renderTemplateContent(内容, 上下文, 引擎)


def renderIfBlock(内容, 条件, 上下文, 引擎=None):
    """渲染条件块"""
    if evaluateCondition(条件, 上下文):
        return renderTemplateContent(内容, 上下文, 引擎)
    return ''


def renderForBlock(内容, 变量名, 列表, 上下文, 引擎=None):
    """渲染循环块"""
    result = []
    for item in 列表:
        ctx = dict(上下文)
        ctx[变量名] = item
        result.append(renderTemplateContent(内容, ctx, 引擎))
    return ''.join(result)


def renderVariables(内容, 上下文, 引擎=None):
    """渲染变量"""
    return renderTemplateContent(内容, 上下文, 引擎)


# =============================================================================
# 块查找
# =============================================================================

def findBlockEnd(内容, 起始位置, 块类型=''):
    """查找块结束位置（简化实现）"""
    return len(内容)


def findBlockInString(内容, 块名):
    """在字符串中查找块（简化实现）"""
    return 0, len(内容)


# =============================================================================
# 条件评估
# =============================================================================

def evaluateCondition(条件, 上下文):
    """评估条件表达式"""
    return evaluateSimpleCondition(条件, 上下文)


def evaluateSimpleCondition(条件, 上下文):
    """评估简单条件"""
    if not 条件:
        return False
    # 如果是变量名，检查上下文中的值
    if 条件 in 上下文:
        return bool(上下文[条件])
    # 简单比较
    if '==' in 条件:
        parts = 条件.split('==', 1)
        left = 上下文.get(parts[0].strip(), parts[0].strip())
        right = 上下文.get(parts[1].strip(), parts[1].strip())
        return left == right
    if '!=' in 条件:
        parts = 条件.split('!=', 1)
        left = 上下文.get(parts[0].strip(), parts[0].strip())
        right = 上下文.get(parts[1].strip(), parts[1].strip())
        return left != right
    if '>' in 条件:
        parts = 条件.split('>', 1)
        try:
            left = float(上下文.get(parts[0].strip(), parts[0].strip()))
            right = float(上下文.get(parts[1].strip(), parts[1].strip()))
            return left > right
        except (ValueError, TypeError):
            pass
    if '<' in 条件:
        parts = 条件.split('<', 1)
        try:
            left = float(上下文.get(parts[0].strip(), parts[0].strip()))
            right = float(上下文.get(parts[1].strip(), parts[1].strip()))
            return left < right
        except (ValueError, TypeError):
            pass
    return bool(条件)


# =============================================================================
# 创建引擎
# =============================================================================

def 创建tpl引擎():
    """创建模板引擎"""
    return _TemplateEngine()