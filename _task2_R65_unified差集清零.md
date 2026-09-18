# R65 任务2：unified（ANTLR）腿 builtin_map 差集清零

- 轮次：R65 ｜ 日期：2026-09-19 ｜ 执行：主 agent
- 背景：R62 补了 25 条「字符串处理同族」后，unified 腿 149 键 vs hook 腿 276 键 → 仍缺 **149 键**。

## 1. 结果总览

| 指标 | R62 末 | **R65** |
| --- | --- | --- |
| unified 腿键数 | 149 | **263** |
| hook 腿键数 | 276 | 276 |
| **差集（hook 有 / unified 缺）** | 149 | **35**（全部为 FFI 族） |
| 同键不同值（行为差异） | 7 | 7 |
| unified 独有键 | 22 | 22 |

## 2. 分族清单（共补 114 键）

| 族 | 补入键数 | 代表 |
| --- | --- | --- |
| 内建/通用 | 20 | `输出`→`print`、`长度`→`len`、`码位`→`ord`、`十六进制`、`最大值/最小值/绝对值/四舍五入`、`范围`、`全部/任意`、`列表/集合/布尔/类型` |
| 断言/解包 | 4 | `断言`→`_light_assert`、`unwrap`/`解包`→`_light_unwrap`、`取可选` |
| 异步 | 4 | `异步睡眠`→`asyncio.sleep`、`限时`→`asyncio.wait_for`、`创建任务`→`create_task`、`并发等待`/`首个完成` |
| 数学 | 18 | `平方根`/`对数`/`自然对数`/`常用对数`/`对数2`/`指数`/`正弦`…`最大公约数`、`幂`/`平方`/`立方` |
| 字符串别名 | 6 | `大写`/`小写`→`_light_builtin.转大写/转小写`、`重复`、`转文本`→`str`、`分割`、`查找` |
| 随机 | 4 | `随机数`→`random.random`、`随机`、`洗牌`、`拼接` |
| 文件/进程 | 33 | `_读文件`、`复制文件`、`重命名`、`复制目录`、`删目录树`、`创建临时目录`、`查找目录列表`、`读/写二进制文件`、`移动文件系统`、`真实路径`、`文件状态`、`句柄状态`、`低级打开/读/写/关闭`、`随机字节`、`原子替换`、`环境枚举`、`单调时钟`、`常量时间比较`、`只读/只写/新建/截断/追加/独占/二进制/不跟随符号链接`、`读取N字节`、`打印输出` |
| 编解码/哈希 | 9 | `序列化`/`反序列化`、`_b64_encode/_b64_decode`、`_md5`/`_sha1`/`_sha256`/`_sha512`/`_hmac_sha256` |
| 迭代 | 4 | `归约`/`折叠`→`functools.reduce`、`枚举`→`enumerate`、`打包`→`zip`、`打开文件`→`open` |
| 类型转换别名 | 9 | `转串`/`串`/`到字符串`/`转换字符串`/`转成字符串`→`转字符串`；`整`→`转整数`；`到数字`/`转数字`→`转浮点` |
| 其它 | 3 | `包含`→`_light_builtin.字符串包含`、`冻结`、`切分` |

## 3. 可解析性核查（逐键）

凡映射到 `_light_builtin.X` 的，必须确认 `stdlib/builtins.py` **确有该属性**，
否则补了只是把 `NameError` 换成 `AttributeError`。

- 核查方式：`importlib.util.spec_from_file_location('lb', 'stdlib/builtins.py')` 从文件路径加载，
  再 `hasattr(lb, X)`。
- ⚠️ **R62 已踩过的坑**：`sys.path.insert(0,'stdlib')` 后 `import builtins` 拿到的是
  **Python 内建模块**（名字冲突），核查结果全 MISSING —— 必须用 spec 从文件路径加载。
- 结果：**114 键全部通过，缺实现 0 条**。

## 4. 配套改动：产物头部补 import

新补的映射会引用 `math.*`、`random.*`、`functools.reduce`，
而 unified 产物头部原本只 `import sys/os/asyncio` → 直接补映射会得到 `NameError: math`。

`src/code_generator_unified.py::generate()` 新增：

```python
self._add_line("import math")
self._add_line("import random")
self._add_line("import functools")
self._add_line("import json")
```

其中 **`import json` 顺带修掉一个既有隐患**：补齐前 unified 的
`'JSON.解析': 'json.loads'` 就已在引用 `json`，而产物从未导入它。

实测产物头部：`['import sys', 'import os', 'import asyncio', 'import math', 'import random', 'import functools', 'import json']`。

