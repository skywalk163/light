# duan-blocks

段言积木组合平台——把「用户自然语言需求」映射为「预置积木的组合装配」，零 token、全离线。

> ✅ 已发布到 PyPI：`pip install duan-blocks` — https://pypi.org/project/duan-blocks/

## 演示

![duan-blocks 概念海报](https://raw.githubusercontent.com/skywalk163/duan/main/blocks_pkg/duan-blocks-poster.png)

- 🎬 概念演示视频（10s，1080P）：[`demo_video/Cinematic_product_launch_video_2026-08-10T13-02-22.mp4`](https://raw.githubusercontent.com/skywalk163/duan/main/demo_video/Cinematic_product_launch_video_2026-08-10T13-02-22.mp4)（仓库 `demo_video/` 目录）
- 🖥️ 本地交互演示页：安装后 `uvicorn duan_blocks.api:app --port 8123` → 打开 `http://localhost:8123/`（输入需求实时看积木组合与运行结果）

```
# 命令行
duan-combo "对一批数字求和再算平均" --输入 "[1,2,3,4,5]"
duan-combo "把这段中文转成拼音" --输入 '"你好"' --json   # 结构化诊断

# Web/API（需 fastapi uvicorn）
uvicorn duan_blocks.api:app --port 8123
#   GET /        演示页（输入需求实时看组合）
#   POST /combo  {"requirement":"半径5的圆有多大","input":"5"}
```

- **零 token 常态**：选块/校验/接线/粘合全本地（概念图 + TF-IDF 混合选块，不调 LLM）。
- **兜底沉淀**：仅能力缺失时经 LLM（或本地规则）生成新积木并永久入库存，下次零 token 复用。
- **运行依赖**：段言运行时（`pip install duan`）；拼音/繁简/历法等可选
  `pip install duan-blocks[zh]`（pypinyin / opencc / lunardate）。
- **定位**：`DUAN_BLOCKS_LIB` 环境变量 → 包内数据（wheel 自带 `_data/积木库`）→ 仓库内。
- **构建发布**：先 `python blocks_pkg/打包数据.py` 复制积木库数据，再 `python -m build blocks_pkg` 产出 sdist+wheel。
