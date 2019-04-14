# -*- coding: utf-8 -*-
import sys
import os

sys.path.append(os.path.dirname(__file__))
from save_and_load import load

# 必须的slot
necessaryTag = ['品牌', '价格', '内存']
# NLU的label和中文tag之间的转换
labelToTag = {'brand': '品牌',
              'price': '价格',
              'memory': '内存',
              'disk': '硬盘大小',
              'cpu': '处理器',
              'gpu': '显卡',
              'experience': '其他',
              'function': '配置要求'}
# 针对每一个slot的发问
ask_slot = {'品牌': ['请问你喜欢什么牌子呢？', '请问你需要什么牌子的呢?'],
            '价格': ['请问你预算多少？', '请问什么价位的合适呢?', '请问预期的价位是多少呢?'],
            '内存': ['请问运行内存需要多大呢？', '请问对运行内存有什么需求吗?']}
# informable slot的回复
listInfo = {'品牌': ['畅销的品牌有惠普,戴尔,华硕呢', '比较畅销的牌子有惠普,戴尔,华硕等'],
            '价格': ['一般常见的价位有3000以下,3000-7000或者以上的呢'],
            '内存': ['常见的内存规格分为4G，6G，8G,16G等等']}

# 将中文的slot转成数据库的字段
nameToColumn = {'品牌': 'brand', '价格': 'price', '内存': 'memory', '硬盘': 'disk',
                '处理器': 'cpu', '显卡': 'gpu', '型号': 'name', '其他': 'experience', '配置要求': 'function'}
# 可以进行调整的字段
adjustableSlot = {'价格': 'price', '内存': 'memory', '硬盘': 'disk'}
# 表示无所谓的词语
whatever_word = ['随意', '随便', '都行', '可以', '没关系']
# 确认的回复
yes_word = ['好的', '确认', '好', '嗯', '恩', '确定', '是', '是的', '可以', '行']
# 否定的回复
no_word = ['不要', '不是', '否定', '否认', '不对', '不可以', '不行', '别', '否', '不']
# 体验属性
experienceAttr = ['信号', '做工', '分辨率', '处理器', '外观', '字体', '反应', '效果', '性价比', '性能', '手感', '拍照', '摄像', '机身', '游戏', '电池',
                  '界面',
                  '网络', '系统', '强悍', '硬件', '续航', '网速', '音质', '流畅', '视频', '软件', '重量', '音质']
# 手机cpu等级
path = os.path.dirname(__file__)
level = load(os.path.join(path, 'cpu.data'))
cpu_level = {}
for i, lv in enumerate(level):
    for cpu in lv:
        cpu_level[cpu] = i

# 游戏列表
game = ['王者荣耀', '王者', '吃鸡', '全军出击', '刺激战场', '我的世界', '明日之后', 'fgo', '炉石', '游戏']
gameRequirement = {'cpu': 'i5', 'memory': 2}
