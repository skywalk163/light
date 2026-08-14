# v4 初学者体验与生态闭环任务规格书

**项目**: 段言（Duan）编程语言
**基线**: commit `16abd2b`（v3.5 — 复合标识符分词修复 + 逻辑运算符解析修复）
**环境**: Windows, Python 3.13, git-bash, 工作目录 `C:\dumatework\duan`
**约束**: 零回归（现有 1302 passed / 4 pre-existing failed 不可增加失败数）

---

## 现状盘点

### 教程体系
| 维度 | 现状 | 缺口 |
|------|------|------|
| 交互式 REPL 教程 | `cli/tutorial.py` 832行，11个练习（变量→FizzBuzz）| 无异常处理/文件IO/模块导入/模式匹配练习；完成度检查用子串匹配（脆弱）；无进度保存 |
| .duan 教程源文件 | `cli/tutorial_30min.duan` 853行，10节 | 无异常处理/文件IO/模块导入章节；`print` 和 `打印` 混用不一致 |
| Markdown 教程 | `docs/30分钟入门段言.md` 928行，10章 | 最完善的资源；同样缺异常/IO/模块章节 |
| 错误提示 | `parser_core.py` 中 `_make_friendly` + `_generate_hint` | 13个关键字提示 + 6个标点提示；无多错误报告；无拼写纠错；无教程链接 |

### 生态工具
| 维度 | 现状 | 缺口 |
|------|------|------|
| duanpub | 109包/2721函数/642FFI，自动索引 | 仅4个P0包有桥接；102个P2包未实现；stdlib函数硬编码为关键字（126个） |
| 转译器 | `pyproject2duan.py` 914行，覆盖几乎所有Python AST | 链式调用bug；点号导入需workaround；无语义校验；builtin反向映射不全 |
| 文档 | 57个.md文件 | 部分使用过时语法（v1.x）；无统一的当前语法参考 |

### 初学者真实痛点（优先级排序）
1. **写了看起来对的代码却报错** — 分词冲突导致 `处理函数` 被拆成 `处理`+`函数`
2. **报错信息看不懂** — 虽然有友好提示，但缺少"怎么改"的具体指导
3. **不知道哪些是内置的** — 126个stdlib函数被注册为关键字，与核心关键字混在一起
4. **教程到实战断层** — 教程只讲基础语法，不教怎么用 duanpub 导入库、怎么转译现有项目

---

## 任务总览

| 任务 | 类型 | 负责方 | 优先级 | 依赖 |
|------|------|--------|--------|------|
| T1: 错误恢复与提示增强 | 编译器 | DuMate | P0 | 无 |
| T2: 交互式教程扩展 | 教程 | DuMate | P0 | T1（错误提示） |
| T3: stdlib 函数关键字剥离 | 编译器 | DuMate | P1 | 无 |
| T4: 端到端实战教程 | 教程 | DuMate | P1 | T3（duanpub导入） |
| T5: 转译器链式调用修复 | 转译器 | Trae | P1 | 无（可并行） |
| T6: 转译器语义校验与报告 | 转译器 | Trae | P2 | T5 |

---

## 任务 T1: 错误恢复与提示增强

### 背景
当前 parser 遇到第一个错误就抛出 `ParseError` 停止。初学者需要反复修改-重试才能发现所有错误。同时，`_generate_hint` 只覆盖 13 个关键字和 6 个标点，很多常见错误没有修复建议。

### 涉及文件
- `src/parser_core.py` — `ParseError` 类、`_make_friendly()`、`_generate_hint()`
- `src/duan_parser_v3.py` — `DuanParser.parse()` 方法

### 目标

#### 1.1 扩展关键字提示（parser_core.py: `_generate_hint`）
在 `_reserved_hints` 字典中补充以下关键字：

