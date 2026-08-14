# CSV

> CSV/TSV读写、流式解析、类型推断、方言自动检测

## 包信息

| 属性 | 值 |
|------|-----|
| 版本 | 1.0.0 |
| 分类 | 开发工具 |
| 优先级 | ⭐ 核心包（已有 stdlib 桥接） |
| 公开函数 | 11 |
| FFI 声明 | 2 |
| stdlib 对应 | CSV读写器 |
| 备注 | 已有 Python 实现，桥接到 stdlib |

**关键词:** CSV, TSV, 表格, 数据, 解析

## 导入方式

```duan
导入 CSV
```

或

```duan
导入 标准CSV
```

## 函数列表

共 11 个公开函数

> CSV — duanpub 桥接模块
> 
> 基于 Python csv 库封装，函数名对齐 duanpub/packages/CSV/源.duan。
> 
> duanpub 原始包通过 C FFI 实现自研 CSV 解析器，
> 本桥接模块用 Python csv 模块替代，提供等价的 CSV/TSV 读写功能。
> 支持类型推断、方言自动检测。

### inferCellType

**参数:** `值`

推断单元格值类型，返回 'int'/'float'/'bool'/'string'

### convertCellValue

**参数:** `值`

将单元格字符串转换为推断后的类型值

### parseCSV

**参数:** `文本, 分隔符, 有表头`

解析 CSV 文本，返回二维列表（含表头）

### parseCSVFile

**参数:** `文件路径, 分隔符, 有表头`

解析 CSV 文件，返回二维列表

### parseCSVStream

**参数:** `文件对象, 分隔符`

从文件流解析 CSV，返回二维列表

### autoDetectDelimiter

**参数:** `文本`

自动检测 CSV 分隔符，返回分隔符字符

### toDictList

**参数:** `数据, 有表头`

将二维列表转为字典列表（第一行作为表头）

### to2DArray

**参数:** `字典列表, 表头`

将字典列表转为二维列表（含表头行）

### getColumn

**参数:** `数据, 列名或索引`

获取指定列的所有值（支持列名或索引）

### serializeCSV

**参数:** `数据, 分隔符, 有表头`

将二维列表序列化为 CSV 文本

### serializeCSVFile

**参数:** `文件路径, 数据, 分隔符, 有表头`

将二维列表序列化并写入 CSV 文件
