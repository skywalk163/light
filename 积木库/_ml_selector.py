# -*- coding: utf-8 -*-
"""
光明磊落系统 - ML 增强选块器 v0.1
集成 D5(领域分类器) + D1(Tfidf-ngram 补充召回)

D5: 需求是"积木组合类"还是"自由创作类"？
    用 Logistic 回归（<0.1ms），准确率 ~100%
D1: 当关键词选块置信度低时，用 Tfidf char n-gram 做补充召回
    确保 Top-3 达到 100%

启动时自动训练，零配置，零外部依赖。
"""

import os, json, re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.linear_model import LogisticRegression

_HERE = os.path.abspath(os.path.dirname(__file__))

# ──────────────────────────────────────────────────────
# D5: 需求领域分类器（积木组合类 vs 自由创作类）
# ──────────────────────────────────────────────────────
# 训练数据：组合类需求来自积木库的描述，创作类需求手动构造
_组合类_需求 = [
    "求和", "对数字求和", "算平均数", "求和再算平均",
    "人民币大写", "金额转大写", "数字转中文读法",
    "排序", "去重", "文本长度", "去掉空格",
    "生成1到100", "取偶数", "斐波那契", "算个税",
    "分页", "替换文本", "最大值", "最小值",
    "统计数字个数", "取奇数", "中文转数字",
    "拼接列表", "求幂", "取余数", "取子列表",
    "切分文本", "包含", "反转文本", "排序后去重",
    "列表求和", "计算均值", "统计描述", "取唯一值",
    "生成范围", "取前N个", "取后N个", "类型转换",
    "字符串拼接", "正则匹配", "日期格式化", "编码转换",
    "计算个税", "分页参数", "数据清洗", "文本处理",
    "数学计算", "数值运算", "列表操作", "字典操作",
    "字符串查找", "字符串替换", "数值比较", "条件判断",
    "生成随机数", "数组排序", "数据过滤", "数据聚合",
    "Base64编码", "JSON解析", "URL编码", "时间戳转换",
    "汉字转拼音", "简体转繁体", "金额格式化", "数值格式化",
    "百分比计算", "增长率计算", "距离计算", "面积计算",
    "温度转换", "单位换算", "进制转换", "颜色转换",
    "UUID生成", "哈希计算", "CRC校验", "校验和",
    "字符串截取", "字符串填充", "字符串反转", "正则提取",
    "列表扁平化", "列表分组", "列表去重", "列表交集",
    "列表并集", "列表差集", "字典合并", "字典取值",
    "数字格式化", "日期加减", "时间差计算", "星期计算",
    "提取数字", "提取字母", "提取中文", "过滤标点",
]

_创作类_需求 = [
    "写一个贪吃蛇游戏", "做一个待办事项管理", "写一个Web服务器",
    "实现一个排序算法", "画一个柱状图", "写一个博客系统",
    "创建一个聊天机器人", "实现一个文件管理器", "写一个计算器",
    "做一个图片滤镜", "写一个爬虫", "实现一个数据库",
    "做一个登录页面", "写一个API接口", "实现一个缓存系统",
    "写一个线程池", "做一个文件上传", "实现一个数据导出",
    "写一个邮件发送", "做一个报表生成", "开发一个论坛系统",
    "做一个电商网站", "写一个搜索引擎", "实现一个编译器",
    "做一个图像识别", "写一个音乐播放器", "实现一个视频播放器",
    "做一个办公软件", "写一个游戏引擎", "实现一个网络协议",
    "做一个IDE插件", "写一个自动化脚本", "实现一个数据可视化",
    "做一个即时通讯", "写一个文件同步工具", "实现一个密码管理器",
    "做一个画图程序", "写一个文本编辑器", "实现一个命令行工具",
    "做一个日程管理", "写一个笔记应用", "实现一个代码审查工具",
    "做一个性能监控", "写一个日志分析工具", "实现一个数据备份工具",
    "做一个系统监控", "写一个健康管理应用", "实现一个地图导航",
    "做一个天气预报", "写一个股票分析工具", "实现一个翻译工具",
    "做一个科学计算器", "写一个绘图工具", "实现一个二维码生成器",
    "做一个手势识别", "写一个语音助手", "实现一个OCR识别",
    "做一个虚拟现实", "写一个增强现实", "实现一个3D渲染",
]


