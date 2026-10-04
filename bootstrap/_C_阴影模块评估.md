# 阴影模块补全评估 —— 断言工具 / 时间管理

> 轨道 C，两个「有意不带纯光明魔数」的阴影模块补全评估。
> 评估日期：2026-10-04。写域：仅 stdlib/断言工具.light、stdlib/时间管理.light、本报告；
> src/、bootstrap/、json 全未动；未 commit/push。

## 一、最终状态一览

| 模块 | 最终状态 | 首两行魔数 | 运行期加载 |
| --- | --- | --- | --- |
| stdlib/断言工具.light | **已补全 + 挂魔数** | 有「纯光明实现」 | hook 优先加载 .light，同名 .py 被遮蔽 |
| stdlib/时间管理.light | **维持阴影 + 原因见下** | 无（L-076 护栏） | 同名 .py 接管 |

回归：
- `python tools/ci/bootstrap_rate.py --root .` 退出码 0（自举率 73.73% 持平基线，影子数 75 持平，关键路径 18/18=100%）。
- `tests/test_stdlib_phase9.py::测试断言工具` 16 项 unittest 全过。
- `tests/test_pure_light_hook.py` 69 passed + 1 xfailed（含 L-076 时间管理护栏）。
- 自写 import 探针 `.scratch/probe_assert.py`：36 条行为断言全过。

---

## 二、断言工具.light —— 已补全

### 2.1 原阴影原因（R58）

原 .light 是「纯函数子集」，缺函数调用类 / 属性类高级断言。**故意不带魔数**——带了会让 hook
优先加载 .light 并无视同名 .py，导致 phase9 在钩子装载环境下
`from 断言工具 import 断言属性存在` 等高级断言 ImportError。

### 2.2 本轮补了什么

按 phase9 `测试断言工具` 类实际用到的 API 全量补进 .light：

- **异常断言**：断言抛出异常 / 断言不抛出异常 / 断言抛出特定异常 / 必抛出异常。
  用 `尝试: ... 捕获 错误:`（事件总线.light 既有方言）+ `isinstance(错误, 异常类型)`。
- **自定义条件断言**：断言满足条件 / 断言所有满足条件 / 断言任一满足条件。
  函数值作参数传入并调用（事件总线.light:处理器(事件名, 载荷) 既有先例）。
- **对象属性断言**：断言属性存在 / 断言属性不存在 / 断言属性值。
  直接调 Python builtin `hasattr` / `getattr`（选择器.light:44 `getattr(对象, "fileno", 空)` 既有先例）。
- **可调用断言**：断言可调用，走 `是函数(值)`（builtins.py:941 callable 地板）。
- **文件断言**：断言文件存在 / 断言文件不存在 / 断言目录存在 / 断言目录不存在。
  走 builtins 地板 `文件存在` / `目录存在`。
- **链式断言器**：类 链式断言器，方法链 返回 己；phase9 调 `.等于().不为无()/.长度为().包含()/.匹配正则()`。
- **断言子类**：用 `issubclass` Python builtin（原 .light 是空实现直接失败，一并修了）。

### 2.3 踩到的方言坑（记录给后续）

1. **`函数` 是保留字**：不能做参数名。原计划 `段落 断言抛出异常(函数, ...)` 编译报错，
   改成 `目标`。
2. **类构造默认参数不支持空字符串字面量**：`段落 构造(消息 等于 ""):` v3 parser 拒绝，
   要用 `段落 构造(消息 等于 空):` + 函数体 `如果 消息 == 空: 设 消息 为 ""`
   （字节缓冲.light:38 既有写法）。
3. **类方法不能叫 `等于`**：v3 parser 在模块级 `等于 ""` 默认参数 + 类方法叫 `等于`
   共存时崩（报一堆恢复误报）。解法：类方法叫 `相等于`，类定义后
   `setattr(链式断言器, "等于", 链式断言器.相等于)` 挂别名。
4. **模块级段落默认字符串参数必须 `等于 ""`，不能 `等于 空`**：code_generator 把
   `X 等于 空` 在模块级段落里错误编译成 `X, 等于: None`（类型注解语法），运行期
   TypeError。类构造里 `等于 空` 反而正确。
5. **默认异常类型**：`异常类型 等于 错误` 里的 `错误` 只在 `继承 错误` 子句被映射成
   Exception，在默认参数表达式里不映射（运行期 NameError）。改成 `异常类型 等于 Exception`。
6. **浮点默认参数**：`容差 等于 0.0001` 在长文件上下文里曾触发 parser 状态错乱，
   最终实测可编译，保留。

### 2.4 仍存在的语义差（不影响 phase9，记录备查）

- `断言字符串相等/包含子串/不包含子串/以开头/以结尾` 未补 .py 的 `忽略大小写` 关键字参数
  （.py 签名是 `(实际值, 期望值, 忽略大小写=False, 消息='')`，.light 是 `(实际值, 期望值, 消息='')`）。
  phase9 未用到；若将来按 .py 签名三参调用（第三参 True/False），.light 会把它当消息。
- `断言匹配正则` 用 `正则表达式.完全匹配`（整串匹配），.py 用 `re.match`（从开头匹配）。
  phase9 用例 `^test\d+$` 带 ^$，两边等价。
