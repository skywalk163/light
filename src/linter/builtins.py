# -*- coding: utf-8 -*-
"""光明内置名清单（LH-21 静态名检查的共享数据源）

单一职责：把「什么是光明内置名」这一事实集中到一处，供
  * `light_linter.py` 的未定义名检查（E002）使用；
  * `tools/内置名清单.py` 生成机器可读 JSON；
  * `tests/unit/test_LH21_未定义名.py` 对拍真实清单。

设计取舍
--------
* 优先从**代码生成器的 `builtin_map`**（权威注册表）读取，保证清单永远跟真实
  内置函数同步，杜绝「文档写了、代码没有」的静默漂移。
* 代码生成器导入失败（依赖缺失 / 循环导入）时**整体兜底**到一份手工维护的
  精选清单，保证 linter 在任何环境下都能跑（宁可漏报，不可让 check 崩溃）。
* **刻意不含** `去空白` 这类「常见但不存在」的错名——本清单是真实清单，
  错名留给检查器去识别并提示（`去除空白` 才对）。

T-0213（L-261）补的第三道约束：**清单里的名字必须「写得出 + 解析得到」**
------------------------------------------------------------------
历史缺口：本清单与 `stdlib/builtins.py` 的真身**从未对拍**，于是 `集合创建`、
`计数`、`连接` 这类「登记了、运行期却是 NameError」的名字能在清单里长期存活——
linter 因为「它是内置」而放行，错误一路留到运行期深处才炸（与 LH-21 / L-251 同源的假绿）。
门禁在 `tests/unit/test_LH40_清单对拍.py`，双闸：

  闸 A（登记）：每个名字都必须来自权威注册表——
      `code_generator.builtin_map` / `keywords.BUILTIN_TYPES` /
      `stdlib/builtins.py::__all__` / 值字面量。
      挡的是 `repr` 这一类：它能跑**只因为生成模块的 Python 内置名泄漏**，
      并不是光明内置名（T-0203 已裁定，真名 `转字符串`）。
  闸 B（可达）：走真实管线（LightParser → PythonCodeGenerator）生成 Python，
      在真命名空间里解析该名字；NameError / AttributeError 即失败。

两道闸各有各的漏网口，缺一不可：只查闸 A 会漏掉「登记在 builtin_map 里、
但映射出来的 Python 表达式跑不通」的名字；只查闸 B 会被 Python 内置名泄漏骗过。

因此本文件还负责挡掉两类**结构性不可用**的名字（见 `_UNSPELLABLE_NAMES` /
`_UNRESOLVABLE_ALIASES`）：它们确实出现在 `builtin_map` / `BUILTIN_TYPES` 里，
但源码写出来必然炸，留在清单里等于给假绿盖章。

T-0278（R220）现场复核：卡面 §一 的两张探针，结论与旧缺陷账不同
------------------------------------------------------------------
复测方式是 `subprocess` 真起 `python -m cli.light run`
（门禁见 `tests/unit/test_R220_linter清单对拍.py`），**不是**进程内 exec：

  `集合创建`        → rc=1 / `name '集合创建' is not defined`。
                     但它**已不在** `get_builtin_names()` 里（T-0213 剔除，见
                     `_CURATED_REMOVED`），所以现状不是「清单假绿」；真写法 `集合([...])`。
  `字典设置默认值`  → rc=1 / `name '字典设置默认值' is not defined`。
                     清单 0 处、`stdlib/builtins.py` 0 处：**从未登记也从未实现**，
                     是清单外的未落地提案，不属于「清单 → 运行期」对拍范围。

对拍结果：清单 333 名，332 个 `<名字>(...)` 形式在真 CLI 下**全部运行期可达**，
`新建` 是关键字式（`新建 类名()`）单列判定 ⇒ 三态处置里「假绿差异」为 **0 项**，
本卡不需要增删任何登记名。

另有一类容易误判的**反向脱节**：`stdlib/builtins.py::__all__` 里有 11 个名字
（`众数` / `圆周率` / `平均数` / `分割路径` / …）只在 `__all__`、不在
`code_generator.builtin_map`，真 CLI 裸调用全部 NameError。它们同样不在本清单里
（清单没盖章，是对的）。**不要**因为「`__all__` 说有」就把它们补登进清单——
那会凭空造出新的假绿；接线属 `src/code_generator.py`（T-0277 独占）。

判别力边界：R220 只钉「清单里的名字 → 运行期可达」**这一个方向**；反方向
（Python 内置名泄漏：`repr` / `len` 真 CLI 可达，却不是光明内置名）由 LH40 闸 A 负责，
R220 里有一条用例实证这个盲区。别把 R220 当双向判据用。
"""