```python
'遍历': '「遍历」用于循环遍历列表或范围。如：遍历 项 于 列表: ... 或 遍历 数 于 1至10: ...',
'当': '「当」用于条件循环（while）。如：当 条件: ...',
'尝试': '「尝试」用于异常处理。如：尝试: ... 捕获 错误类型 为 变量: ...',
'捕获': '「捕获」在「尝试」块中用于捕获异常。如：捕获 ValueError 为 e: ...',
'抛出': '「抛出」用于主动抛出异常。如：抛出 ValueError("消息")。',
'静态': '「静态」修饰段落使其成为静态方法。如：静态 段落 方法名(): ...',
'异步': '「异步」修饰段落使其成为异步函数。如：异步 段落 名字(): ...',
'等待': '「等待」用于等待异步操作完成（相当于 await）。如：设 结果 为 等待 异步函数()。',
'使用': '「使用」用于上下文管理器（with）。如：使用 文件 为 变量: ...',
'嵌入': '「嵌入」用于在段言中嵌入 Python/C 代码块。如：嵌入 Python: ... 结束嵌入',
'标注': '「标注」用于自定义装饰器。如：标注 装饰器名\n段落 名字(): ...',
'定义': '「定义」用于声明常量。如：定义 圆周率 为 3.14159。',
'继承': '「继承」用于类继承。如：类 子类 继承 父类: ...',
```

#### 1.2 新增分词冲突检测提示
在 `ParseError.__init__` 中，当 `token_value` 是单字关键字（如 `函`、`数`、`输`、`出`、`返`、`回`）时，检测是否可能是分词冲突：

```python
# 分词冲突检测
_split_conflict_hints = {
    '函': '词法分析可能将包含「函数」的标识符错误拆分。尝试在关键字和标识符之间加空格，或使用英文标识符。',
    '数': '词法分析可能将包含「数据」「数字」等的标识符错误拆分。尝试加空格分隔。',
    '输': '词法分析可能将包含「输出」的标识符错误拆分。尝试加空格分隔。',
    '返': '词法分析可能将包含「返回」的标识符错误拆分。尝试加空格分隔。',
}
```

#### 1.3 新增教程链接提示
在错误信息末尾，根据错误类型添加教程链接：

```python
# 教程链接
_tutorial_links = {
    'COLON': '参考教程：30分钟入门段言.md 第3章「条件判断」',
    'KEYWORD': '参考教程：30分钟入门段言.md 第2章「变量与赋值」',
    'FUNCTION': '参考教程：30分钟入门段言.md 第6章「函数/段落」',
    'CLASS': '参考教程：30分钟入门段言.md 第8章「类与对象」',
}
```

#### 1.4 多错误收集（Error Recovery）
在 `DuanParser.parse()` 中实现"恐慌模式"错误恢复：

```python
def parse(self, source: str) -> Module:
    """解析源代码，支持多错误收集"""
    self.errors = []
    try:
        return self._parse_internal(source)
    except ParseError as e:
        self.errors.append(e)
        # 尝试跳过到下一个语句边界（句号或换行），继续解析
        self._synchronize_to_statement_boundary()
        # 继续解析剩余语句
        while not self._is_at_end():
            try:
                stmt = self._parse_statement()
                if stmt:
                    self.statements.append(stmt)
            except ParseError as e2:
                self.errors.append(e2)
                self._synchronize_to_statement_boundary()
        # 如果收集了多个错误，一起报告
        if self.errors:
            raise ParseError(
                f"发现 {len(self.errors)} 个错误:\n\n" +
                "\n\n---\n\n".join(str(e) for e in self.errors)
            )
```

`_synchronize_to_statement_boundary()` 方法：跳过 token 直到遇到句号 `。`、换行 `\n`、DEDENT 或文件结束。

### 验收标准
1. 所有现有测试通过（1302 passed，不增加失败数）
2. 以下代码产生包含修复建议的错误信息：
   - `设 遍历 为 10。` → 提示"遍历是保留关键字"
   - `尝试: 打印(1)` → 提示"尝试需要搭配捕获"
   - `处理函数` 被错误拆分时 → 提示可能的分词冲突
3. 多错误场景：一段有 2 个语法错误的代码，一次性报告 2 个错误而非只报告第 1 个
4. 错误信息中包含教程章节引用

### 测试
```bash
cd C:\dumatework\duan
python -m pytest tests/ -q --tb=short -k "not antlr" --ignore=tests/test_module_system.py --ignore=tests/test_comprehensive.py --ignore=tests/test_modern_features.py --ignore=tests/test_ternary_antlr.py
```

---

## 任务 T2: 交互式教程扩展

### 背景
当前 `cli/tutorial.py` 有 11 个练习，覆盖变量到 FizzBuzz。但缺少异常处理、文件IO、模块导入、duanpub 使用等进阶内容。完成度检查用子串匹配（`expected in output`），脆弱且不可靠。

