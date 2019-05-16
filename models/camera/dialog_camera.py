import numpy as np
import sys
import os

sys.path.append(os.path.dirname(__file__))
from save_and_load import *
import json
import re
from static_data_camera import necessary_tag, label_to_tag, ask_slot, list_info, adjustable_slot, \
    whatever_word, yes_word, no_word, func_synonyms, exp_synonyms, function_attr, brand_list, tagToLabel, fail_slot, \
    preset
from collections import defaultdict
from search_camera import search_camera


def check_sentiment_polarity(s):
    '''
    要贵一点的
    不要太贵了
    差不多就行
    中等的吧
    :param s: input sentence
    :return: hit_word,level(up/mid/down/none)
    '''
    mid_word = ['中等', '差不多', '一般', '正常', '普通']
    up_word = ['贵', '高', '大', '好']
    down_word = ['便宜', '小', '低配', '糟糕', '少', '差']
    no_word = ['不要', '不是', '否定', '否认', '不对', '不可以', '不行', '别', '否', '不', '没']
    tooWord = ['太', '有点', '过于', '不够']

    for word in mid_word:
        if word in s:
            return word, 'mid'

    for word in down_word:
        if word in s:
            for neg in no_word:
                if neg in s:
                    return word, 'mid'
            return word, 'down'

    for word in up_word:
        if word in s:
            for neg in no_word:
                if neg in s:
                    return word, 'mid'
            return word, 'up'

    return '', 'none'


def split_all(s, target=',.?，。？！!'):
    '''
    split a sentence by target
    :param s: input sentence
    :param target: target string
    :return:a list of string
    '''
    sent = []
    line = ''
    for word in s:
        if word not in target:
            line += word
        else:
            sent.append(line)
            line = ''
    if line != '':
        sent.append(line)
    return sent


def trans_number(num):
    '''
    transfer chinese number to 1-9
    :param num:number string
    :return:transfered number string
    '''
    digit = [str(i) for i in range(1, 10)]
    digit_char = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
    if num in digit:
        return digit.index(num) + 1
    if num in digit_char:
        return digit_char.index(num) + 1
    return 'unkown'


def trans_price(s):
    valide_char = '1234567890一二三四五六七八九十百千万'
    for char in s:
        if char not in valide_char:
            return -1
    if re.match(r'^\d+$', s):
        return int(s)
    digit_char = ['一', '二', '三', '四', '五', '六', '七', '八', '九']
    for i, digit in enumerate(digit_char):
        s = s.replace(digit, str(i + 1))
    s = s.replace('两', str(2))
    match = re.match(r'^[\d+\.*\d*万]*[\d+千]*[\d+百]*[\d+十]*[\d+]*$', s)
    if match:
        base = {'万': 10000, '千': 1000, '百': 100, '十': 10}
        total = 0
        cache = ''
        for digit in s:
            if digit not in base:
                cache += digit
            else:
                total += float(cache) * base[digit]
                cache = ''
        if cache != '':
            total += float(cache)
        return total
    return -1


def get_random_sentence(sentence_list):
    '''
    select a sentence randomly
    :param sentence_list:
    :return: selected sentence
    '''
    num = np.random.randint(len(sentence_list))
    return sentence_list[num]


def get_change_intent(domain, sentence):
    '''
    check if the input contains a change intention
    :param domain:current domain
    :param sentence:user input
    :return:(target,positive) a tuple contains a change target and a value to measure whether to change
    '''
    changeable_slot = ['价格', '像素']
    target_to_label = {'价格': 'price', '像素': 'pixel'}
    pos_word = ['贵', '高', '大', '好']
    neg_word = ['便宜', '小', '低', '糟糕', '少', '差']
    positive_count = 0
    target = ''
    # 匹配描述目标
    for word in changeable_slot:
        if word in sentence:
            target = word
            break
    # 补充目标
    if target == '':
        if any(w in sentence for w in ['贵', '便宜']):
            target = '价格'
        elif any(w in sentence for w in ['高', '低']):
            target = '价格?'

    if target != '':
        target = target_to_label[target]
    too_word = ['太', '有点', '过于', '不够']
    for word in pos_word:
        if word in sentence:
            if all(w + word not in sentence for w in too_word):
                positive_count += 1
            else:
                positive_count -= 1
    for word in neg_word:
        if word in sentence:
            if all(w + word not in sentence for w in too_word):
                positive_count -= 1
            else:
                positive_count += 1

    positive = 0
    if positive_count > 0:
        positive = 1
    elif positive_count < 0:
        positive = -1

    return (target, positive)