import os
import sys
import functools
from typing import Dict, List, Set, Tuple


# 手工兜底清单（动态读取失败时使用）。**只放真实存在的内置名**，
# 与 src/code_generator.py 的 builtin_map 同口径；不含 `去空白`。
#
# T-0213 从这里摘掉 5 个「登记了但运行期 NameError」的伪名（见 `_EXCLUDED_NAMES`）：
#   `集合创建`（真名 `集合([])`）、`计数` / `连接`（是**方法名**，写在
#   `method_name_map` 里，只能 `.计数(x)` / `.连接(分隔符)` 这样用）、
#   `转布尔`（真函数在 `类型工具` 模块，须 `从 类型工具 导入`）、
#   `repr`（Python 内置名泄漏，不是光明内置名，真名 `转字符串`）。
_CURATED_BUILTIN_NAMES = frozenset({
    # 输出与类型
    '印', '打印', '显示', '输出', '写',
    '类型', '转字符串', '转整数', '转浮点', '转文本', '转串', '转成字符串',
    '字符串', '整数', '浮点数', '布尔', '列表', '字典', '集合', '文本', '任意', '空',
    # 数学与统计
    '绝对值', '求和', '求最大', '求最小', '最大值', '最小值', '四舍五入', '次方',
    '范围', '全部', '任意', '去重', '平方根', '对数', '自然对数', '常用对数', '对数2',
    '指数', '正弦', '余弦', '正切', '反正弦', '反余弦', '反正切', '反正切2', '阶乘',
    '向上取整', '向下取整', '最大公约数', '平方', '立方', '取模', '均值', '方差',
    '标准差', '中位数', '随机数', '随机整数', '随机浮点', '随机选择', '洗牌', '随机字节',
    # 字符串
    '拼接', '分割', '替换', '查找', '截取', '去除空白', '大写', '小写', '转大写',
    '转小写', '重复', '切分', '开头', '结尾', '长度', '长', '子串',
    '最后索引', '去除左侧空白', '去除右侧空白', '去除空格', '字符串长度', '字符串获取',
    '字符串包含', '字符串替换', '字符串分割', '分割字符串', '连接字符串', '替换字符串',
    '字符串截取', '查找子串', '替换字符串次数', '截取到末尾', '字符串计数', '字符串重复',
    '字符串反转', '转标题', '字符串对齐居中', '字符串对齐左', '字符串对齐右',
    '是字母', '是空白', '是数字', '是数字符', '是空', '是字符串', '是列表', '是字典',
    '是整数', '是浮点', '是布尔', '是函数', '是字节', '是负零', '显示宽度',
    # 容器
    '列表创建', '新建列表', '列表获取', '列表追加', '列表弹出', '列表插入', '列表排序',
    '排序列表', '列表反转', '列表包含', '列表长度', '字典创建', '新建字典', '字典设置',
    '字典删除', '字典键列表', '字典值列表', '字典项列表', '字典包含键', '字典获取',
    '副本', '浅拷贝', '深拷贝', '冻结',
    # 高阶
    '筛选', '映射', '归约', '折叠', '排序', '反转', '枚举', '打包', '去重',
    # 文件系统
    '读取文件', '写入文件', '原子写入', '追加文件', '文件存在', '是文件', '目录存在', '路径存在',
    '创建目录', '删除文件', '删除目录', '列出目录', '列出文件', '文件大小', '复制文件',
    '重命名', '复制目录', '删目录树', '创建临时目录', '查找目录列表', '读二进制文件',
    '写入二进制文件', '绝对路径', '连接路径', '目录名', '文件名', '扩展名', '真实路径',
    '文件状态', '环境变量', '主目录', '随机UUID', '设置环境变量', '参数列表', '用户参数',
    '退出程序', '当前目录', '切换目录', '执行命令', '移动文件系统',
    # 编码 / 网络
    '序列化', '反序列化', '解析JSON', '序列化JSON', '美化JSON', 'XML解析', 'XML生成',
    '_b64_encode', '_b64_decode', '_md5', '_sha1', '_sha256', '_sha512', '_hmac_sha256',
    '打开文件', '读取行', '读取N字节', '写入输出', '打印输出', '刷新输出', '写入错误',
    '打印错误', '码位', '字符自码位', '十六进制', '首', '末', '解包', 'unwrap',
    # 异步
    '异步睡眠', '睡眠异步', '限时', '创建任务', '并发等待', '首个完成',
    # 时间
    '时间戳', '格式化时间', '时间格式化', '睡眠秒', '播种随机种子',
    # FFI
    '取地址', '解引用', '指针偏移', 'FFI错误', '系统错误码', '设系统错误码',
    '创建数组', '设置数组', '分配内存', '释放内存', '设指针值', '创建回调',
    '创建结构体值', '创建枚举', '创建联合体', '解析库路径', '变长参数调用', '获取平台',
    '查找库', '结构体大小', '字段偏移', '结构体转字节', '字节转结构体', '注册回调',
    '注销回调', '获取回调', 'FFI调试', 'FFI禁用调试', 'FFI获取日志', '位域设置',
    '位域获取', '创建函数指针', '创建类型别名', '定义宏', '获取宏',
})