### 涉及文件
- `cli/tutorial.py` — `interactive_repl()` 函数中的 `exercises` 列表
- `cli/tutorial_30min.duan` — 补充章节
- `docs/30分钟入门段言.md` — 补充章节

### 目标

#### 2.1 新增 5 个练习（tutorial.py: exercises 列表）

**练习 12: 异常处理**
```
知识讲堂: 尝试/捕获/抛出 语法
目标: 用 try-except 捕获除零错误
示例:
  尝试:
      设 结果 为 10 除以 0。
  捕获 ZeroDivisionError 为 e:
      打印("不能除以零！")。
```

**练习 13: 文件读写**
```
知识讲堂: 使用/读取文件/写入文件
目标: 读取文件内容并输出
示例:
  使用 "data.txt" 为 文件:
      打印(文件.读取())。
```

**练习 14: 模块导入**
```
知识讲堂: 导入/从...导入
目标: 导入数学库并使用
示例:
  导入 数学。
  打印(数学.圆周率)。
```

**练习 15: 列表推导式**
```
知识讲堂: [表达式 遍历 变量 于 列表 若 条件]
目标: 用推导式生成平方数列表
示例:
  设 平方数 为 [x 乘以 x 遍历 x 于 1至5]。
  打印(平方数)。
```

**练习 16: 综合实战 — 待办列表**
```
知识讲堂: 综合运用变量、列表、循环、函数
目标: 实现一个简单的待办列表程序
示例:
  设 待办 为 []。
  段落 添加任务(任务):
      列表追加(待办, 任务)。
      打印("已添加: " 加上 任务)。
  添加任务("学习段言")。
  添加任务("写第一个程序")。
  打印("共 " 加上 串(列表长度(待办)) 加上 " 个任务")。
```

#### 2.2 改进完成度检查机制
将子串匹配替换为更可靠的检查方式：

```python
def _check_exercise(exercise: dict, output: str, namespace: dict) -> bool:
    """检查练习是否完成"""
    # 方式1: 精确输出匹配（expected 是完整输出）
    if 'expected_exact' in exercise:
        return output.strip() == exercise['expected_exact'].strip()
    
    # 方式2: 变量检查（检查 namespace 中的变量值）
    if 'check_vars' in exercise:
        for var_name, expected_val in exercise['check_vars'].items():
            if var_name not in namespace or namespace[var_name] != expected_val:
                return False
        return True
    
    # 方式3: 关键输出行匹配（所有行都必须出现）
    if 'expected_lines' in exercise:
        output_lines = [l.strip() for l in output.strip().split('\n')]
        for expected_line in exercise['expected_lines']:
            if expected_line.strip() not in output_lines:
                return False
        return True
    
    # 兼容旧方式: 子串匹配（逐步淘汰）
    if 'expected' in exercise:
        return exercise['expected'] in output
    return False
```

#### 2.3 新增进度保存与恢复
```python
import json

PROGRESS_FILE = os.path.join(os.path.expanduser("~"), ".duan_tutorial_progress")

def _save_progress(current_exercise: int, completed: set):
    """保存教程进度"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'current': current_exercise, 'completed': list(completed)}, f)

def _load_progress() -> dict:
    """加载教程进度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'current': 0, 'completed': []}
```

启动时检测到进度文件时提示：
```
检测到上次的学习进度：已完成 8/16 个练习，上次进行到练习 9
输入 continue 继续，输入 restart 重新开始，输入 list 查看所有练习
```

#### 2.4 补充 tutorial_30min.duan 和 Markdown 教程
在两个教程文件中补充对应章节：
- 第 11 节: 异常处理（尝试/捕获/抛出/最终）
- 第 12 节: 文件操作（使用/读取文件/写入文件）
- 第 13 节: 模块系统（导入/从...导入/duanpub 简介）

### 验收标准
1. 交互式教程有 16 个练习（原 11 + 新 5）
2. 完成度检查使用新机制（精确匹配/变量检查/行匹配），旧练习也迁移到新机制
3. 进度保存与恢复正常工作
4. `tutorial_30min.duan` 和 `30分钟入门段言.md` 有对应的 3 个新章节
5. 所有新练习的 demo 代码能被 DuanParser 正确解析和执行