class Camera_Dialogue():
    def __init__(self, nlu):
        self.slot_value = {}
        self.state = "init"
        self.last_state = 'init'
        self.ask_slot = ""
        self.expected = ''
        self.result_list = None
        self.choice = {}
        self.morewhat = None
        self.show_result = False
        self.finish = False
        self.nlu = nlu
        self.asked = []
        self.asked_more = False
        self.extract_none = False
        self.prefix = ''
        self.preset = []
        self.result_offset = 0
        self.current_commit_sv = []

    def save(self):
        '''
        save current model to a json file
        :return: json string
        '''
        model = {
            'slot_value': self.slot_value,
            'state': self.state,
            'ask_slot': self.ask_slot,
            'expected': self.expected,
            'morewhat': self.morewhat,
            'asked': self.asked,
            'asked_more': self.asked_more,
            'extract_none': self.extract_none,
            'prefix': self.prefix,
            'preset': self.preset,
            'offset': self.result_offset,
            'current_commit': self.current_commit_sv
        }
        return json.dumps(model)

    def load(self, model):
        '''
        load model from json string
        :param model:json string
        :return:None
        '''
        m = json.loads(model)
        self.slot_value = m['slot_value']
        self.state = m['state']
        self.ask_slot = m['ask_slot']
        self.expected = m['expected']
        self.morewhat = m['morewhat']
        self.asked = m['asked']
        self.asked_more = m['asked_more']
        self.extract_none = m['extract_none']
        self.prefix = m['prefix']
        self.preset = m['preset']
        self.result_offset = m['offset']
        self.current_commit_sv = m['current_commit']
        if self.state == 'result':
            res = self.search(self.slot_value)
            self.result_list = res

    def reset(self):
        '''
        reset a dialog state
        :return:None
        '''
        self.slot_value = {}
        self.state = "init"
        self.last_state = 'init'
        self.ask_slot = ""
        self.expected = ''
        self.result_list = None
        self.choice = {}
        self.morewhat = None
        self.show_result = False
        self.finish = False
        self.asked = []
        self.asked_more = False
        self.extract_none = False
        self.preset = []
        self.prefix = ''
        self.result_offset = 0
        self.current_commit_sv = []

    def change_state(self, state, last_state=None):
        '''
        change dialog state
        :param state:next state
        :param last_state:current state
        :return:None
        '''
        print("state change to:" + state)
        if last_state is None:
            self.last_state = self.state
        else:
            self.last_state = last_state
        if state in ['result', 'confirm_choice']:
            self.show_result = True
        else:
            self.show_result = False
        self.state = state

    def go_last_state(self):
        '''
        go back to last dialog state
        :return:None
        '''
        print("state go back to:" + self.last_state)
        self.state = self.last_state

    def user(self, sentence):
        '''
        deal with user input, routing input to different state
        :param sentence:user input
        :return:None
        '''
        sentence = sentence.strip()
        if self.state == 'init':
            self.init(sentence)
        elif self.state == 'ask':
            self.ask(sentence)
        elif self.state == 'result':
            self.result(sentence)
        elif self.state == 'confirm_choice':
            self.confirm_choice(sentence)
        elif self.state == 'adjust_confirm':
            self.adjust_confirm(sentence)
        elif self.state == 'ask_more':
            self.ask_more(sentence)

    def list_slot(self, sentence):
        '''
        list informable slot,empty for input
        :param sentence:sentence
        :return:None
        '''
        pass

    def do_adjust(self, morewhat):
        '''
        excute an adjustion
        :param morewhat:(target,positive) : ('价格',1) ,positive>0 means adjust higher value
        :return:None
        '''
        print("do adjust:", morewhat)
        result = self.get_result()
        print(result)
        if morewhat[0] in adjustable_slot:
            upper = max([item[morewhat[0]] for item in result if morewhat[0] in item])
            lower = min([item[morewhat[0]] for item in result if morewhat[0] in item])
            if morewhat[1] > 0:
                self.slot_value[morewhat[0]] = [(upper, '>=')]
            else:
                self.slot_value[morewhat[0]] = [(lower, '<=')]
        self.change_state('result')

    def adjust_confirm(self, sentence):
        '''
        confirm adjustion for uncertained input
        :param sentence: user input
        :return: None
        '''
        targetWord = ['价格', '像素']
        target_to_label = {'价格': 'price', '像素': 'pixel'}
        for word in targetWord:
            if word in sentence:
                self.morewhat = (target_to_label[word], self.morewhat[1])
                self.do_adjust(self.morewhat)

        intent = self.nlu.intention_predict(sentence)
        if intent == 'answer_yes':
            self.morewhat = (self.expected, self.morewhat[1])
            self.change_state('do_adjust')
            self.do_adjust(self.morewhat)
        elif intent == 'answer_slot':
            tag = self.extract(sentence)
            to_add = self.fill_message(tag)
            if len(to_add) > 0:
                self.write(to_add)
                self.change_state('result')

    def confirm_choice(self, sentence):
        '''
        confirm the result the user chosed
        :param sentence: user input
        :return:None
        '''
        intent = self.nlu.intention_predict(sentence)
        if intent == 'answer_yes':
            self.change_state('done')
            self.finish = True
            return
        elif intent == 'answer_no':
            self.change_state('result')
            return
        for word in no_word:
            if word in sentence:
                self.change_state('result')
                return
        for word in yes_word:
            if word in sentence:
                self.change_state('done')
                self.finish = True
                return

    def result(self, sentence):
        '''
        check user's reponse to the result
        :param sentence:user input
        :return:None
        '''
        if '查看更多' in sentence:
            self.result_offset += 5
            return
        if self.check_choice(sentence):
            self.change_state('done')
            self.finish = True
            return
        tag = self.extract(sentence)
        if len(tag) > 0:
            tag = self.nlu.confirm_slot(tag, sentence)
            to_add = self.fill_message(tag)
            self.write(to_add)
            self.result_offset = 0

        morewhat = get_change_intent('camera', sentence)
        if morewhat[1] != 0:
            if '?' in morewhat[0]:
                self.change_state('adjust_confirm')
                self.morewhat = morewhat
            elif morewhat[0] != '':
                self.change_state('do_adjust')
                self.do_adjust(morewhat)
                self.result_offset = 0

    def response(self):
        '''
        NLG module,generating response according to current state
        :return:dialog response
        '''
        if len(self.preset) > 0:
            sentence_list = ['好的～根据客官的需求,小助手', '收到～小助手帮客官', '明白了！善解人意的小助手帮客官']
            prefix = get_random_sentence(sentence_list)
            for item in self.preset:
                if item[0] == 'price':
                    prefix += '预设价格为%s元左右,' % str(int(item[2]))
            self.prefix = prefix
            self.preset = []
        elif len(self.current_commit_sv) > 0:
            sentence_list = ['好的～', '明白～', '好咧,', '好的哟,', '没问题,']
            prefix = get_random_sentence(sentence_list)
            commit_str = self.get_slot_table(self.current_commit_sv)
            print("current commit:", commit_str)
            label_to_name = {'brand': '品牌',
                             'price': '价格',
                             'pixel': '像素',
                             'level': '级别',
                             'frame': '画幅',
                             'type': '类型',
                             'screen': '屏幕类型',
                             'shutter': '快门类型',
                             'experience': '体验要求',
                             'function': '功能要求'}
            for item in commit_str:
                if item in ['brand', 'price', 'level', 'frame', 'type', 'screen', 'shutter']:
                    if self.state == 'result':
                        prefix += '修改%s为%s,' % (label_to_name[item], commit_str[item])
                    else:
                        prefix += '%s%s,' % (label_to_name[item], commit_str[item])
                if item == 'pixel':
                    if self.state == 'result':
                        prefix += '修改%s为%s,' % (label_to_name[item], commit_str[item])
                    else:
                        prefix += '%s%s,' % (label_to_name[item], commit_str[item])
                    if '不限' not in commit_str[item]:
                        prefix += '万,'
                    else:
                        prefix += ','

                if item in ['experience', 'function']:
                    if self.state == 'result':
                        prefix += '修改%s为%s,' % (label_to_name[item], commit_str[item])
                    else:
                        prefix += '%s为%s,' % (label_to_name[item], commit_str[item])

            self.prefix = prefix
            self.current_commit_sv = []

        if self.state == 'ask':
            # 检查必须的slot_value,如果没有的话就发出提问
            if self.ask_slot != '':
                if self.extract_none:
                    self.extract_none = False
                    res = self.prefix + get_random_sentence(fail_slot[self.ask_slot])
                    self.prefix = ''
                    return res
                else:
                    res = self.prefix + get_random_sentence(ask_slot[self.ask_slot])
                    self.prefix = ''
                    return res
            else:
                self.extract_none = False
            unasked = []
            for slot in necessary_tag:
                if slot not in self.asked:
                    unasked.append(slot)
            if len(unasked) > 0:
                num = np.random.randint(len(unasked))
                slot = unasked[num]
                self.ask_slot = slot
                res = self.prefix + get_random_sentence(ask_slot[slot])
                self.prefix = ''
                return res
            # 如果到了这里,说明所有的slot都问完了,转入confirm_result
            else:
                self.change_state('ask_more')
                return self.response()

        if self.state == 'ask_more':
            if not self.asked_more:
                # first ask
                sentence_list = ['请问客官还有其他需求吗?', '请问客官还有进一步的需求吗?']
                self.asked_more = True
                res = self.prefix + get_random_sentence(sentence_list)
                self.prefix = ''
                return res
            else:
                # not first ask
                if self.extract_none:
                    self.extract_none = False
                    res = self.prefix + get_random_sentence(fail_slot['more'])
                    self.prefix = ''
                    return res
                sentence_list = ['请问客官还有其他需求吗?', '请问客官还有进一步的需求吗?']
                res = self.prefix + get_random_sentence(sentence_list)
                self.prefix = ''
                return res

        if self.state == 'list':
            self.change_state('ask')
            if self.ask_slot == '':
                return self.response()
            return get_random_sentence(list_info[self.ask_slot])

        if self.state == 'result':
            res = self.search(self.slot_value)
            self.result_list = res
            if len(res) == 0:
                sentence_list = ["小助手暂时没找到合适的商品哦,换个条件试试?","小助手翻遍了数据库,还是没找到合适的商品,换个条件试试？",
                                 "客官的要求太独特了,小助手找不到符合的商品,可否换个条件试试?","小助手尽力了，但是还是没有找到合适的商品，换个条件试试？"]
                res = self.prefix + get_random_sentence(sentence_list)
                self.prefix = ''
                return res
            sentence_list = ["为客官推荐以下商品,可回复第几个进行选择,回复“查看更多”可以显示其他商品哦～","经过小助手精挑细选，使出蛮荒之力，给客官推荐以下几款产品，回复第几个即可选择哟，回复“查看更多”可以显示其他商品～"]
            res = self.prefix + get_random_sentence(sentence_list)
            self.prefix = ''
            return res

        if self.state == 'adjust_confirm':
            target = self.morewhat[0].replace('?', '')
            if target == 'price':
                self.expected = 'price'
                if self.morewhat[1] <= 0:
                    return get_random_sentence(["请问您是需要更贵的产品吗?"])
                else:
                    return get_random_sentence(["请问您是需要更便宜的产品吗?"])

        if self.state == 'confirm_choice':
            sentence_list = ["即将为您预订以下商品,是否确认？"]
            return get_random_sentence(sentence_list)

        if self.state == 'done':
            sentence_list = ["本次服务已结束,谢谢您的使用","小助手成功完成任务啦，我们下次再见～","小助手服务结束了哦～谢谢客官的支持！"]
            self.finish = True
            return get_random_sentence(sentence_list)

    def do_choice(self):
        '''
        select a result
        :return:None
        '''
        self.list = [self.choice]

    def check_necessary(self):
        '''
        check if all the necessary tag is asked
        :return:True / False
        '''
        for tag in necessary_tag:
            if tag not in self.asked:
                return False
        return True

    def ask_more(self, sentence):
        '''
        check slot every time
        check yes or no,too
        mostly copy from adjust_confirm
        :param sentence:
        :return:None
        '''
        print("ask more", sentence)
        intent = self.nlu.intention_predict(sentence)
        print("intent", intent)
        if intent == 'answer_no':
            self.change_state('result')
            return
        else:
            for word in no_word:
                if word in sentence:
                    self.change_state('result')
                    return

        tag = self.extract(sentence)
        intent = self.nlu.requirement_predict(sentence)
        if len(tag) == 0 and intent == 'whatever':
            if self.ask_slot != '':
                self.write({self.ask_slot: [('whatever', '=')]})
        else:
            tag = self.nlu.confirm_slot(tag, sentence)
            to_add = self.fill_message(tag)
            self.write(to_add)
            if len(to_add) == 0:
                print("set extract none to True")
                self.extract_none = True

    def ask(self, sentence):
        '''
        check user response for a asking action
        :param sentence:user input
        :return:None
        '''
        intent = self.nlu.intention_predict(sentence)
        if intent == 'ask_slot_list':
            self.change_state('list')
            self.list_slot(sentence)
        else:
            tag = self.extract(sentence)
            intent = self.nlu.requirement_predict(sentence)
            print(sentence, intent)
            print(tag)
            if len(tag) == 0 and intent == 'whatever':
                if self.ask_slot != '':
                    self.write({self.ask_slot: [('whatever', '=')]})
            else:
                tag = self.nlu.confirm_slot(tag, sentence)
                to_add = self.fill_message(tag)
                self.write(to_add)
                if len(to_add) == 0:
                    tag = []
                    sents = split_all(sentence)
                    for sent in sents:
                        tag.extend(self.get_about_intention(sent))
                    if len(tag) > 0:
                        for t in tag:
                            t['need'] = True
                        to_add = self.fill_message(tag)
                        self.write(to_add)
                    if len(to_add) == 0:
                        self.extract_none = True
            if self.check_necessary():
                self.change_state('ask_more')

    def init(self, sentence):
        '''
        init state
        :param sentence:user input
        :return:None
        '''
        self.change_state('ask')
        self.ask(sentence)

    def chose(self, sentence):
        pass

    def filterNum(self, s):
        '''
        check if string contains continuous number
        :param s:
        :return:
        '''
        match = re.search(r'(\d+[\.\d+]*)', s)
        if match:
            return float(match.group(1))
        else:
            return -1

    def fill_message(self, tag):
        '''
        transfer the tag format
        :param tag:[{'type': 'pixel_m', 'word': '我要3000万像素的'}]
        :return:{'像素':[(3000,'=')]}
        '''
        for t in tag:
            if t['need'] is None:
                t['need'] = True
        print("fill_message", tag)
        if len(tag) == 0:
            return {}
        res = defaultdict(lambda: [])
        # entities = tag['entities']
        op_dict = {'l': '>=', 'm': '=', 'u': '<='}
        bi_tag = ['brand', 'experience', 'function', 'frame', 'type', 'level']
        for t in tag:
            op = '='
            name = t['type']
            if t['type'] in bi_tag:
                if t['need']:
                    res[name].append((t['word'], '='))
                else:
                    res[name].append((t['word'], '!='))
            else:
                if t['word'] == 'whatever':
                    res[name] = [('whatever', '=')]
                    continue
                if t['type'].find('_') != -1:
                    name_ = t['type'].split('_')
                    name = name_[0]
                    op = op_dict[name_[1]]
                value = self.filterNum(t['word'])
                if value > 0:
                    res[name].append((value, op))
        res = dict(res)
        print("fill message result:", res)
        return res

    def write(self, table):
        '''
        write slot-value-pair to slot table
        :param table:{'像素':[(3000,'=')]}
        :return:None
        '''
        # table：待写入的slot-value
        print("write", table)
        for t in table:
            if t == self.ask_slot:
                self.asked.append(self.ask_slot)
                self.ask_slot = ''
            if t not in self.slot_value:
                self.slot_value[t] = []
            if t in ['experience', 'function']:
                self.slot_value[t].extend(table[t])
                attr_set = set()
                squeeze = []
                for attr in self.slot_value[t]:
                    if attr[0] not in attr_set:
                        attr_set.add(attr[0])
                        squeeze.append(attr)
                self.slot_value[t] = squeeze

            else:
                self.slot_value[t] = table[t]
            self.asked.append(t)
        if len(table) > 0:
            self.current_commit_sv = table
        print("write done")

    def check_choice(self, sentence):
        '''
        check which result user chose
        :param sentence: user input
        :return:result index
        '''
        # 1. 通过第几个的方式来选择 
        if len(self.result_list) == 0:
            return False
        pattern = re.compile('^([一二三四五12345])$')
        m = pattern.search(sentence)
        if (m):
            index = trans_number(m.group(1))
            if index > len(self.list):
                return False
            if '倒数' in sentence or '最后' in sentence:
                index = -index
            if index > 0:
                self.choice = self.result_list[index - 1]
            else:
                self.choice = self.result_list[index]
            return True

        pattern = re.compile('[第|最后]([一二三四五12345])')
        m = pattern.search(sentence)
        if m:
            index = trans_number(m.group(1))
            if index > len(self.result_list):
                return False
            if '倒数' in sentence or '最后' in sentence:
                index = -index
            if index > 0:
                self.choice = self.result_list[index - 1]
            else:
                self.choice = self.result_list[index]
            return True
        else:
            intent = self.nlu.requirement_predict(sentence)
            if intent == 'whatever':
                self.choice = self.result_list[0]
                return True
            else:
                for word in whatever_word:
                    if word in sentence:
                        self.choice = self.result_list[0]
                        return True
                return False

    def slot_validate_check(self, sv_pair):
        print("validate check:", sv_pair)
        sv_pair = [pair for pair in sv_pair if pair['type'].split('_')[0] in tagToLabel]
        print("filter illegal slot:", sv_pair)

        filtered_sv = []
        number = re.compile(r'^\d+$')
        frame_list = ['APS-C画幅', '全画幅', '中画幅', 'm4/3画幅', 'APS-H画幅', 'APS画幅', '半画幅']
        frame_list = [frame.lower() for frame in frame_list]
        level_list = ['入门级', '初级', '中级', '高级', '专业', '中端', '低端', '高端', '新手级', '入门']
        type_list = ['卡片机', '广角相机', '长焦', '三防', '微单', '卡片', '数码微单', 'vr相机', '全景相机', 'VR相机', '单反', '胶片相机', '移轴机', '全景相机',
                     '多功能照相机', '家用摄像机']
        for sv in sv_pair:
            # check brand
            if sv['word'] == 'whatever':
                filtered_sv.append(sv)
                continue
            if sv['type'] == 'brand':
                if sv['word'] not in brand_list:
                    continue
            # check price
            if 'price' in sv['type']:
                sv['word'] = sv['word'].replace('元', '').replace('块', '')
                price = trans_price(sv['word'])
                if price == -1:
                    continue
                sv['word'] = str(price)
            # check frame
            if sv['type'] == 'frame':
                if sv['word'] not in frame_list:
                    continue
            # check level
            if sv['type'] == 'level':
                if sv['word'] not in level_list:
                    continue
            # check pixel
            if 'pixel' in sv['type']:
                if not re.match('\d+万*', sv['word']):
                    continue
            # check type
            if sv['type'] == 'type':
                if sv['word'] not in type_list:
                    continue
            filtered_sv.append(sv)
        print("after check:", filtered_sv)
        return filtered_sv

    def get_about_intention(self, sentence):
        '''
        type 1: 要内存大的（出现target和目标词
        type 2: 要便宜点的（隐藏的目标为当前的slot
        :param sentence:
        :return:[(type:'',word:'')]
        '''
        print("get about intention")
        res = []
        # type 1
        target_word = ['价格']
        target_to_label = {'价格': 'price'}
        type_1_flag = False
        for word in target_word:
            if word in sentence:
                sentiment, level = check_sentiment_polarity(sentence)
                if level != 'none':
                    type_1_flag = True
                    label = target_to_label[word]
                    preset_value = preset[label][level]
                    res.append({'type': label, 'word': str(preset_value)})
                    self.preset.append((label, level, str(preset_value)))
        # type 2
        if not type_1_flag:
            sentiment, level = check_sentiment_polarity(sentence)
            if level != 'none':
                if self.ask_slot != '':
                    label = self.ask_slot
                    if label in preset:
                        preset_value = preset[label][level]
                        res.append({'type': label, 'word': str(preset_value)})
                        self.preset.append((label, level, str(preset_value)))
        print("about intention result:", res)

        return res

    def extract(self, sentence):
        print("extract")
        sents = split_all(sentence)
        tag = []
        name_to_label = {'牌子': 'brand', '品牌': 'brand', '价格': 'price', '价钱': 'price',
                         '像素': 'pixel', '屏幕': 'screen', '类型': 'type', '级别': 'level', '画幅': 'frame'}
        for sent in sents:
            tag.extend(self.nlu.camera_slot_predict(sent)['entities'])
            intent = self.nlu.requirement_predict(sent)
            for word in whatever_word:
                if word in sent:
                    intent = 'whatever'
            print(sent, intent)
            if intent == 'whatever':
                get_slot = False
                for word in name_to_label:
                    if word in sent:
                        tag.append({'type': name_to_label[word], 'word': 'whatever'})
                        get_slot = True
                if get_slot:
                    continue
                if self.ask_slot != '':
                    tag.append({'type': self.ask_slot, 'word': 'whatever'})
        for word in exp_synonyms:
            if word in sentence:
                tag.append({'type': 'experience', 'word': word})
        func_words = set()
        for word in func_synonyms:
            if word in sentence:
                if func_synonyms[word] in func_words:
                    continue
                func_words.add(func_synonyms[word])
                tag.append({'type': 'function', 'word': word})
        print("extarct res:", tag)
        # 修正tag为数据库标签
        for t in tag:
            for word in label_to_tag:
                t['type'] = t['type'].replace(word, label_to_tag[word])
        print("change tag name:", tag)
        tag = self.slot_validate_check(tag)
        return tag

    def search(self, slot_value_table):
        # 调用这个函数进行数据库查询
        condition = slot_value_table
        result = search_camera(condition)
        self.result_list = result[self.result_offset:self.result_offset + 5]

        return self.result_list

    def get_result(self):
        return_slot = ['name', 'price', 'type', 'level', 'pixel', 'screen', 'shutter']
        res = []
        result_list = self.result_list
        for item in result_list:
            temp = {}
            itemDict = item.__dict__
            for key in itemDict:
                if key in return_slot:
                    if type(itemDict[key]) == float:
                        temp[key] = itemDict[key]
                    elif itemDict[key] is not None:
                        temp[key] = itemDict[key]

            res.append(temp)
        return res

    def get_slot_table(self, slot_value=None):
        '''
        return current slot table
        :return: slot_table dict,{'slot':'value'}
        '''

        if slot_value is None:
            slot_value = self.slot_value
        print("get slot table", slot_value)
        res = {}
        op_dict = {'<=': '小于', '=': '', '>=': '大于', '!=': '不要'}
        order = {'!=': 0, '=': 2, '<=': 1, '>=': 1}
        for slot in slot_value:
            if slot in ['experience', 'function']:
                continue
            sv = sorted(slot_value[slot], key=lambda x: order[x[1]], reverse=True)
            sentence_list = []
            for con in sv:
                word = con[0] if con[0] != 'whatever' else '不限'
                try:
                    word = str(int(word))
                except ValueError:
                    word = str(word)
                sentence_list.append(op_dict[con[1]] + word)
            res[slot] = ','.join(sentence_list)

        for slot in ['experience', 'function']:
            if slot in slot_value:
                sentence_list = []
                for word in slot_value[slot]:
                    if word[1] != '!=':
                        sentence_list.append(word[0])
                if len(sentence_list) > 0:
                    res[slot] = ','.join(sentence_list)
        print("slot table:", res)
        return res


if __name__ == '__main__':
    pass
