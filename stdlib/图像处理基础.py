# -*- coding: utf-8 -*-
"""
图像处理基础工具

提供基于 PIL (Pillow) 的简单图像处理功能封装，包括打开、保存、缩放、裁剪、旋转、
滤镜、颜色转换等操作。

用法:
    from 标准库.图像处理基础 import 打开图像, 新建图像, 调整大小, 裁剪, 旋转

示例:
    设 图像 = 打开图像("photo.jpg")
    设 缩略图 = 调整大小(图像, 200, 200)
    保存图像(缩略图, "thumb.jpg")
"""

from typing import Optional, Tuple, Union, List

# 尝试导入 PIL
try:
    from PIL import Image as _Image
    from PIL import ImageFilter as _ImageFilter
    from PIL import ImageEnhance as _ImageEnhance
    from PIL import ImageDraw as _ImageDraw
    from PIL import ImageFont as _ImageFont
    PIL_可用 = True
except ImportError:
    PIL_可用 = False

    # 创建虚拟类，以便在导入时不会崩溃
    class _Image:
        """PIL 不可用时的虚拟类"""
        @staticmethod
        def open(*args, **kwargs):
            raise ImportError("Pillow 未安装，请运行: pip install Pillow")

        class Image:
            pass


class 图像对象:
    """图像对象封装类

    Attributes:
        宽: 图像宽度（像素）
        高: 图像高度（像素）
        模式: 图像模式（RGB, RGBA, L 等）
        格式: 图像格式（JPEG, PNG 等）
    """

    def __init__(self, pil_image: _Image.Image):
        """初始化图像对象

        Args:
            pil_image: PIL Image 对象
        """
        self._图像 = pil_image
        self.宽: int = pil_image.width
        self.高: int = pil_image.height
        self.模式: str = pil_image.mode
        self.格式: Optional[str] = pil_image.format

    def 获取PIL对象(self) -> _Image.Image:
        """获取底层 PIL Image 对象

        Returns:
            PIL Image 对象
        """
        return self._图像

    def 复制(self) -> "图像对象":
        """复制图像

        Returns:
            新的图像对象
        """
        return 图像对象(self._图像.copy())

    def 显示(self):
        """显示图像（使用系统默认图片查看器）"""
        self._图像.show()

    def 获取像素(self, x: int, y: int) -> Tuple[int, ...]:
        """获取指定位置的像素值

        Args:
            x: 横坐标
            y: 纵坐标

        Returns:
            像素值元组，RGB 图像返回 (R, G, B)
        """
        return self._图像.getpixel((x, y))

    def 设置像素(self, x: int, y: int, 颜色: Tuple[int, ...]):
        """设置指定位置的像素值

        Args:
            x: 横坐标
            y: 纵坐标
            颜色: 像素颜色值
        """
        self._图像.putpixel((x, y), 颜色)


def 检查PIL():
    """检查 Pillow 库是否可用

    Raises:
        ImportError: 如果 Pillow 未安装
    """
    if not PIL_可用:
        raise ImportError("Pillow 未安装，请运行: pip install Pillow")


def 打开图像(路径: str) -> 图像对象:
    """打开图像文件

    Args:
        路径: 图像文件路径

    Returns:
        图像对象

    Raises:
        FileNotFoundError: 如果文件不存在
        ImportError: 如果 Pillow 未安装
    """
    检查PIL()
    try:
        pil_image = _Image.open(路径)
        pil_image.load()
        return 图像对象(pil_image)
    except FileNotFoundError:
        raise FileNotFoundError(f"图像文件不存在: {路径}")


def 新建图像(
    宽: int,
    高: int,
    颜色: Union[str, Tuple[int, int, int], Tuple[int, int, int, int]] = "白色",
    模式: str = "RGB"
) -> 图像对象:
    """创建新图像

    Args:
        宽: 图像宽度
        高: 图像高度
        颜色: 背景颜色，支持颜色名称或 RGB 元组
        模式: 图像模式，默认 "RGB"

    Returns:
        图像对象
    """
    检查PIL()
    pil_image = _Image.new(模式, (宽, 高), 颜色)
    return 图像对象(pil_image)


def 保存图像(图像: 图像对象, 路径: str, 格式: Optional[str] = None, 质量: int = 95):
    """保存图像到文件

    Args:
        图像: 图像对象
        路径: 保存路径
        格式: 图像格式（如 "JPEG", "PNG"），默认从文件扩展名推断
        质量: JPEG 保存质量（1-100），默认 95
    """
    kwargs = {}
    if 格式 and 格式.upper() == "JPEG":
        kwargs["quality"] = 质量

    pil_image = 图像.获取PIL对象()
    if 格式:
        pil_image.save(路径, 格式, **kwargs)
    else:
        pil_image.save(路径, **kwargs)