### 测试
```bash
cd C:\dumatework\duan
python cli/tutorial.py --repl  # 手动验证各练习
python -c "
from cli.tutorial import _compile_duan, _run_duan
# 验证所有练习的 demo 代码都能编译执行
exercises = [...]  # 从 tutorial.py 获取
for i, ex in enumerate(exercises):
    try:
        _run_duan(ex['demo_code'])
        print(f'练习 {i+1}: OK')
    except Exception as e:
        print(f'练习 {i+1}: FAIL - {e}')
"
```

---

## 任务 T3: stdlib 函数关键字剥离

### 背景
当前 `VERB_ARITY` 有 168 个条目，其中 126 个是 3 字以上的 stdlib 库函数名（`读取文件`、`创建结构体值`、`MD5哈希`...）。这些函数被硬编码为关键字，导致：
- 词法膨胀（与用户标识符冲突）
- 转译器需要无穷尽的关键字冲突检测
- 每新增 stdlib 函数就要改 keywords.py

### 涉及文件
- `src/keywords.py` — 从 `VERB_ARITY` 中移除 stdlib 函数关键字
- `src/lexer.py` — 移除对这些关键字的词法识别
- `src/parser_expr.py` — 动词调用解析改为运行时名称查找
- `src/parser_stmt.py` — 同上
- `src/code_generator.py` — 库函数调用生成改为属性访问或名称查找
- `stdlib/duanpub/__init__.py` — 加载器需支持未导入时的友好报错

### 目标

#### 3.1 分类保留
`VERB_ARITY` 中保留以下两类：

**A. 核心语言动词**（保留为关键字）
```
打印, 输出, 读取, 首列末, 加减乘除模幂, 大于小于等于, 
乘以减去除以模以幂以, 取余整除, 且或非, 是空,
设定义, 列表创建（如果用于字面量语法）
```

**B. stdlib 库函数**（移除，改为导入后使用）
```
读取文件, 写入文件, 删除文件, 文件存在, 创建目录...
列表追加, 列表弹出, 列表排序, 列表长度...
字典创建, 字典获取, 字典设置...
解析JSON, 序列化JSON, 美化JSON...
MD5哈希, SHA1哈希, Base64编码...
随机整数, 随机浮点, 随机选择...
（共 126 个，全部移除）
```

#### 3.2 导入机制
用户通过 `导入` 语句使用 stdlib 函数：

```duan
# 方式1: 模块导入
导入 文件系统。
文件系统.写入文件("test.txt", "内容")。

# 方式2: 从模块导入
从 文件系统 导入 写入文件。
写入文件("test.txt", "内容")。

# 方式3: 便捷导入（向后兼容）
导入 文件系统: 读取文件, 写入文件, 文件存在。
读取文件("test.txt")。
```

#### 3.3 向后兼容层
在 `stdlib/duanpub/__init__.py` 加载器中，当用户直接使用未导入的 stdlib 函数时，不报"未定义"错误，而是：

```python
# 友好提示而非 NameError
def __getattr__(name):
    """当使用未导入的 stdlib 函数时，给出友好提示"""
    _KNOWN_STDLIB = _load_index()
    if name in _KNOWN_STDLIB:
        pkg = _KNOWN_STDLIB[name]['package']
        raise NameError(
            f"函数「{name}」属于 stdlib 包「{pkg}」。\n"
            f"请先导入：导入 {pkg}。 或 从 {pkg} 导入 {name}。\n"
            f"参考教程：30分钟入门段言.md 第13章「模块系统」"
        )
    raise NameError(f"名称「{name}」未定义。")
```

#### 3.4 迁移工具
扩展现有 `tools/migrate_syntax.py`，新增 `--stdlib` 模式：
- 扫描 `.duan` 文件中使用的 stdlib 函数名
- 在文件头部自动添加对应的 `导入` 语句
- 将裸函数调用改为 `模块.函数()` 或保持（如果已从模块导入）

### 验收标准
1. `VERB_ARITY` 从 168 减少到 ~42（仅核心语言动词）
2. `ALL_KEYWORDS` 从 91 减少到 ~65
3. 所有现有测试通过（需先迁移测试文件中的 stdlib 调用）
4. duanpub 109 包解析通过
5. 未导入直接使用 stdlib 函数时，给出友好的导入提示
6. 迁移工具能自动处理现有 `.duan` 文件

