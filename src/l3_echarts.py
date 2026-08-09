"""
光明 L3 领域嵌入 - ECharts 可视化 DSL
=====================================
提供中文语法的 ECharts 图表配置生成能力。
支持柱状图、折线图、饼图、散点图四种图表类型。

用法示例（在 .light 文件中）：
    引 Python:
        from l3_echarts import L3ECharts
        l3_chart = L3ECharts()
    结束引

    设 配置 = l3_chart.图表配置("柱状图", 标题="销售数据", 数据=[10, 20, 30])
    设 配置 = l3_chart.图表配置("折线图", 标题="趋势", 数据=[5, 15, 25], 标签=["一月","二月","三月"])
"""

import json
from typing import List, Optional, Dict, Any, Union


class L3EChartsError(Exception):
    """L3 ECharts DSL 错误"""
    pass


class L3ECharts:
    """ECharts 可视化 DSL 入口

    支持中文关键字：
        - 图表配置(图表类型, 标题=..., 数据=..., 标签=..., ...)
        - 图表类型: "柱状图", "折线图", "饼图", "散点图"
    """

    # 支持的颜色列表
    DEFAULT_COLORS = [
        "#5470C6", "#91CC75", "#FAC858", "#EE6666",
        "#73C0DE", "#3BA272", "#FC8452", "#9A60B4",
    ]

    def __init__(self):
        self._chart_config = None

    # ==================== 公共 API ====================

    def 图表配置(self, 类型: str, **kwargs) -> Dict[str, Any]:
        """生成 ECharts 兼容的 JavaScript 配置字典

        参数:
            类型: 图表类型 ("柱状图" / "折线图" / "饼图" / "散点图")
            **kwargs:
                标题: str - 图表标题
                数据: list - 数据系列
                标签: list - X 轴标签（可选）
                副标题: str - 副标题（可选）
                宽度: str - 容器宽度（默认 "100%"）
                高度: str - 容器高度（默认 "400px"）
                颜色: list - 自定义颜色列表（可选）
                系列名: str - 系列名称（可选）
                堆叠: bool - 是否堆叠（可选，仅柱状图/折线图）
                平滑: bool - 是否平滑曲线（可选，仅折线图）

        返回:
            Dict[str, Any] - ECharts option 配置字典

        示例:
            >>> chart = L3ECharts()
            >>> cfg = chart.图表配置("柱状图", 标题="销售数据", 数据=[10, 20, 30])
            >>> cfg["title"]["text"]
            '销售数据'
        """
        类型 = 类型.strip()
        type_map = {
            "柱状图": self._build_bar,
            "折线图": self._build_line,
            "饼图": self._build_pie,
            "散点图": self._build_scatter,
        }

        builder = type_map.get(类型)
        if builder is None:
            raise L3EChartsError(f"不支持的图表类型：'{类型}'，仅支持：柱状图/折线图/饼图/散点图")

        # 验证参数
        self._validate_params(类型, kwargs)

        config = builder(**kwargs)
        self._chart_config = config
        return config

    def 导出JSON(self, 缩进: int = 2) -> str:
        """将当前图表配置导出为 JSON 字符串

        参数:
            缩进: JSON 缩进空格数（默认 2）

        返回:
            str - 格式化后的 JSON 字符串
        """
        if self._chart_config is None:
            raise L3EChartsError("尚未生成图表配置，请先调用 图表配置()")
        return json.dumps(self._chart_config, ensure_ascii=False, indent=缩进)

    def 导出HTML(self, 标题: str = "光明图表") -> str:
        """生成可直接运行的 HTML 文件内容

        参数:
            标题: 页面标题

        返回:
            str - 完整的 HTML 源码
        """
        if self._chart_config is None:
            raise L3EChartsError("尚未生成图表配置，请先调用 图表配置()")
        option_json = json.dumps(self._chart_config, ensure_ascii=False)
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{标题}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
    <style>
        html, body {{ margin: 0; padding: 0; height: 100%; }}
        #chart {{ width: 100%; height: 100vh; }}
    </style>
</head>
<body>
    <div id="chart"></div>
    <script>
        var chart = echarts.init(document.getElementById('chart'));
        var option = {option_json};
        chart.setOption(option);
        window.addEventListener('resize', function() {{ chart.resize(); }});
    </script>