def 调整大小(图像: 图像对象, 宽: int, 高: int, 保持比例: bool = True) -> 图像对象:
    """调整图像大小

    Args:
        图像: 图像对象
        宽: 目标宽度（像素）
        高: 目标高度（像素）
        保持比例: 是否保持宽高比（默认 True）

    Returns:
        调整大小后的图像对象
    """
    检查PIL()
    pil_image = 图像.获取PIL对象()

    if 保持比例:
        pil_image.thumbnail((宽, 高), _Image.LANCZOS)
        return 图像对象(pil_image)
    else:
        resized = pil_image.resize((宽, 高), _Image.LANCZOS)
        return 图像对象(resized)


def 裁剪(图像: 图像对象, 左: int, 上: int, 右: int, 下: int) -> 图像对象:
    """裁剪图像

    Args:
        图像: 图像对象
        左: 左侧坐标
        上: 顶部坐标
        右: 右侧坐标
        下: 底部坐标

    Returns:
        裁剪后的图像对象
    """
    检查PIL()
    pil_image = 图像.获取PIL对象()
    cropped = pil_image.crop((左, 上, 右, 下))
    return 图像对象(cropped)


def 旋转(图像: 图像对象, 角度: float, 扩展: bool = True, 填充颜色: Optional[Tuple[int, ...]] = None) -> 图像对象:
    """旋转图像

    Args:
        图像: 图像对象
        角度: 旋转角度（度）
        扩展: 是否扩展画布以适应旋转后的图像
        填充颜色: 填充空白区域的颜色

    Returns:
        旋转后的图像对象
    """
    检查PIL()
    pil_image = 图像.获取PIL对象()
    rotated = pil_image.rotate(角度, expand=扩展, fillcolor=填充颜色)
    return 图像对象(rotated)


def 翻转(图像: 图像对象, 水平: bool = False, 垂直: bool = False) -> 图像对象:
    """翻转图像

    Args:
        图像: 图像对象
        水平: 是否水平翻转
        垂直: 是否垂直翻转

    Returns:
        翻转后的图像对象
    """
    检查PIL()
    pil_image = 图像.获取PIL对象()

    if 水平:
        pil_image = pil_image.transpose(_Image.FLIP_LEFT_RIGHT)
    if 垂直:
        pil_image = pil_image.transpose(_Image.FLIP_TOP_BOTTOM)

    return 图像对象(pil_image)


def 应用滤镜(图像: 图像对象, 滤镜类型: str = "模糊") -> 图像对象:
    """应用图像滤镜

    Args:
        图像: 图像对象
        滤镜类型: 滤镜类型，可选：
            - "模糊" (BLUR)
            - "轮廓" (CONTOUR)
            - "细节" (DETAIL)
            - "边缘增强" (EDGE_ENHANCE)
            - "浮雕" (EMBOSS)
            - "锐化" (SHARPEN)
            - "平滑" (SMOOTH)

    Returns:
        应用滤镜后的图像对象
    """
    检查PIL()
    滤镜映射 = {
        "模糊": _ImageFilter.BLUR,
        "轮廓": _ImageFilter.CONTOUR,
        "细节": _ImageFilter.DETAIL,
        "边缘增强": _ImageFilter.EDGE_ENHANCE,
        "浮雕": _ImageFilter.EMBOSS,
        "锐化": _ImageFilter.SHARPEN,
        "平滑": _ImageFilter.SMOOTH,
    }

    if 滤镜类型 not in 滤镜映射:
        raise ValueError(f"不支持的滤镜类型: {滤镜类型}，可选: {', '.join(滤镜映射.keys())}")

    pil_image = 图像.获取PIL对象()
    filtered = pil_image.filter(滤镜映射[滤镜类型])
    return 图像对象(filtered)


def 灰度化(图像: 图像对象) -> 图像对象:
    """将图像转换为灰度图

    Args:
        图像: 图像对象

    Returns:
        灰度图像对象
    """
    检查PIL()
    pil_image = 图像.获取PIL对象().convert("L")
    return 图像对象(pil_image)


def 调整亮度(图像: 图像对象, 因子: float = 1.0) -> 图像对象:
    """调整图像亮度

    Args:
        图像: 图像对象
        因子: 亮度因子，1.0 为原始亮度，< 1 变暗，> 1 变亮

    Returns:
        调整后的图像对象
    """
    检查PIL()
    pil_image = 图像.获取PIL对象()
    enhancer = _ImageEnhance.Brightness(pil_image)
    return 图像对象(enhancer.enhance(因子))