### 风险与对策
- **高风险**：大量测试文件直接使用 stdlib 函数关键字。需先用迁移工具批量处理。
- **中风险**：lexer 行为变化可能影响分词。需全量测试。
- **低风险**：向后兼容层确保旧代码不会直接 NameError，而是得到提示。

### 测试
```bash
cd C:\dumatework\duan
# 先迁移测试文件
python tools/migrate_syntax.py --stdlib tests/
# 全量测试
python -m pytest tests/ -q --tb=short -k "not antlr" --ignore=tests/test_module_system.py --ignore=tests/test_comprehensive.py --ignore=tests/test_modern_features.py --ignore=tests/test_ternary_antlr.py
# duanpub 解析验证
python -c "
from tools.gen_duanpub_index import scan_packages
results = scan_packages()
print(f'Packages: {len(results[\"passed\"])} passed, {len(results[\"failed\"])} failed')
"
```

---

## 任务 T4: 端到端实战教程

### 背景
当前教程只讲基础语法，初学者学完后不知道怎么实际用段言做项目。需要一篇"从零到项目"的端到端教程，串联 duanpub 导入、文件操作、转译器使用。

### 涉及文件
- `docs/端到端实战教程.md`（新建）
- `examples/weather_app/`（新建示例项目）

### 目标

#### 4.1 实战教程文档结构

```markdown
# 段言端到端实战：从零构建一个天气查询程序

## 第1步: 环境准备
- 安装段言
- 验证安装: duan --version
- 启动 REPL: duan repl

## 第2步: 基础语法回顾
- 变量、条件、循环、函数（链接到30分钟教程）

## 第3步: 使用 duanpub 导入库
- 导入 HTTP 客户端
- 导入 JSON 解析器
- 理解模块系统

## 第4步: 构建天气查询函数
- 定义函数接收城市名
- 调用 HTTP API
- 解析 JSON 响应
- 格式化输出

## 第5步: 文件操作
- 保存查询结果到文件
- 读取历史查询

## 第6步: 异常处理
- 网络错误处理
- JSON 解析错误处理
- 文件不存在处理

## 第7步: 用转译器迁移 Python 项目
- 安装转译器
- 转译现有 Python 代码
- 检查转译报告
- 修复转译不完整的部分

## 第8步: 打包与分享
- duan pkg build
- duan publish
```

#### 4.2 示例项目
在 `examples/weather_app/` 中创建一个完整的段言项目：

```
examples/weather_app/
├── main.duan          # 主程序
├── config.duan        # 配置模块
├── utils.duan         # 工具函数
├── duan.json          # 项目配置
└── README.md          # 项目说明
```

`main.duan` 示例：
```duan
导入 文件系统。
导入 JSON。
从 HTTP客户端 导入 获取。

段落 查询天气(城市名):
    设 响应 为 获取("https://api.weather.com/v1?city=" 加上 城市名)。
    设 数据 为 解析JSON(响应)。
    设 温度 为 数据["temperature"]。
    设 天气 为 数据["condition"]。
    打印(城市名 加上 ": " 加上 串(温度) 加上 "C, " 加上 天气)。
    返回 数据。

段落 保存查询(城市名, 数据):
    设 记录 为 城市名 加上 "," 加上 串(数据["temperature"]) 加上 "\n"。
    追加文件("history.txt", 记录)。
    打印("已保存查询记录")。

# 主程序
设 城市 为 "北京"。
尝试:
    设 结果 为 查询天气(城市)。
    保存查询(城市, 结果)。
捕获 Exception 为 e:
    打印("查询失败: " 加上 串(e))。
```

### 验收标准
1. `docs/端到端实战教程.md` 完成，包含 8 个步骤
2. `examples/weather_app/` 中的代码能被 DuanParser 正确解析
3. 教程中所有代码示例都能编译执行（HTTP 部分可用 mock 代替）
4. 教程覆盖：duanpub 导入、文件操作、异常处理、转译器使用

---

## 任务 T5: 转译器链式调用修复（Trae 任务）

### 背景
`pyproject2duan.py` 和 `py2duan_transpiler.py` 在转换 Python 链式方法调用（`a.b.c()`）时存在 bug。这是 v3.5 T4（TokenType.DOT 拆分）的前置依赖。

### 涉及文件
- `tools/ai_copilot/py2duan_transpiler.py` — `_visit_Attribute` 方法
- `tools/ai_copilot/pyproject2duan.py` — 同步修复