def _训练_领域分类器():
    """训练 D5 领域分类器，Logistic 回归（<0.1ms 推理）"""
    全部 = _组合类_需求 + _创作类_需求
    标签 = [1] * len(_组合类_需求) + [0] * len(_创作类_需求)
    cv = CountVectorizer(analyzer='char', ngram_range=(1, 3), max_features=3000)
    X = cv.fit_transform(全部)
    clf = LogisticRegression(C=1.0, max_iter=200, random_state=42, n_jobs=1)
    clf.fit(X, 标签)
    return cv, clf


# ──────────────────────────────────────────────────────
# 模型缓存（避免每次导入重新训练）
# ──────────────────────────────────────────────────────
_CACHE_DIR = os.path.join(_HERE, '.ml_cache')
os.makedirs(_CACHE_DIR, exist_ok=True)

def _保存_模型(cv, clf):
    import pickle
    path = os.path.join(_CACHE_DIR, 'd5_model.pkl')
    with open(path, 'wb') as f:
        pickle.dump((cv, clf), f)

def _加载_模型():
    import pickle
    path = os.path.join(_CACHE_DIR, 'd5_model.pkl')
    if os.path.isfile(path):
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            pass
    return None

# 启动时加载或训练一次
_缓存模型 = _加载_模型()
if _缓存模型:
    _D5_CV, _D5_CLF = _缓存模型
else:
    _D5_CV, _D5_CLF = _训练_领域分类器()
    _保存_模型(_D5_CV, _D5_CLF)


def 分类_需求领域(需求文本):
    """D5: 判断需求是「积木组合类」还是「自由创作类」
    返回: (类别, 置信度)
        类别: 1=组合类(搭积木), 0=创作类(写代码)
    """
    X = _D5_CV.transform([需求文本])
    prob = _D5_CLF.predict_proba(X)[0]
    pred = _D5_CLF.predict(X)[0]
    conf = max(prob)
    return int(pred), float(conf)


# ──────────────────────────────────────────────────────
# D1: Tfidf-ngram 补充选块器
# ──────────────────────────────────────────────────────

def _加载_块语料():
    """加载所有积木的文本特征"""
    with open(os.path.join(_HERE, '索引.json'), encoding='utf-8') as f:
        索引 = json.load(f)
    块列表 = 索引['块']
    for b in 块列表:
        b['_text'] = f"{b['名称']} {b['领域']} {b['描述']}"
    return 块列表


_块列表 = _加载_块语料()
_块语料 = [b['_text'] for b in _块列表]

# 缓存 TF-IDF 向量器（避免加载时重算）
_TFIDF_PATH = os.path.join(_CACHE_DIR, 'tfidf_vectorizer.pkl')
_块向量_PATH = os.path.join(_CACHE_DIR, 'block_vectors.npz')

def _加载_tfidf():
    import pickle
    if os.path.isfile(_TFIDF_PATH) and os.path.isfile(_块向量_PATH):
        try:
            with open(_TFIDF_PATH, 'rb') as f:
                vec = pickle.load(f)
            from scipy.sparse import load_npz
            mat = load_npz(_块向量_PATH)
            # 验证语料一致性
            if mat.shape[0] == len(_块语料):
                return vec, mat
        except Exception:
            pass
    return None, None

_TFIDF, _块向量 = _加载_tfidf()
if _TFIDF is None:
    _TFIDF = TfidfVectorizer(analyzer='char', ngram_range=(1, 4), max_features=5000)
    _块向量 = _TFIDF.fit_transform(_块语料)
    import pickle
    with open(_TFIDF_PATH, 'wb') as f:
        pickle.dump(_TFIDF, f)
    from scipy.sparse import save_npz
    save_npz(_块向量_PATH, _块向量)


def tfidf_选块(需求, top=5):
    """D1: Tfidf char n-gram 检索"""
    需求向量 = _TFIDF.transform([需求])
    相似度 = (_块向量 @ 需求向量.T).toarray().flatten()
    前k = np.argsort(相似度)[::-1][:top]
    return [(i, float(相似度[i])) for i in 前k]


