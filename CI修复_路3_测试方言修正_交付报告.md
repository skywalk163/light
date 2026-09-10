# 路 3 交付报告 — 测试方言与对象式 API 修正

> 分支：`task-3-测试方言修正`（commit `7faa860a`）
> 仓库真相源：`G:/dswork/duan-light-merge/light-merge`
> 日期：2026-09-10

## 验收结果

**0.88 上路 3 的 4 个文件：229 passed / 1 xfailed，AttributeError + NameError 全消除。**
本地同样全绿：227 passed / 2 skipped / 1 xfailed。

## 根因与修复

任务书预判的「对象式 API（'dict' object has no attribute '是否有效' 等）」与
「方言 NameError（`列表`/`无`/`split` 等）」两条线，实测共同根因只有一个：

**`tests/test_pure_light_hook.py` 在模块顶层全局 `install()` 光明导入钩子。**
pytest 收集阶段 import 该文件时钩子即全局生效，同进程内所有 stdlib 导入被改走
`.light` 版本——phase4/13/comprehensive 的 缓存/进度条/数据验证/参数解析/
高级文件/字符串常量 等模块因此拿到 `.light` 的 dict/bool 返回值与方言错误，
表现即任务书罗列的 34 红。

修复：
1. **钩子作用域收敛**：`test_pure_light_hook.py` 的顶层 `install()` 改为
   module 级 autouse fixture——钩子只在本模块测试执行期间安装、结束卸载，
   其它测试文件不再受影响。
2. **stdlib `.light` 方言修正**：`参数解析/字符串常量/格式化/模板/高级文件.light`
   中 `列表` 未定义等方言问题修正（即使钩子只在本模块生效，这些文件自身的
   纯光明测试也需要它们正确）。
3. **`stdlib/builtins.py` 补 `sort = 排序列表` 别名**：`统计.light` 百分位数依赖，
   与路 4 的「统计 sort」项配套。
4. 随带并入同一工作树里的路 1 在途修复（doc_block_scan 白名单、lightpub
   ENV_DEPENDENCY、native_leg 绝对路径、import_hook re 宽松断言、R13B HTTPS
   skip），见路 1 交付报告。

## 验证

- 本地：`pytest tests/test_stdlib_phase4.py tests/test_stdlib_phase13.py
  tests/test_stdlib_comprehensive.py tests/test_pure_light_hook.py -q`
  → 227 passed, 2 skipped, 1 xfailed
- 组合跑（钩子 + 原受污染文件）：`+ test_light_stdlib.py test_light_syntax.py`
  → 202 passed, 2 skipped, 1 xfailed
- 0.88（重传后）：229 passed, 1 xfailed

## 遗留
- 路 3 无遗留。任务书中「对象式→函数式逐个改测试」未再需要——根因（钩子全局
  泄漏）消除后，stdlib 返回值恢复函数式原貌，34 红自然转绿。
