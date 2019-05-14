# -*- coding: utf-8 -*-
import sys
import os

sys.path.append(os.path.dirname(__file__))
from save_and_load import load, read_list, read

# 必须的slot
necessaryTag = ['brand', 'price']
# NLU的label和中文tag之间的转换
labelToTag = {'brand': 'brand',
              'price': 'price',
              'memory_size': 'disk',
              'pixel': 'pixelb',
              'screen_size': 'size',
              'experience': 'experience',
              'function': 'function'}
tagToLabel = {labelToTag[k]: k for k in labelToTag}
# 针对每一个slot的发问
ask_slot = {'brand': ['请问你喜欢什么牌子呢？', '请问你需要什么牌子的呢?'],
            'price': ['请问你预算多少？', '请问什么价位的合适呢?', '请问预期的价位是多少呢?'],
            'memory': ['请问运行内存需要多大呢？', '请问对运行内存有什么需求吗?']}
# informable slot的回复
listInfo = {'brand': ['畅销的品牌有华为，小米，苹果呢', '比较受欢迎的牌子有苹果，小米，华为等'],
            'price': ['一般常见的价位有1000-2000,2000-3000或者3000以上的呢'],
            'memory': ['常见的内存规格分为4G，6G，8G']}

fail_slot = {
    'brand': ['抱歉，没能正确识别品牌哦,您可以直接回复品牌名字来指定品牌'],
    'price': ['不好意思啦～小C没能识别出有效的价格'],
    'memory': ['真是非常抱歉，小C没能顺利识别出内存大小呢'],
    'more': ['不好意思哟，这个小C暂时理解不了哦~']
}

# 可以进行调整的字段
adjustableSlot = ['price', 'pixelb', 'disk', 'size', 'memory']
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
# cpu　gpu等级
path = os.path.dirname(__file__)
cpu_level = load(path + '/data/phone_cpu_level.data')

brand_list = '''
OPPO vivo 华为 荣耀 三星 苹果 一加 努比亚 魅族 联想 金立 中兴 Moto 锤子科技 360 国美手机 小米 夏普 华硕 美图 诺基亚 HTC 8848
SUGAR 黑莓 海信 AGM 黑鲨 索尼 谷歌 LG 酷派 VERTU 中国移动 飞利浦 联想 ZUK 小辣椒 TCL 天语 YotaPhone 长虹 MANNROG 微软
格力 朵唯 纽曼 雷蛇 大神 传音 ivvi 海尔 酷比 索野 康佳 誉品 乐目 邦华 COMIO 青橙 创星 卡布奇诺 独影天幕 詹姆士 21克 汇威 百合
波导 守护宝 ioutdoor 保千里 私人医生 阿尔卡特 朗界 E人E本 红鸟 sonim PPTV 尼凯恩 innos 云狐 新石器 柯达 会播 富可视 VEB
铂爵 青想 米蓝 传奇 途为 imoo 神舟 BDV TP-LINK 易百年 小格雷 首云 克里特 先锋 图灵 小宇宙 泛泰 大唐 电信 雅马亚虎 VANO VAIO
松下 东芝 惠普 全普 奥克斯 欧恩
'''
brand_list = brand_list.split()
brand_list = [brand.strip() for brand in brand_list]
brand_list = [brand for brand in brand_list if brand]


def load_function(file_path):
    file = read_list(file_path)
    function_name = ['cpu', 'memory']
    res = {}
    i = 0
    while i < len(file):
        name = file[i]
        temp = {}
        i += 1
        while i < len(file) and file[i] != '':
            line = file[i].split(':')
            for word in function_name:
                if word == line[0]:
                    temp[word] = line[1]
            i += 1

        res[name] = temp
        while i < len(file) and file[i] == '':
            i += 1
    return res


def load_func_synonyms(file_path):
    file = read_list(file_path)
    res = {}
    for line in file:
        line = line.split()
        std_word = line[0]
        for word in line:
            res[word] = std_word

    return res


def load_exp_synonyms(file_path):
    file = read_list(file_path)
    words = []
    for line in file:
        line = line.split()
        words.extend(line)
    return words


function_attr = load_function(path + '/data/phone_func_attr.txt')
func_synonyms = load_func_synonyms(path + '/data/phone_func_synonyms.txt')

good_words = read_list(path + '/data/good_words_phone.txt')
bad_words = read_list(path + '/data/bad_words_phone.txt')

exp_synonyms = load_exp_synonyms(path + '/data/phone_aspect_words.txt')