- `断言空白字符串/非空白字符串` 维持原 .light 语义（空/非空），未对齐 .py 的 `str.isspace()`。
  phase9 未测。
- `测试开始/测试结束/测试运行` 维持降级 docs（返回 0），未对齐 .py 的真计数。

---

## 三、时间管理.light —— 维持阴影

### 3.1 结论

**不补魔数**，维持现状：运行期由 stdlib/时间管理.py 接管。`tests/test_pure_light_hook.py`
的 L-076 护栏硬断言：

```python
assert not hasattr(mod, "__light_source__")
assert getattr(mod, "__file__", "").endswith(".py")
for 缺了就红 in ("计时函数", "计时器", "定时器", "倒计时", "多次计时"):
    assert hasattr(mod, 缺了就红)
assert "纯光明实现" not in "".join(light_text.splitlines(keepends=True)[:2])
```

只要首两行带魔数，这个护栏直接红。

### 3.2 .py 有而 .light 缺的 API，逐项归因

| API | 为何不能纯光明补 |
| --- | --- |
| `定时器` / `周期定时器`（threading.Timer / threading.Thread） | **threading 边界**。Light 纯光明腿无线程原语，hook 装载后无 `threading` 模块可引。 |
| `计时`（装饰器） | 需要包函数返回新函数（闭包），Light 方言未验证支持。 |
| `计时函数` / `多次计时` / `测量执行时间` | 需要把 Python 函数对象当参数传入并调用——Light 方言支持函数值调用（事件总线.light 实证），**但**这几个在 .py 里还包了 `*args, **kwargs` 透传，Light 不支持可变参数列表。phase3 测试 `计时函数(测试函数)` 不传额外参数可补，但 `多次计时(测试函数, 次数=5)` 返回 dict，dict 字面量在 Light 里要手写。 |
| `计时器` / `秒表` / `创建秒表`（纯状态机 + perf_counter） | **方言上可补**（perf_counter 已有内建，类/字段/方法 Light 支持），但补了也带不了魔数——因为下面 threading 缺口补不掉，.light 仍是 .py 真子集，带魔数会让 phase3 `from 时间管理 import 定时器` ImportError。 |
| `倒计时`（纯状态机 + sleep + perf_counter） | 同上，方言可补，但带魔数仍会因 `定时器` 缺名而触发 ImportError。 |
| `进程时间` / `线程时间` | **time.light 内建缺口**：stdlib/time.light 只暴露 `_dv_timestamp/_sleep_sec/_clock/_strftime`，没有 `time.process_time()` / `time.thread_time()` 的内建绑定。要补必须改 time.light 加内建（动 src/ 编译器或加 C 绑定）。 |
| `时区偏移` / `时区名称` / `夏令时` | **time.light 内建缺口**：`time.timezone` / `time.tzname` / `time.daylight` 无内建。同上。 |
| `解析时间`（time.strptime） / `时间元组转时间戳`（time.mktime） | **time.light 内建缺口**：stdlib/re.light 不是真 strptime（无结构化时间解析），无内建。 |

### 3.3 工作量评估（若要解锁时间管理纯光明）

按依赖从易到难：

1. **time.light 加 6 个内建绑定**（进程时间 / 线程时间 / 时区偏移 / 时区名称 / 夏令时 /
   解析时间 / 时间元组转时间戳）：在 src/ 编译器里加 runtime 内建函数，
   每个约 1-2 行 Python（直接 `time.process_time` 等）。**约 0.5 人日**。
   卡在哪：src/ 写域本轮不动；要动 src/runtime 内建表。
2. **纯状态机类补进 .light**（计时器 / 秒表 / 倒计时 / 创建秒表）：纯 Light 类，
   用 perf_counter 字段。**约 0.5 人日**。
3. **函数值计时 API**（计时函数 / 多次计时 / 测量执行时间）：Light 函数值调用已验证，
   但 `*args` 透传要在 Light 里手写 `列(...)` 或固定参数签名。**约 0.5 人日**。
4. **threading 缺口（定时器 / 周期定时器 / 计时装饰器）**：
   这是硬边界——Light 纯光明腿无线程原语。要么：
   - (a) 在 hook 装载后允许 `导入 threading`（标准库保护放行），.light 里 `导入 threading`
     直接用；
   - (b) 在 runtime 里暴露 `_thread` 内建。
   **约 1-2 人日**，但突破了「纯光明 = 无线程」的语义边界，需要架构决策。
5. **改 L-076 护栏**：test_pure_light_hook.py 的时间管理断言要改成「确认 .light 导出面
   覆盖 .py 全部 phase3 用到的名字」而非「硬禁魔数」。**约 0.25 人日**。

**总评**：时间管理要整体挂魔数，需要 (1)+(2)+(3)+(5) 共约 1.75 人日，且不碰 threading
就永远是 .py 真子集。**当前轮次不动，维持阴影**。

---

## 四、写域边界自检

- 改了：stdlib/断言工具.light（首两行魔数 + 补全高级断言）。
- 未动：stdlib/时间管理.light（保持原样）、src/、bootstrap/、json baseline。
- 新建：本报告。
- 未 commit / push。
- .scratch/ 下的探针脚本是临时验证物，不属交付物。
