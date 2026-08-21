# CLI 待办事项管理器

用光明语言编写的命令行待办事项管理工具，演示完整的 CRUD 操作、JSON 文件持久化存储和命令行参数解析。

## 功能

- **add** - 添加待办事项
- **list** - 列出所有待办事项（含统计信息）
- **complete** - 标记待办事项为已完成
- **delete** - 删除待办事项
- **edit** - 编辑待办事项标题
- **search** - 搜索待办事项
- **clear** - 清空所有待办事项
- **help** - 显示帮助信息

## 运行

```bash
cd examples/todo_cli
light run 主.light help
light run 主.light add "学习光明编程语言"
light run 主.light add "完成示例项目"
light run 主.light list
light run 主.light complete 1
light run 主.light edit 2 "完成所有示例项目"
light run 主.light search 示例
light run 主.light delete 2
```

## 项目结构

- `主.light` — 主程序入口，包含所有功能实现
- `todos.json` — 自动生成的数据存储文件
- `README.md` — 项目说明文档