def 调整对比度(图像: 图像对象, 因子: float = 1.0) -> 图像对象:
    """调整图像对比度

    Args:
        图像: 图像对象
        因子: 对比度因子，1.0 为原始对比度

    Returns:
        调整后的图像对象
    """
    检查PIL()
    pil_image = 图像.获取PIL对象()
    enhancer = _ImageEnhance.Contrast(pil_image)
    return 图像对象(enhancer.enhance(因子))


def 调整饱和度(图像: 图像对象, 因子: float = 1.0) -> 图像对象:
    """调整图像饱和度

    Args:
        图像: 图像对象
        因子: 饱和度因子，1.0 为原始饱和度

    Returns:
        调整后的图像对象
    """
    检查PIL()
    pil_image = 图像.获取PIL对象()
    enhancer = _ImageEnhance.Color(pil_image)
    return 图像对象(enhancer.enhance(因子))


def 调整锐度(图像: 图像对象, 因子: float = 1.0) -> 图像对象:
    """调整图像锐度

    Args:
        图像: 图像对象
        因子: 锐度因子，1.0 为原始锐度

    Returns:
        调整后的图像对象
    """
    检查PIL()
    pil_image = 图像.获取PIL对象()
    enhancer = _ImageEnhance.Sharpness(pil_image)
    return 图像对象(enhancer.enhance(因子))


def 转换为RGB(图像: 图像对象) -> 图像对象:
    """将图像转换为 RGB 模式

    Args:
        图像: 图像对象

    Returns:
        RGB 模式图像对象
    """
    检查PIL()
    pil_image = 图像.获取PIL对象().convert("RGB")
    return 图像对象(pil_image)


def 获取图像信息(路径: str) -> dict:
    """获取图像文件信息

    Args:
        路径: 图像文件路径

    Returns:
        包含图像信息的字典（宽度、高度、模式、格式、文件大小等）
    """
    检查PIL()
    try:
        with _Image.open(路径) as img:
            import os
            文件大小 = os.path.getsize(路径)
            return {
                "宽度": img.width,
                "高度": img.height,
                "模式": img.mode,
                "格式": img.format,
                "文件大小": 文件大小,
                "文件大小(KB)": round(文件大小 / 1024, 2),
            }
    except Exception as e:
        return {"错误": str(e)}


def 创建缩略图(输入路径: str, 输出路径: str, 最大宽: int = 200, 最大高: int = 200):
    """创建图像缩略图并保存

    Args:
        输入路径: 源图像路径
        输出路径: 缩略图保存路径
        最大宽: 最大宽度
        最大高: 最大高度
    """
    图像 = 打开图像(输入路径)
    缩略图 = 调整大小(图像, 最大宽, 最大高, 保持比例=True)
    保存图像(缩略图, 输出路径)


def 绘制文本(
    图像: 图像对象,
    文本: str,
    位置: Tuple[int, int] = (0, 0),
    颜色: Tuple[int, int, int] = (0, 0, 0),
    字号: int = 20,
    字体路径: Optional[str] = None
) -> 图像对象:
    """在图像上绘制文本

    Args:
        图像: 图像对象
        文本: 要绘制的文本
        位置: 文本位置 (x, y)
        颜色: 文本颜色 RGB 元组
        字号: 字体大小
        字体路径: 字体文件路径（可选）

    Returns:
        绘制了文本的图像对象
    """
    检查PIL()
    pil_image = 图像.获取PIL对象().copy()
    draw = _ImageDraw.Draw(pil_image)

    if 字体路径:
        try:
            font = _ImageFont.truetype(字体路径, 字号)
        except Exception:
            font = _ImageFont.load_default()
    else:
        font = _ImageFont.load_default()

    draw.text(位置, 文本, fill=颜色, font=font)
    return 图像对象(pil_image)


def 合并图像(图像1: 图像对象, 图像2: 图像对象, 位置: Tuple[int, int] = (0, 0)) -> 图像对象:
    """将图像2粘贴到图像1上

    Args:
        图像1: 底图图像对象
        图像2: 要粘贴的图像对象
        位置: 粘贴位置 (x, y)

    Returns:
        合并后的图像对象
    """
    检查PIL()
    pil1 = 图像1.获取PIL对象().copy()
    pil2 = 图像2.获取PIL对象()
    pil1.paste(pil2, 位置)
    return 图像对象(pil1)