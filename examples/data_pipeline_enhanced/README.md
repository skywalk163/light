# 数据管道增强版

用段言语言编写的数据管道示例，实现 CSV → JSON → SQLite 完整数据流水线，包含数据验证、错误处理、日志记录和统计报告。

## 功能

- CSV 数据解析（含格式错误检测）
- 数据清洗与验证（年龄、薪资范围校验）
- 统计计算（平均/最高/最低薪资、部门分布、城市分布）
- JSON 文件导出（数据 + 统计报告）
- SQLite 数据库存储与查询（按部门/城市分组统计）
- 日志记录（pipeline.log）
- 高薪人员筛选
- 按部门分组展示

## 运行

```bash
cd examples/data_pipeline_enhanced
duan run 主.duan
```

## 项目结构

- `主.duan` — 主程序入口，包含所有功能实现
- `pipeline.log` — 自动生成的日志文件
- `employees_enhanced.json` — 自动生成的员工数据 JSON 文件
- `statistics.json` — 自动生成的统计报告 JSON 文件
- `pipeline_enhanced.db` — 自动生成的 SQLite 数据库文件
- `README.md` — 项目说明文档