### 目标
以下 Python 代码正确转译：
```python
# Python
result = obj.method().chain().value
self.data.items.append(10)
```
转译为：
```duan
设 结果 为 obj.方法().链式().值。
己.data.items.列表追加(10)。
```

### 验收标准
1. 链式调用 `a.b.c()` 正确转译
2. 深层属性访问 `self.a.b.c` 正确转译
3. 混合调用 `obj.method().attr` 正确转译
4. 转译后的段言代码能被 DuanParser 正确解析

### 测试
```bash
cd C:\dumatework\duan
python tools/ai_copilot/test_transpiler_v2.py
```

---

## 任务 T6: 转译器语义校验与报告（Trae 任务）

### 背景
当前转译器是纯语法转换，不检查转译后的段言代码是否能被 DuanParser 正确解析。`_validate_duan()` 只报告 pass/fail，不提供详细信息。

### 涉及文件
- `tools/ai_copilot/pyproject2duan.py` — `_validate_duan()` 方法
- `tools/ai_copilot/py2duan_transpiler.py` — 错误收集

### 目标

#### 6.1 增强验证报告
转译完成后生成详细报告：

```
=== 转译报告 ===
文件总数: 25
转译成功: 22 (88%)
解析失败: 3 (12%)

失败详情:
1. utils.py:12 — ParseError: 期望句号「。」
   源码: result = obj.method().chain()
   转译: 设 结果 为 obj.方法().链式()
   原因: 链式调用解析不完整
   
2. models.py:45 — ParseError: 无法识别的语法元素
   源码: @dataclass
   转译: 标注 dataclass
   原因: 装饰器解析限制

建议:
- 3 个文件需要手动修复
- 链式调用问题参考: docs/trae_tasks_v3.5.md T1
- 装饰器问题参考: docs/trae_tasks_v3.5.md T3
```

#### 6.2 转译统计
在 `CONVERSION_REPORT.md` 中新增统计项：
- Python 特性使用统计（match-case、async、装饰器、类型注解...）
- 转译覆盖率（成功/失败/部分成功）
- 不支持的语法列表

### 验收标准
1. 转译报告包含每个文件的转译状态（成功/失败/部分）
2. 失败文件附带具体错误信息和源码行号
3. 报告末尾有修复建议和文档链接
4. `CONVERSION_REPORT.md` 包含 Python 特性使用统计

---

## 通用约束

### 1. 不要修改以下文件（与 Trae 并行工作时）
- `tools/ai_copilot/py2duan_transpiler.py` — Trae 负责（T5/T6）
- `tools/ai_copilot/pyproject2duan.py` — Trae 负责（T5/T6）

### 2. 编码规范
- 代码正文用 ASCII 半角标点
- Python 文件写 `encoding="utf-8"`
- `.sh` 文件用 LF 行尾
- 全角字符不要嵌入源代码字符串之外

### 3. 提交规范
- 每个 task 独立 commit
- commit message 格式：`feat: T1 错误恢复与提示增强` / `feat: T2 交互式教程扩展` 等
- 不要 push，只 commit 到本地

### 4. 测试规范
- 每完成一个 task 跑一次测试套件
- 确保零新增失败
- 如果修复了 pre-existing 失败，在 commit message 中说明

### 5. 优先级与依赖
```
T1 (错误提示) ──→ T2 (教程扩展) ──→ T4 (端到端教程)
                                        ↑
T3 (stdlib剥离) ────────────────────────┘

T5 (链式调用) ──→ T6 (语义校验)
```

- T1 和 T3 可并行
- T5 和 T6 可并行
- T2 依赖 T1（教程中使用新的错误提示）
- T4 依赖 T3（端到端教程中使用 duanpub 导入）

### 6. DuMate / Trae 分工

| 任务 | 负责方 | 理由 |
|------|--------|------|
| T1 错误恢复 | DuMate | 需要深入理解 parser 内部结构 |
| T2 教程扩展 | DuMate | 需要理解教程体系和教学设计 |
| T3 stdlib 剥离 | DuMate | 需要全面理解 keywords/lexer/parser 联动 |
| T4 端到端教程 | DuMate | 需要理解 duanpub 和生态全貌 |
| T5 链式调用 | Trae | 专注于转译器内部修复 |
| T6 语义校验 | Trae | 专注于转译器报告增强 |