## 5. ⛔ 刻意不补：FFI 全族 35 键

`取地址 解引用 指针偏移 FFI错误 系统错误码 设系统错误码 创建数组 设置数组 分配内存
释放内存 设指针值 创建回调 创建结构体值 创建枚举 创建联合体 解析库路径 变长参数调用
获取平台 查找库 结构体大小 字段偏移 结构体转字节 字节转结构体 注册回调 注销回调
获取回调 FFI调试 FFI禁用调试 FFI获取日志 位域设置 位域获取 创建函数指针 创建类型别名
定义宏 获取宏`

- 原因：这 35 键的值形如 `_light_ffi.取地址`，而 **`_light_ffi` 在 hook 腿产物里是
  `import stdlib.FFI as _light_ffi`（`code_generator.py:1124`）导入的，
  unified 产物头部根本没有这个 import**。直接补映射 → `NameError: _light_ffi`。
- 正确做法：把 hook 腿同款 guarded import 移植过来
  （`code_generator.py:1119-1130`，含 `_LightFFIUnavailable` 占位与 `_light_ffi_available` 特征位），
  且必须插在 `sys.path.insert(_light_stdlib)` **之后**。
- 改动面超出本轮（会改变每一个 unified 产物的头部），**登记为 R66**。
- 影响：FFI 相关 .light 走 unified 腿仍会 NameError，但**该腿当前无法端到端运行**
  （见下），故无实际回归。

## 6. ⚠️ 本轮踩坑：字符串值里的 `''` 被吞

生成插入文本时用的是 `f"'{k}': '{v}',"`，而 `拼接` 的值是
`lambda *a: (a[-1] if len(a) > 1 else '').join(...)` —— **内含 `''`**，
被 Python 的隐式字符串拼接吞掉，落盘成 `else ).join(...)`。

- 隐蔽性：`ast.parse` 照样通过（语法合法），**只有语义坏了**。
- 捕获方式：靠差集探针的「同键不同值」从 7 涨到 8 才发现。
- 修复：改用双引号包裹该条目，并在代码里留了注释警告。
- 教训：往源码里**程序化插入含引号的字符串值**必须用 `repr()`，不能手拼引号。

## 7. 验证

- 差集探针：unified 149 → **263 键**；差集 149 → **35**；同键不同值回到 **7**。
- 逐键抽查（`UnifiedCodeGenerator().builtin_map`）：
  `拼接`→`lambda *a: (a[-1] if len(a) > 1 else '').join(...)`（已修复）、
  `平方根`→`math.sqrt`、`归约`→`functools.reduce`、`随机数`→`random.random`、
  `包含`→`_light_builtin.字符串包含`、`去除空格`→`_light_builtin.去除空白`。
- ⚠️ **仍无法端到端验证**：`antlrparser/` 只有 `.g4`，缺 Java antlr4 生成的
  `LightLangLexer.py` / `LightLangParser.py` → `cli/light_unified.py --backend antlr`
  在本机与 0.82 都 `ModuleNotFoundError`。本轮验证仍为 **AST 级**
  （手工构造 `antlrparser.light_ast` 节点直接驱动 `UnifiedCodeGenerator`），
  验证的正是同一处查表，判据等价。**补 ANTLR 生成产物仍登记为待办。**

## 8. 行为差异 7 项（**本轮维持登记，未裁决**）

| 键 | hook 腿 | unified 腿 |
| --- | --- | --- |
| `首` | `lambda x: x[0]` | `operator.itemgetter(0)` |
| `末` | `lambda x: x[-1]` | `operator.itemgetter(-1)` |
| `整数` | `int` | `_light_builtin.整数` |
| `去重` | `list(set(x))` | `list(dict.fromkeys(x))`（保序） |
| `阶乘` | `math.factorial` | `_light_builtin.阶乘` |
| `排序` | `sorted` | `_light_builtin.列表排序` |
| `反转` | `reversed`（迭代器） | `_light_builtin.列表反转`（列表） |

任务书要求本轮**只裁决 `反转`**。裁决需要「改任一侧都有测试立红」的反跑判据；
由于 unified 腿**无法端到端跑**（缺 ANTLR 生成产物），**拿不出可执行判据**，
故按「拿不出判据就维持登记不动」的原则，**不裁决**，留待 ANTLR 产物补齐后再定。

## 9. 交付物

| 文件 | 改动 |
| --- | --- |
| `light-merge/src/code_generator_unified.py` | 补 114 键 + 产物头部 import（math/random/functools/json）+ `拼接` 引号修复 |
| `light-merge/_task2_R65_unified差集清零.md` | 本报告 |
