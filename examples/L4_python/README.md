# 光明 v4.0 — L4 外语引用层（Python 生态直通）演示

光明 v4.0 分层架构的 **L4 外语引用层** 原型：
通过 `引 Python:` / `结束引` 语法块，光明代码可以直接调用 **Python 生态 10 万+ 第三方库**。

## 两步模式（推荐写法）

```light
# 第1步：引 Python: 定义函数（只做一次）
引 Python:
    import numpy as np
    def l4_mean(arr):
        return float(np.mean(arr))
结束引

# 第2步：光明侧像普通函数一样调用
设 结果 = l4_mean([12, 25, 30, 43])
打印 结果
```

## 5 个演示 Demo

| 文件 | 功能 | 用到的 Python 包 |
|------|------|-----------------|
| `demo1_numpy_mean.light` | 用 numpy 计算数组均值 | numpy |
| `demo2_pandas_csv.light` | 用 pandas 创建并读取 CSV | pandas |
| `demo3_matplotlib_plot.light` | 用 matplotlib 画折线图保存 PNG | matplotlib |
| `demo4_requests_http.light` | 用 requests 发 HTTP GET | requests |
| `demo5_sklearn_iris.light` | 用 sklearn KNN 做鸢尾花分类 | scikit-learn |
| `all_in_one_demo.light` | **一个文件同时演示 5 个功能** | 全部 5 个包 |

## 快速开始

```bash
# 1. 安装依赖
pip install -r examples/L4_python/requirements.txt

# 2. 运行光明（任选一种方式）
#    方式A：统一入口 cli/light.py run
python -m cli.light run examples/L4_python/all_in_one_demo.light

#    方式B：如果已有 light 命令
light run examples/L4_python/demo1_numpy_mean.light
```

## 数据类型映射（光明 ↔ Python）

自动互转，不用手动处理：

| 光明类型 | Python 类型 |
|---------|------------|
| 整数 / 小 | `int` |
| 浮点 / 精 | `float` |
| 串 | `str` |
| 列 | `list` |
| 典 | `dict` |
| 真 / 假 | `True` / `False` |
| 空 | `None` |

## 说明

- 当前 v4.0 A/B 阶段运行时实现：Python 嵌入块直接输出到编译结果，共享作用域（未来 C/D 阶段会演进为：作用域隔离 + 数据级互操作，但外部函数调用写法不变）。
- 联网类 demo（`demo4_requests_http.light`）未联网时会打印友好提示，不会中断。
- 画图类 demo 输出 `.png` 到当前目录，可打开查看。
