# CLI 待办事项管理器

用段言语言编写的命令行待办事项管理工具，演示完整的 CRUD 操作、JSON 文件持久化存储和命令行参数解析。

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
duan run 主.duan help
duan run 主.duan add "学习段言编程语言"
duan run 主.duan add "完成示例项目"
duan run 主.duan list
duan run 主.duan complete 1
duan run 主.duan edit 2 "完成所有示例项目"
duan run 主.duan search 示例
duan run 主.duan delete 2
```

## 项目结构

- `主.duan` — 主程序入口，包含所有功能实现
- `todos.json` — 自动生成的数据存储文件
- `README.md` — 项目说明文档