# ANTLR 腿解析冒烟矩阵（cli/light_unified.py --backend antlr 的前置能力）

- 生成时间：2026-09-20 10:23:23
- 集合：`examples/*.light`（42 个文件）
- 结果：**0 / 42 解析通过**（耗时 4.1s，仅解析不执行）
- 工具：`scripts/antlr_leg_smoke.py`

## 失败归类

| 归类 | 数量 |
|---|---|
| 缺语句终止符(PERIOD) | 15 |
| 其它 | 9 |
| 多余 token | 7 |
| 块未闭合(缺 `结束`) | 5 |
| 缺括号 | 3 |
| 语法不匹配 | 3 |

## 逐文件

| 文件 | 结果 | 首错 |
|---|---|---|
| `examples/_test_nested_closure.light` | FAIL | 第9行, 第3列: 多余的 '外层'，此处应为 LPAREN |
| `examples/advanced.light` | FAIL | 第10行, 第12列: 语法错误，无法解析此处的输入   建议: 请检查此行的语法结构，是否有拼写错误或缺少关键字 |
| `examples/basic.light` | FAIL | 第5行, 第0列: 在 '设' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/bootstrap_eval.light` | FAIL | 第4行, 第3列: 在 '"=== 光明自举示例：表达式求值器 ==="' 处缺少 'LPAREN' |
| `examples/bootstrap_lexer.light` | FAIL | 第4行, 第3列: 在 '"=== 光明自举示例：简单词法分析器 ==="' 处缺少 'LPAREN' |
| `examples/calculator.light` | FAIL | 第26行, 第2列: 在 '段落' 处缺少 '缁撴潫' |
| `examples/class_access_control.light` | FAIL | 第5行, 第7列: 语法错误，无法解析此处的输入   建议: 请检查此行的语法结构，是否有拼写错误或缺少关键字 |
| `examples/class_complete.light` | FAIL | 第6行, 第7列: 语法错误，无法解析此处的输入   建议: 请检查此行的语法结构，是否有拼写错误或缺少关键字 |
| `examples/class_example.light` | FAIL | 第12行, 第2列: 在 '段落' 处缺少 '缁撴潫' |
| `examples/class_static.light` | FAIL | 第5行, 第7列: 语法错误，无法解析此处的输入   建议: 请检查此行的语法结构，是否有拼写错误或缺少关键字 |
| `examples/ffi_comprehensive.light` | FAIL | 第4行, 第4列: 语法错误，无法解析此处的输入   建议: 请检查此行的语法结构，是否有拼写错误或缺少关键字 |
| `examples/ffi_math.light` | FAIL | 第4行, 第4列: 语法错误，无法解析此处的输入   建议: 请检查此行的语法结构，是否有拼写错误或缺少关键字 |
| `examples/ffi_system.light` | FAIL | 第8行, 第4列: 语法错误，无法解析此处的输入   建议: 请检查此行的语法结构，是否有拼写错误或缺少关键字 |
| `examples/hanoi.light` | FAIL | 第12行, 第0列: 多余的 '结束'，此处应为 <EOF>、K_IF、璁? 等 |
| `examples/hello.light` | FAIL | 第11行, 第0列: 在 '打印' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/module_demo.light` | FAIL | 第15行, 第0列: 多余的 '结束'，此处应为 <EOF>、K_IF、璁? 等 |
| `examples/my_first.light` | FAIL | 第11行, 第0列: 在 '如果' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/student_management.light` | FAIL | 第14行, 第4列: 在 '段落' 处缺少 '缁撴潫' |
| `examples/test_L051.light` | FAIL | 第10行, 第4列: 在 '设' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/test_L052.light` | FAIL | 第5行, 第0列: 在 '打印' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/test_L056.light` | FAIL | 第24行, 第4列: 在 '设' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/test_L068.light` | FAIL | 第16行, 第2列: 在 '段落' 处缺少 '缁撴潫' |
| `examples/test_L069.light` | FAIL | 第5行, 第17列: 语法错误，无法解析此处的输入   建议: 请检查此行的语法结构，是否有拼写错误或缺少关键字 |
| `examples/test_L070.light` | FAIL | 第4行, 第16列: 语法不匹配: 遇到了 '{'，期望 K_IF、鎺ユ敹、杈撳叆 等   建议: 检查括号是否匹配，是否缺少左括号「（」或右括号「）」 |
| `examples/test_L071.light` | FAIL | 第7行, 第8列: 多余的 '{'，此处应为 K_IF、鎺ユ敹、杈撳叆 等 |
| `examples/test_L072.light` | FAIL | 第24行, 第0列: 在 '段落' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/test_L073.light` | FAIL | 第8行, 第4列: 多余的 '类'，此处应为 K_INHERIT、瀹炵幇、COLON 等 |
| `examples/test_L074.light` | FAIL | 第10行, 第9列: 语法不匹配: 遇到了 '{'，期望 K_IF、鎺ユ敹、杈撳叆 等   建议: 检查括号是否匹配，是否缺少左括号「（」或右括号「）」 |
| `examples/test_L075.light` | FAIL | 第7行, 第6列: 多余的 'x4E00'，此处应为 RPAREN |
| `examples/test_L076.light` | FAIL | 第14行, 第2列: 在 '打印' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/test_L077.light` | FAIL | 第9行, 第2列: 在 'l' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/test_L170.light` | FAIL | 第14行, 第9列: 语法不匹配: 遇到了 '{'，期望 K_IF、鎺ユ敹、杈撳叆 等   建议: 检查括号是否匹配，是否缺少左括号「（」或右括号「）」 |
| `examples/test_L172.light` | FAIL | 第27行, 第0列: 语法错误，无法解析此处的输入   建议: 请检查此行的语法结构，是否有拼写错误或缺少关键字 |
| `examples/test_bubble.light` | FAIL | 第15行, 第17列: 多余的 '结束'，此处应为 <EOF>、K_IF、璁? 等 |
| `examples/test_fib.light` | FAIL | 第8行, 第0列: 在 '当' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/test_fib_src.light` | FAIL | 第9行, 第0列: 在 '当' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/test_hello.light` | FAIL | 第4行, 第0列: 在 '设' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/test_hello_src.light` | FAIL | 第4行, 第0列: 在 '设' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/test_para.light` | FAIL | 第4行, 第0列: 在 '设' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/test_turing.light` | FAIL | 第6行, 第2列: 在 '返回' 处缺少 'PERIOD'   建议: 每条语句末尾需要加中文句号「。」 |
| `examples/type_annotation_demo.light` | FAIL | 第4行, 第3列: 在 '"=== 光明类型注解示例 ==="' 处缺少 'LPAREN' |
| `examples/typed_demo.light` | FAIL | 第11行, 第2列: 在 '否则' 处缺少 '缁撴潫' |
