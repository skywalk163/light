# -*- coding: utf-8 -*-
"""计划缓存 v0.21：需求指纹 → 装配方案复用。

零 token 链路里最贵的三步是选块、校验、接线。同一个需求第二次进来时，
这三步的结果必然相同——除非库变了。那就别再算一遍。

失效模型（宁可多算一次，不可用错方案）
--------------------------------------
缓存键 = 需求指纹 + 库指纹 + 策略指纹，任一变化即未命中：

  需求指纹  规范化后的需求文本（去空白/去标点/统一全半角）
  库指纹    全部块的 名称|路径|导出名|输入类型|输出类型 的摘要
            —— 兜底生成新块、改契约、改名都会让它变，旧方案自动作废
  策略指纹  选块策略 + top + 阈值 + 链式开关，参数不同不共用

另存输入类型：方案里的接线是按类型规划出来的，输入类型变了就必须重算，
所以命中还要求 输入类型 一致（值可以不同——值只是替换进 共享，不影响接线）。

缓存内容只存「步骤」（含接线好的参数），不存生成的段言源码：
源码由 粘合.py 从步骤和当前库文件实时合成，块文件被改过也能自动跟上。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

缓存路径 = os.path.join(_HERE, '.计划缓存.json')
版本 = 'v0.21'
上限 = int(os.environ.get('DUAN_PLAN_CACHE_MAX', '500'))


# ---------------------------------------------------------------------------
# 指纹
# ---------------------------------------------------------------------------
_标点 = re.compile(r'[\s，。！？、；：,.!?;:\'"“”‘’（）()\[\]【】]+')


def 规范需求(需求):
    """同一个意思的不同排版应该命中同一条缓存。"""
    s = (需求 or '').strip().lower()
    s = _标点.sub('', s)
    # 全角数字/字母归一化，避免 "IP" 与 "ＩＰ" 分裂成两条
    s = ''.join(chr(ord(c) - 0xFEE0) if '\uff01' <= c <= '\uff5e' else c for c in s)
    return s


def _摘要(text):
    return hashlib.sha1(text.encode('utf-8')).hexdigest()[:16]


def 库指纹(索引):
    块 = 索引.get('块') or []
    行 = []
    for b in sorted(块, key=lambda x: x.get('名称') or ''):
        输入 = ','.join(i.get('类型', '?') for i in (b.get('输入') or []))
        行.append('%s|%s|%s|%s|%s|%s' % (
            b.get('名称'), b.get('路径'), b.get('导出名'), 输入,
            (b.get('输出') or {}).get('类型', '?'),
            '1' if b.get('选块可见', True) else '0'))
    return _摘要('\n'.join(行))


def 策略指纹(策略, top, 阈值, 链式):
    return _摘要('%s|%s|%s|%s' % (策略, top, 阈值, bool(链式)))


def 键(需求, 索引, 策略, top, 阈值, 链式):
    return _摘要('%s##%s##%s' % (规范需求(需求), 库指纹(索引),
                                策略指纹(策略, top, 阈值, 链式)))


# ---------------------------------------------------------------------------
# 存储
# ---------------------------------------------------------------------------
def _空库():
    return {'版本': 版本, '库指纹': None, '条目': {}}


def 载入(path=None):
    p = path or 缓存路径
    if not os.path.exists(p):
        return _空库()
    try:
        with open(p, encoding='utf-8') as f:
            d = json.load(f)
        if d.get('版本') != 版本:
            return _空库()
        return d
    except Exception:
        return _空库()


def 保存(d, path=None):
    p = path or 缓存路径
    条 = d.get('条目') or {}
    if len(条) > 上限:
        # 超限按最后命中时间淘汰，保留活跃的一半
        序 = sorted(条.items(), key=lambda kv: kv[1].get('最后命中', 0), reverse=True)
        d['条目'] = dict(序[:上限 // 2])
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def 读(需求, 索引, 策略='混合', top=3, 阈值=None, 链式=False,
      输入类型=None, path=None):
    """命中返回 {'步骤','候选','输入类型',...}，否则 None。"""
    d = 载入(path)
    指纹 = 库指纹(索引)
    if d.get('库指纹') and d['库指纹'] != 指纹:
        # 库已变（新块入库/契约变更）→ 整体作废，绝不拿旧方案硬套
        return None
    k = 键(需求, 索引, 策略, top, 阈值, 链式)
    e = (d.get('条目') or {}).get(k)
    if not e:
        return None
    if 输入类型 is not None and e.get('输入类型') != 输入类型:
        # 接线是按类型规划的，类型不同必须重算
        return None
    e['命中次数'] = e.get('命中次数', 0) + 1
    e['最后命中'] = int(time.time())
    d['库指纹'] = 指纹
    保存(d, path)
    return e


def 写(需求, 索引, 步骤, 候选, 策略='混合', top=3, 阈值=None, 链式=False,
      输入类型=None, 兜底=False, path=None):
    d = 载入(path)
    指纹 = 库指纹(索引)
    if d.get('库指纹') and d['库指纹'] != 指纹:
        d = _空库()          # 库变了，旧条目全清
    d['库指纹'] = 指纹
    d.setdefault('条目', {})[键(需求, 索引, 策略, top, 阈值, 链式)] = {
        '需求': 需求, '步骤': 步骤,
        '候选': [c.get('名称') for c in (候选 or [])],
        '输入类型': 输入类型, '兜底': bool(兜底),
        '写入时间': int(time.time()), '命中次数': 0, '最后命中': 0,
    }
    保存(d, path)


def 清空(path=None):
    p = path or 缓存路径
    if os.path.exists(p):
        os.remove(p)
    return True


def 统计(path=None):
    d = 载入(path)
    条 = d.get('条目') or {}
    return {
        '版本': d.get('版本'), '库指纹': d.get('库指纹'), '条目数': len(条),
        '累计命中': sum(e.get('命中次数', 0) for e in 条.values()),
        '路径': path or 缓存路径,
    }


def _cli(argv=None):
    p = argparse.ArgumentParser(description='段言积木计划缓存 v0.21')
    p.add_argument('动作', choices=['统计', '清空', '列出'])
    args = p.parse_args(argv)
    if args.动作 == '清空':
        清空()
        print('已清空计划缓存')
        return 0
    if args.动作 == '列出':
        d = 载入()
        for k, e in (d.get('条目') or {}).items():
            print('%s  命中%-3d 步骤=%s  %s'
                  % (k, e.get('命中次数', 0),
                     '+'.join(s.get('块', '?') for s in e.get('步骤') or []),
                     e.get('需求')))
        return 0
    print(json.dumps(统计(), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(_cli())