</body>
</html>"""

    # ==================== 内部构建方法 ====================

    def _validate_params(self, 类型: str, kwargs: Dict[str, Any]) -> None:
        """验证参数合法性"""
        数据 = kwargs.get("数据")
        if 数据 is None:
            raise L3EChartsError(f"{类型} 必须提供 '数据' 参数")

        if not isinstance(数据, (list, tuple)):
            raise L3EChartsError(f"'数据' 参数必须是列表类型，收到 {type(数据).__name__}")

        if len(数据) == 0:
            raise L3EChartsError(f"'数据' 参数不能为空列表")

        # 饼图数据必须是字典列表
        if 类型 == "饼图":
            for item in 数据:
                if not isinstance(item, dict):
                    raise L3EChartsError(
                        f"饼图数据必须是字典列表（如 [{{\"name\":\"A\",\"value\":10}}]），"
                        f"收到 {type(item).__name__}"
                    )
                if "value" not in item:
                    raise L3EChartsError(f"饼图数据项缺少 'value' 字段：{item}")

    def _get_colors(self, kwargs: Dict[str, Any]) -> List[str]:
        """获取颜色配置"""
        return kwargs.get("颜色", list(self.DEFAULT_COLORS))

    def _get_title(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """构建标题配置"""
        标题 = kwargs.get("标题", "")
        副标题 = kwargs.get("副标题", "")
        title_cfg: Dict[str, Any] = {
            "text": 标题,
            "left": "center",
        }
        if 副标题:
            title_cfg["subtext"] = 副标题
        return title_cfg

    def _get_labels(self, kwargs: Dict[str, Any]) -> List[str]:
        """获取标签"""
        return list(kwargs.get("标签", []))

    def _build_bar(self, **kwargs) -> Dict[str, Any]:
        """构建柱状图配置"""
        数据 = kwargs.get("数据", [])
        标签 = self._get_labels(kwargs)
        系列名 = kwargs.get("系列名", "数据")
        堆叠 = kwargs.get("堆叠", False)

        series: Dict[str, Any] = {
            "name": 系列名,
            "type": "bar",
            "data": 数据,
            "itemStyle": {"borderRadius": [4, 4, 0, 0]},
        }
        if 堆叠:
            series["stack"] = "total"
            series["label"] = {"show": True, "position": "inside"}

        config: Dict[str, Any] = {
            "title": self._get_title(kwargs),
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "legend": {"data": [系列名]},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
            "xAxis": {"type": "category", "data": 标签, "axisLabel": {"rotate": 0}},
            "yAxis": {"type": "value"},
            "series": [series],
            "color": self._get_colors(kwargs),
        }

        if kwargs.get("宽度"):
            config["_width"] = kwargs["宽度"]
        if kwargs.get("高度"):
            config["_height"] = kwargs["高度"]

        return config

    def _build_line(self, **kwargs) -> Dict[str, Any]:
        """构建折线图配置"""
        数据 = kwargs.get("数据", [])
        标签 = self._get_labels(kwargs)
        系列名 = kwargs.get("系列名", "数据")
        平滑 = kwargs.get("平滑", True)

        series: Dict[str, Any] = {
            "name": 系列名,
            "type": "line",
            "data": 数据,
            "smooth": 平滑,
            "lineStyle": {"width": 3},
            "symbolSize": 8,
        }

        config: Dict[str, Any] = {
            "title": self._get_title(kwargs),
            "tooltip": {"trigger": "axis"},
            "legend": {"data": [系列名]},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
            "xAxis": {"type": "category", "data": 标签, "boundaryGap": False},
            "yAxis": {"type": "value"},
            "series": [series],
            "color": self._get_colors(kwargs),
        }

        if kwargs.get("宽度"):
            config["_width"] = kwargs["宽度"]
        if kwargs.get("高度"):
            config["_height"] = kwargs["高度"]

        return config

    def _build_pie(self, **kwargs) -> Dict[str, Any]:
        """构建饼图配置"""
        数据 = kwargs.get("数据", [])
        标题 = kwargs.get("标题", "")

        config: Dict[str, Any] = {
            "title": self._get_title(kwargs),
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "legend": {"orient": "vertical", "left": "left"}
            if len(数据) <= 8
            else {"show": False},
            "series": [
                {
                    "name": 标题 or "数据",
                    "type": "pie",
                    "radius": ["0%", "70%"],
                    "center": ["50%", "60%"],
                    "data": 数据,
                    "label": {"formatter": "{b}: {d}%"},
                    "emphasis": {
                        "itemStyle": {"shadowBlur": 10, "shadowOffsetX": 0, "shadowColor": "rgba(0,0,0,0.5)"}
                    },
                }
            ],
            "color": self._get_colors(kwargs),
        }

        if kwargs.get("宽度"):
            config["_width"] = kwargs["宽度"]
        if kwargs.get("高度"):
            config["_height"] = kwargs["高度"]

        return config

    def _build_scatter(self, **kwargs) -> Dict[str, Any]:
        """构建散点图配置"""
        数据 = kwargs.get("数据", [])
        标签 = self._get_labels(kwargs)
        系列名 = kwargs.get("系列名", "数据")

        # 如果数据是二维点列表，转换为 ECharts 格式
        formatted_data = []
        for item in 数据:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                formatted_data.append(item)
            elif isinstance(item, dict):
                formatted_data.append([item.get("x", 0), item.get("y", 0)])
            else:
                formatted_data.append([item, 0])

        config: Dict[str, Any] = {
            "title": self._get_title(kwargs),
            "tooltip": {"trigger": "item", "formatter": "({c})"},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
            "xAxis": {"type": "value"},
            "yAxis": {"type": "value"},
            "series": [
                {
                    "name": 系列名,
                    "type": "scatter",
                    "data": formatted_data,
                    "symbolSize": 12,
                }
            ],
            "color": self._get_colors(kwargs),
        }

        if 标签:
            config["xAxis"] = {"type": "category", "data": 标签}  # type: ignore

        if kwargs.get("宽度"):
            config["_width"] = kwargs["宽度"]
        if kwargs.get("高度"):
            config["_height"] = kwargs["高度"]

        return config

    # ==================== 便捷方法 ====================

    def 柱状图(self, 数据: List[Any], 标题: str = "", 标签: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """快速创建柱状图"""
        kwargs.update({"数据": 数据, "标题": 标题, "标签": 标签 or []})
        return self.图表配置("柱状图", **kwargs)

    def 折线图(self, 数据: List[Any], 标题: str = "", 标签: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """快速创建折线图"""
        kwargs.update({"数据": 数据, "标题": 标题, "标签": 标签 or []})
        return self.图表配置("折线图", **kwargs)

    def 饼图(self, 数据: List[Dict[str, Any]], 标题: str = "", **kwargs) -> Dict[str, Any]:
        """快速创建饼图"""
        kwargs.update({"数据": 数据, "标题": 标题})
        return self.图表配置("饼图", **kwargs)

    def 散点图(self, 数据: List[Any], 标题: str = "", **kwargs) -> Dict[str, Any]:
        """快速创建散点图"""
        kwargs.update({"数据": 数据, "标题": 标题})
        return self.图表配置("散点图", **kwargs)