"""
光明（Light）编程语言 - 动词信息模块

定义动词的元数和修改模式（决策28、决策34）

决策28：元数驱动解析
- 动词声明参数数量，自动收集参数
- 支持无括号函数调用

决策34：主谓/谓宾语义
- mode='modify': 原地修改（列表排序 → 列表.sort()）
- mode='functional': 返回新对象（排序列表 → sorted(列表)）
- mode='both': 两种模式都支持
"""

from typing import Dict, Optional
from dataclasses import dataclass


# =============================================================================
# 动词信息定义
# =============================================================================

@dataclass
class VerbInfo:
    """动词信息"""
    arity: int           # 参数数量（-1表示可变参数）
    mode: str            # functional, modify, both
    description: str     # 描述
    
    def supports_modify(self) -> bool:
        """是否支持原地修改"""
        return self.mode in ('modify', 'both')
    
    def supports_functional(self) -> bool:
        """是否支持函数式"""
        return self.mode in ('functional', 'both')


# =============================================================================
# 动词信息表
# =============================================================================

VERB_INFO: Dict[str, VerbInfo] = {
    # 算术运算（二元，函数式）
    '加': VerbInfo(arity=2, mode='functional', description='加法运算'),
    '减': VerbInfo(arity=2, mode='functional', description='减法运算'),
    '乘': VerbInfo(arity=2, mode='functional', description='乘法运算'),
    '除': VerbInfo(arity=2, mode='functional', description='除法运算'),
    '取余': VerbInfo(arity=2, mode='functional', description='取余运算'),
    
    # 比较运算（二元，函数式）
    '大于': VerbInfo(arity=2, mode='functional', description='大于比较'),
    '小于': VerbInfo(arity=2, mode='functional', description='小于比较'),
    '等于': VerbInfo(arity=2, mode='functional', description='等于比较'),
    '不等于': VerbInfo(arity=2, mode='functional', description='不等于比较'),
    '大于等于': VerbInfo(arity=2, mode='functional', description='大于等于比较'),
    '小于等于': VerbInfo(arity=2, mode='functional', description='小于等于比较'),
    
    # 列表操作（一元或二元）
    '首': VerbInfo(arity=1, mode='functional', description='取首元素'),
    '末': VerbInfo(arity=1, mode='functional', description='取末元素'),
    '余': VerbInfo(arity=1, mode='functional', description='取余下元素'),
    '长': VerbInfo(arity=1, mode='functional', description='取长度'),
    
    # 列表构造（可变参数）
    '列': VerbInfo(arity=-1, mode='functional', description='列表构造'),
    
    # 列表修改操作（二元，支持两种模式）
    '添加': VerbInfo(arity=2, mode='modify', description='添加元素（原地修改）'),
    '插入': VerbInfo(arity=2, mode='modify', description='插入元素（原地修改）'),
    '删除': VerbInfo(arity=2, mode='modify', description='删除元素（原地修改）'),
    '移除': VerbInfo(arity=2, mode='modify', description='移除元素（原地修改）'),
    
    # 列表函数式操作（二元，函数式）
    '过滤': VerbInfo(arity=2, mode='functional', description='筛选元素（返回新列表）'),
    '映射': VerbInfo(arity=2, mode='functional', description='映射变换（返回新列表）'),
    '归约': VerbInfo(arity=2, mode='functional', description='归约计算'),
    '排序': VerbInfo(arity=1, mode='both', description='排序（支持两种模式）'),
    '反转': VerbInfo(arity=1, mode='both', description='反转（支持两种模式）'),
    
    # I/O操作（一元）
    '打印': VerbInfo(arity=1, mode='functional', description='打印输出'),
    '读取': VerbInfo(arity=1, mode='functional', description='读取输入'),
    
    # 字符串操作（二元，函数式）
    '连接': VerbInfo(arity=2, mode='functional', description='字符串连接'),
    '分割': VerbInfo(arity=2, mode='functional', description='字符串分割'),
    '替换': VerbInfo(arity=3, mode='functional', description='字符串替换'),
    
    # 属性提取（一元，函数式）
    '之': VerbInfo(arity=2, mode='functional', description='属性提取'),
}


# =============================================================================
# 辅助函数
# =============================================================================

def get_verb_info(verb: str) -> Optional[VerbInfo]:
    """获取动词信息"""
    return VERB_INFO.get(verb)


def get_arity(verb: str) -> int:
    """获取动词参数数量"""
    info = VERB_INFO.get(verb)
    return info.arity if info else 1


def get_mode(verb: str) -> str:
    """获取动词修改模式"""
    info = VERB_INFO.get(verb)
    return info.mode if info else 'functional'


def is_verb(word: str) -> bool:
    """判断是否为动词"""
    return word in VERB_INFO


def supports_modify(verb: str) -> bool:
    """判断是否支持原地修改"""
    info = VERB_INFO.get(verb)
    return info.supports_modify() if info else False


def supports_functional(verb: str) -> bool:
    """判断是否支持函数式"""
    info = VERB_INFO.get(verb)
    return info.supports_functional() if info else True


# =============================================================================
# Python映射
# =============================================================================

VERB_TO_PYTHON = {
    # 算术运算
    '加': ('+', 'operator'),
    '减': ('-', 'operator'),
    '乘': ('*', 'operator'),
    '除': ('/', 'operator'),
    '取余': ('%', 'operator'),
    
    # 比较运算
    '大于': ('>', 'operator'),
    '小于': ('<', 'operator'),
    '等于': ('==', 'operator'),
    '不等于': ('!=', 'operator'),
    '大于等于': ('>=', 'operator'),
    '小于等于': ('<=', 'operator'),
    
    # 列表操作
    '首': ('lambda x: x[0]', 'function'),
    '末': ('lambda x: x[-1]', 'function'),
    '长': ('len', 'function'),
    '列': ('list', 'function'),
    
    # 列表修改操作
    '添加': ('append', 'method'),
    '插入': ('insert', 'method'),
    '删除': ('remove', 'method'),
    
    # 列表函数式操作
    '过滤': ('filter', 'function'),
    '映射': ('map', 'function'),
    '归约': ('reduce', 'function'),
    '排序': ('sorted', 'function'),  # 函数式
    '反转': ('reversed', 'function'),  # 函数式
    
    # I/O操作
    '打印': ('print', 'function'),
    '读取': ('input', 'function'),
    
    # 字符串操作
    '连接': ('join', 'method'),
    '分割': ('split', 'method'),
    '替换': ('replace', 'method'),
}


def get_python_mapping(verb: str) -> Optional[tuple]:
    """获取动词到Python的映射"""
    return VERB_TO_PYTHON.get(verb)


# =============================================================================
# 测试
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("动词信息模块测试")
    print("=" * 60)
    
    # 测试动词信息
    test_verbs = ['加', '排序', '添加', '过滤']
    
    for verb in test_verbs:
        info = get_verb_info(verb)
        if info:
            print(f"\n动词: {verb}")
            print(f"  参数数量: {info.arity}")
            print(f"  修改模式: {info.mode}")
            print(f"  描述: {info.description}")
            print(f"  支持原地修改: {info.supports_modify()}")
            print(f"  支持函数式: {info.supports_functional()}")
            
            # Python映射
            mapping = get_python_mapping(verb)
            if mapping:
                print(f"  Python映射: {mapping[0]} ({mapping[1]})")
    
    print("\n" + "=" * 60)
    print(f"动词总数: {len(VERB_INFO)}")
    print("=" * 60)