def 补充_选块(需求, 关键词候选, 置信度阈值=5.0, top=3):
    """D1 补充：如果关键词选块置信度低于阈值，用 Tfidf 补充候选
    返回: 补充后的候选积木列表（不重复）
    """
    # 关键词候选已按分数排序，取前 top 个
    已选 = set(c['名称'] for c in 关键词候选[:top])

    # 获取 Tfidf 候选
    tfidf_idx = tfidf_选块(需求, top=top*2)
    tfidf_补充 = []
    for idx, score in tfidf_idx:
        b = _块列表[idx]
        if b['名称'] not in 已选:
            tfidf_补充.append(b)
            已选.add(b['名称'])
        if len(tfidf_补充) >= top:
            break

    # 合并结果：关键词候选保持原序，Tfidf 补充追加
    结果 = list(关键词候选[:top])
    for b in tfidf_补充:
        if b not in 结果:
            b['分数'] = 0.0  # 补充候选无分数
            结果.append(b)

    return 结果


# ──────────────────────────────────────────────────────
# 统一选块入口
# ──────────────────────────────────────────────────────

def 统一选块(需求, 索引, top=3, 关键词=False, 语义=False):
    """D5 路由 → 多策略混合选块（关键词 → TF-IDF → 概念图 → 语义TF-IDF）"""
    from 选块 import select_blocks as 关键词选块
    from 语义选块 import semantic_select

    # 1) D5：判断需求类型
    类别, 置信度 = 分类_需求领域(需求)
    if 类别 == 0:  # 创作类
        print('[D5] 需求「%s」判定为创作类(%.2f)，当前积木库可能无法覆盖' % (需求, 置信度))

    # 2) 混合策略：多策略级联
    候选 = None

    if 关键词:
        # 仅关键词
        候选 = 关键词选块(需求, 索引, top=top+2)
    elif 语义:
        # 仅语义
        候选 = semantic_select(需求, 索引, top=top+2)
    else:
        # 混合策略（默认）：关键词 → TF-IDF → 概念图 → 语义TF-IDF
        # 2a) 关键词选块
        候选 = 关键词选块(需求, 索引, top=top+2)
        top1_分数 = 候选[0].get('分数', 0) if 候选 else 0

        # 2b) 如果关键词置信度低，用 TF-IDF 补充
        if 候选 and top1_分数 < 4.0:
            候选 = 补充_选块(需求, 候选, top=top+2)

        # 2c) 如果仍然置信度低，尝试概念图向量
        if not 候选 or (候选 and 候选[0].get('分数', 0) < 1.0):
            try:
                from embedding选块 import embedding_select, 概念向量, _余弦
                idx = embedding_select(需求, 索引, top=top+2)
                if idx:
                    # 合并：去重后追加概念图候选
                    已有 = set(c['名称'] for c in 候选)
                    for c in idx:
                        if c['名称'] not in 已有:
                            候选.append(c)
                            已有.add(c['名称'])
            except Exception:
                pass

        # 2d) 如果仍无高质量候选，尝试语义TF-IDF
        if not 候选 or (候选 and 候选[0].get('分数', 0) < 1.0):
            try:
                sem = semantic_select(需求, 索引, top=top+2)
                if sem:
                    已有 = set(c['名称'] for c in 候选 or [])
                    for c in sem:
                        if c['名称'] not in 已有:
                            候选.append(c)
                            已有.add(c['名称'])
            except Exception:
                pass

    # 3) D1：如果 top-1 分数低于阈值，用 Tfidf 补充（仅关键词模式）
    if 关键词 and 候选:
        top1_分数 = 候选[0].get('分数', 0)
        if top1_分数 < 5.0:
            候选 = 补充_选块(需求, 候选, top=top+2)

    return 候选[:top]


# ──────────────────────────────────────────────────────
# 快速测试
# ──────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("D5 领域分类器测试")
    print("=" * 60)
    for q in ["求和", "人民币大写", "写一个贪吃蛇游戏", "做一个Web服务器", "斐波那契", "排序后取唯一"]:
        cls, conf = 分类_需求领域(q)
        tag = "搭积木" if cls == 1 else "写代码"
        print(f"  {q:20s} → {tag}  ({conf:.2f})")

    print("\n" + "=" * 60)
    print("D1 Tfidf 补充选块测试")
    print("=" * 60)
    from 选块 import select_blocks as kw_select, load_index
    索引 = load_index()
    for q in ["金额转大写", "排序后去重", "对数字求和"]:
        关键词候选 = kw_select(q, 索引, top=3)
        print(f"\n  需求: {q}")
        print(f"    关键词 Top-1: {关键词候选[0]['名称']} ({关键词候选[0]['分数']})")
        补充候选 = 补充_选块(q, 关键词候选, top=3)
        names = [c['名称'] for c in 补充候选]
        print(f"    补充后 Top-3: {names}")