# ── T-0213 剔除名单（两条结构性不可用，理由见模块 docstring）──────────────────
# 1) 写不出来：名字尾部就是保留关键字，词法阶段先切关键字，源码里落地的**不是**这个名字。
#    `打印(FFI调试(1))`   → 生成 `FFI(None)`    → NameError: name 'FFI' is not defined
#    `设 r 为 XML生成(空)` → 生成 `XML(None)`    → NameError: name 'XML' is not defined
#    真身确实在（`_light_ffi.启用调试` / `stdlib/builtins.py::XML生成`），但**用户写不出来**；
#    留在清单里等于让 linter 给一个必然 NameError 的写法盖章。解析器侧修复（别把关键字
#    切进标识符）不在本卡 paths 内，已记入 T-0213 summary 另开卡。
_UNSPELLABLE_NAMES = frozenset({'FFI调试', 'XML生成'})

# 2) 只在类型标注位置有意义的缩写别名：`BUILTIN_TYPES` 里登记了，但 `builtin_map` 里
#    **没有**对应映射，写成调用必炸（实测 `设 x 为 集()` / `数(1)` → NameError）。
#    `集合`/`字典`/`整数`/`列表`/`文本`/`布尔`/`任意`/`串`/`列` 都有真映射，故不在剔除之列。
#    （标注在生成期被擦除，`设 x: 集 为 空` 能跑并不代表 `集` 是可调用的内置名；
#     若将来要给标注单列名单，应由 linter 侧另建一张表，别混进「内置函数名」清单。）
_UNRESOLVABLE_ALIASES = frozenset({'集', '典', '数', '浮数', '小数'})

# 剔除理由汇总（T-0213 的清理账目：summary / 门禁都引用这张表，不许静默删名）。
# 键必须与 `_UNSPELLABLE_NAMES ∪ _UNRESOLVABLE_ALIASES ∪ _CURATED_REMOVED` 完全一致。
_CURATED_REMOVED = {
    '集合创建': '伪名：`集合` 是内置类型，真写法 `集合([])`（T-0203 已同裁定）',
    '计数': '方法名（`method_name_map` 里是 `count`），只能 `.计数(x)`；不是地板内置名',
    '连接': '方法名（`method_name_map` 里是 `join`），只能 `.连接(分隔符)`；真名 `连接字符串`',
    '转布尔': '真函数在 `类型工具` 模块，须 `从 类型工具 导入`；不是地板内置名',
    'repr': 'Python 内置名泄漏（能跑只因生成模块的命名空间有它），真名 `转字符串`',
    '真值': '不是真名字：`设 y 为 真值` → NameError（字面量只有 `真` / `假` / `空`）',
    '假值': '不是真名字：`设 y 为 假值` → NameError（字面量只有 `真` / `假` / `空`）',
}

_EXCLUDED_NAMES = {
    **_CURATED_REMOVED,
    **{n: '词法把名字尾部当保留关键字切开，源码里写不出来' for n in _UNSPELLABLE_NAMES},
    **{n: '只在类型标注位置有意义的缩写别名，builtin_map 无映射，调用必 NameError'
       for n in _UNRESOLVABLE_ALIASES},
}


def _load_dynamic_builtins() -> Tuple[Set[str], Dict[str, str]]:
    """返回内置名集合与来源映射。

    **口径**：以手工兜底清单 `_CURATED_BUILTIN_NAMES` 为**保证下限**，再叠加
    代码生成器 `builtin_map` / `BUILTIN_TYPES` 的动态注册。这样：
      * 即使代码生成器导入失败，清单也完整（宁可漏报，不可崩）；
      * 代码生成器新增的内置名自动进入清单（永不落后于真实表）；
      * `去空白` 这类「常见但不存在」的错名**刻意不在**兜底清单里，也不在
        真实表里 → 清单永远不会误含它。

    最后统一过一道 `_EXCLUDED_NAMES` 剔除（见上）：其中 `_UNSPELLABLE_NAMES` /
    `_UNRESOLVABLE_ALIASES` 来自权威表但源码写出来必然 NameError，必须在这里挡掉；
    `_CURATED_REMOVED` 已从兜底清单里删掉，这里的 discard 只是幂等兜底
    （防止将来有人把它们加回 `builtin_map` / `BUILTIN_TYPES` 又悄悄复活）。
    """
    names: Set[str] = set(_CURATED_BUILTIN_NAMES)
    sources: Dict[str, str] = {}
    for name in _CURATED_BUILTIN_NAMES:
        sources.setdefault(name, '内置函数')

    try:
        from code_generator import PythonCodeGenerator
        bm = getattr(PythonCodeGenerator(), 'builtin_map', None) or {}
        for k in bm:
            if isinstance(k, str) and k:
                names.add(k)
                sources.setdefault(k, '内置函数')
    except Exception:  # pragma: no cover - 兜底，绝不把 check 拖崩
        pass

    try:
        from keywords import BUILTIN_TYPES
        for k in BUILTIN_TYPES:
            if isinstance(k, str) and k:
                names.add(k)
                sources.setdefault(k, '内置类型')
    except Exception:  # pragma: no cover - 兜底
        pass

    # 字面量/常量名不算可调用内置函数，但属于「语言内置名」，放行不报未定义。
    # T-0213：`真值` / `假值` 曾在此处登记，但两者**不是**真名字（实测
    # `设 y 为 真值` → NameError），已摘掉；`真` / `假` / `空` 走字面量真身，保留。
    for k in ('真', '假', '空', 'True', 'False', 'None'):
        names.add(k)
        sources.setdefault(k, '字面量')

    for bad in _EXCLUDED_NAMES:
        names.discard(bad)
        sources.pop(bad, None)
    return names, sources


@functools.lru_cache(maxsize=1)
def get_builtins() -> Tuple[Set[str], Dict[str, str]]:
    """返回 (内置名集合, 来源映射)。

    带缓存：多次调用不重复触发代码生成器导入。返回集合与映射均为**只读**语义，
    调用方不得修改。
    """
    return _load_dynamic_builtins()


def get_builtin_names() -> Set[str]:
    """返回全部内置名的集合（含内置函数、内置类型、字面量名）。"""
    names, _ = get_builtins()
    return set(names)


def get_builtin_sources() -> Dict[str, str]:
    """返回 {内置名: 来源}，来源为 '内置函数' / '内置类型' / '字面量'。"""
    _, sources = get_builtins()
    return dict(sources)


def get_builtin_sorted() -> List[str]:
    """返回排序后的内置名列表。"""
    return sorted(get_builtin_names())


def is_builtin(name: str) -> bool:
    """名字是否为内置名（含字面量名）。"""
    if not name:
        return False
    return name in get_builtin_names()
