#!/usr/bin/env python3
"""One-time, source-checked repair of all 192 cards. IDs and book references stay stable.

The original-sentence replacements were checked against the user's six annotated
reading pages. Supplemental examples are explicitly labelled, never exam quotes.
This script is maintenance history, not a second runtime vocabulary source.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '2026-09-27.1'
BASE_SHAS = {
 '2010-e1-text4': '473e4f5ae0064c97ae40d2711cf5152723e6f2a5',
 '2011-e1-text1': 'd4ba5d7061fc4606cd304b00e0051974b34217ce',
 '2011-e1-text2': 'c62c040ec68e4c7bd61c3df53a3b3604ee23f38c',
 '2011-e1-text3': 'a131b3ef249cfdd012714032ea1302941a2aee9b',
 '2011-e1-text4': 'dc2cab1ab679ea596b03c0d92c465661e9081926',
 '2012-e1-text1': '3613c3da5f18bc9fa4a9e18cb56b45895529a1b7',
}
PATCH = {k: {} for k in BASE_SHAS}


def change(deck, ident, **fields):
    PATCH[deck].setdefault(ident, {}).update(fields)


def original(deck, identifiers, quote, translation, marked=()):
    """A complete original sentence; only genuine marked evidence keeps clue=True."""
    for ident in identifiers.split():
        change(deck, ident, quote=quote, translation=translation,
               exampleType='original', quoteType='真题正文原句', clue=ident in marked)


def supplement(deck, ident, quote, translation, mark):
    """A full teaching example, explicitly distinguished from the question option."""
    change(deck, ident, quote=quote, translation=translation, mark=mark,
           exampleType='supplemental', quoteType='补充例句（助手编写，非真题原句）', clue=False)


def pairs(deck, rows):
    # id | exact phrase appearing in the example | translation of that phrase only
    for line in rows.strip().splitlines():
        ident, phrase, meaning = (s.strip() for s in line.split('|'))
        change(deck, ident, collocation=phrase, collocationMeaning=meaning)


# 2010 English I Text 4: accounting standard-setters.
d = '2010-e1-text4'
original(d, 'blame', 'Bankers have been blaming themselves for their troubles in public.',
         '银行家们在公开场合一直因自身的困境责怪自己。')
original(d, 'behind-scenes standard-setter',
         'Behind the scenes, they have been taking aim at someone else: the accounting standard-setters.',
         '在幕后，他们却一直把矛头指向别人：会计准则制定者。')
original(d, 'moan',
         'Their rules, moan the banks, have forced them to report enormous losses, and it’s just not fair.',
         '银行抱怨说，这些规则迫使它们报告巨额亏损，这实在不公平。', marked=('moan',))
original(d, 'asset fetch',
         'These rules say they must value some assets at the price a third party would pay, not the price managers and regulators would like them to fetch.',
         '这些规则要求银行按第三方愿意支付的价格，而非经理和监管者希望资产卖出的价格，为部分资产估值。', marked=('asset','fetch'))
original(d, 'lobby', 'Unfortunately, banks’ lobbying now seems to be working.',
         '遗憾的是，银行的游说如今似乎正在奏效。')
original(d, 'compromise',
         'The details may be unknowable, but the independence of standard-setters, essential for the proper functioning of capital markets, is being compromised.',
         '具体细节或许无从知晓，但对资本市场正常运作至关重要的准则制定者的独立性正在受到损害。')
original(d, 'toxic-assets',
         'And, unless banks carry toxic assets at prices that attract buyers, reviving the banking system will be difficult.',
         '而且，除非银行按能够吸引买家的价格将问题资产入账，否则银行体系将难以复苏。')
original(d, 'bruising-encounter',
         'After a bruising encounter with Congress, America’s Financial Accounting Standards Board (FASB) rushed through rule changes.',
         '在与国会经历一场激烈而令人受挫的交锋后，美国财务会计准则委员会匆忙通过了规则修改。')
original(d, 'illiquid flexibility',
         'These gave banks more freedom to use models to value illiquid assets and more flexibility in recognizing losses on long-term assets in their income statements.',
         '这些修改让银行在用模型评估难以变现的资产时拥有更多自由，也让它们在损益表中确认长期资产损失时拥有更大的灵活性。')
original(d, 'overall',
         'The IASB says it does not want to act without overall planning, but the pressure to fold when it completes its reconstruction of rules later this year is strong.',
         '国际会计准则理事会表示不愿在缺少总体规划的情况下行动，但它在当年晚些时候完成规则重构时，将面临强大的妥协压力。')
original(d, 'bad-debts',
         'Today they argue that market prices overstate losses, because they largely reflect the temporary illiquidity of markets, not the likely extent of bad debts.',
         '如今银行主张，市场价格夸大了损失，因为这些价格主要反映市场暂时缺乏流动性，而非坏账可能达到的规模。')
original(d, 'book-value investor skeptical',
         'But banks’ shares trade below their book value, suggesting that investors are skeptical.',
         '但银行股票的交易价格低于其账面价值，这表明投资者持怀疑态度。')
original(d, 'paralysis reluctant booking-losses',
         'And dead markets partly reflect the paralysis of banks which will not sell assets for fear of booking losses, yet are reluctant to buy all those supposed bargains.',
         '而市场停滞也在一定程度上反映了银行的瘫痪状态：它们害怕确认亏损而不肯卖出资产，却又不愿买入那些所谓的便宜货。')
original(d, 'combative', 'Successful markets require independent and even combative standard-setters.',
         '成功的市场需要独立、甚至敢于对抗压力的准则制定者。', marked=('combative',))
original(d, 'pension',
         'The FASB and IASB have been exactly that, cleaning up rules on stock options and pensions, for example, against hostility from special interests.',
         '美国财务会计准则委员会和国际会计准则理事会过去正是如此，例如，它们曾顶住特殊利益集团的敌意，整顿股票期权和养老金方面的规则。')
for row in [
 ('sympathy','She expressed sympathy for the workers who had lost their jobs.','她对失去工作的工人表示同情。','sympathy'),
 ('object-to','The committee objects to changing the rules without discussion.','委员会反对未经讨论就修改规则。','objects to'),
 ('exaggerate','The report exaggerated the value of the assets.','这份报告夸大了资产的价值。','exaggerated'),
 ('revival','The revival of the local economy created new jobs.','当地经济的复苏创造了新的就业岗位。','revival'),
 ('reevaluate','The bank needs to reevaluate some of its assets.','这家银行需要重新评估部分资产。','reevaluate'),
 ('misinterpret','Readers may misinterpret the figures without enough context.','缺乏足够的背景信息时，读者可能会误解这些数字。','misinterpret'),
 ('neglect','The report neglected the risk of bad debts.','这份报告忽视了坏账风险。','neglected'),
 ('deny','The manager denied hiding the losses.','经理否认隐瞒了亏损。','denied'),
 ('objectiveness','The editor questioned the objectiveness of the report.','编辑对这份报道的客观性提出了质疑。','objectiveness'),
 ('diminish','Public trust may diminish when important facts are hidden.','重要事实被隐瞒时，公众的信任可能会减弱。','diminish'),
]: supplement(d,*row)
change(d,'blame',mark='blaming themselves for their troubles')
change(d,'object-to',note='object to＝反对；to 是介词，后接名词或动名词。词条来自第38题题干；例句是另写的用法示例。')
change(d,'objectiveness',form='第40题选项 C；名词',note='objectiveness＝客观性，与 objective“客观的”对应。第40题中它是干扰项，不应当作作者态度的结论。')
change(d,'diminish',note='diminish 是动词“减弱、减少”。第37题中的 the diminishing role of management 指“管理层作用的减弱”，并非正确选项。')
change(d,'deny',note='deny doing sth.＝否认做过某事。原选项不是文章事实，故用另写例句展示语法，避免把干扰项当作结论。')
change(d,'sympathy',form='第40题选项 D；名词',note='sympathy 可表示同情，也可表示支持、赞同。例句展示常见用法；原题中作者同情准则制定者承受的压力，并不赞成其每次让步。')
pairs(d, '''
sympathy | sympathy for the workers | 对工人的同情
compromise | is being compromised | 正在受到损害
lobby | banks’ lobbying | 银行的游说
asset | value some assets | 为部分资产估值
illiquid | illiquid assets | 难以变现的资产
booking-losses | for fear of booking losses | 因害怕确认亏损
reluctant | are reluctant to buy | 不愿购买
object-to | objects to changing the rules | 反对修改规则
exaggerate | exaggerated the value | 夸大了价值
revival | revival of the local economy | 当地经济的复苏
blame | blaming themselves for their troubles | 因自身困境责怪自己
behind-scenes | Behind the scenes | 在幕后
standard-setter | accounting standard-setters | 会计准则制定者
moan | moan the banks | 银行抱怨说
toxic-assets | carry toxic assets | 将问题资产入账
bruising-encounter | a bruising encounter with Congress | 与国会的一场激烈交锋
flexibility | more flexibility in recognizing losses | 确认损失时更大的灵活性
overall | overall planning | 总体规划
book-value | below their book value | 低于其账面价值
investor | investors are skeptical | 投资者持怀疑态度
paralysis | the paralysis of banks | 银行的瘫痪状态
combative | combative standard-setters | 敢于对抗压力的准则制定者
pension | rules on stock options and pensions | 关于股票期权和养老金的规则
reevaluate | reevaluate some of its assets | 重新评估部分资产
misinterpret | misinterpret the figures | 误解这些数字
neglect | neglected the risk | 忽视了风险
bad-debts | extent of bad debts | 坏账的规模
deny | denied hiding the losses | 否认隐瞒亏损
objectiveness | objectiveness of the report | 报道的客观性
skeptical | investors are skeptical | 投资者持怀疑态度
diminish | trust may diminish | 信任可能减弱
fetch | would like them to fetch | 希望它们卖得（某个价钱）
''')

# 2011 English I Text 1: live classical music and recordings.
d='2011-e1-text1'
original(d,'announcement appointment',
 'The decision of the New York Philharmonic to hire Alan Gilbert as its next music director has been the talk of the classical-music world ever since the sudden announcement of his appointment in 2009.',
 '纽约爱乐乐团决定聘请艾伦·吉尔伯特担任下一任音乐总监；自2009年突然公布这一任命以来，这个决定就一直是古典音乐界热议的话题。')
original(d,'unpretentious formidable',
 'Even Tommasini, who had advocated Gilbert’s appointment in the Times, calls him “an unpretentious musician with no air of the formidable conductor about him.”',
 '就连曾在《纽约时报》倡议任命吉尔伯特的托马西尼，也称他为“一位谦逊朴实、毫无令人敬畏的大指挥家派头的音乐家”。', marked=('unpretentious','formidable'))
original(d,'description orchestra hitherto faint-praise',
 'As a description of the next music director of an orchestra that has hitherto been led by musicians like Gustav Mahler and Pierre Boulez, that seems likely to have struck at least some Times readers as faint praise.',
 '对于一支此前一直由古斯塔夫·马勒、皮埃尔·布列兹这类音乐家执掌的乐团来说，用这种话描述它的下一任音乐总监，至少在部分《纽约时报》读者看来，恐怕只是勉强的称赞。')
original(d,'orchestral',
 'To be sure, he performs an impressive variety of interesting compositions, but it is not necessary for me to visit Avery Fisher Hall, or anywhere else, to hear interesting orchestral music.',
 '诚然，他演奏的有趣作品种类丰富，令人印象深刻；但为了听到有趣的管弦乐，我没有必要前往艾弗里·费舍尔音乐厅或其他任何地方。')
original(d,'substitute concertgoer no-substitute-for miss-the-point',
 'Devoted concertgoers who reply that recordings are no substitute for live performance are missing the point.',
 '那些回应说“录音无法替代现场演出”的忠实音乐会观众，没有抓住问题的关键。',marked=('substitute','concertgoer','no-substitute-for','miss-the-point'))
original(d,'instrumentalist troupe museum',
 'For the time, attention, and money of the art-loving public, classical instrumentalists must compete not only with opera houses, dance troupes, theater companies, and museums, but also with the recorded performances of the great classical musicians of the 20th century.',
 '为了争夺艺术爱好者的时间、注意力和金钱，古典器乐演奏者不仅必须与歌剧院、舞团、剧团和博物馆竞争，还必须与20世纪古典音乐大师的演奏录音竞争。')
original(d,'vibrant',
 'Gilbert’s own interest in new music has been widely noted: Alex Ross, a classical-music critic, has described him as a man who is capable of turning the Philharmonic into “a markedly different, more vibrant organization.”',
 '吉尔伯特本人对新音乐的兴趣已广受关注：古典音乐评论家亚历克斯·罗斯称，他有能力把爱乐乐团变成“一个明显不同、更加充满活力的组织”。')
original(d,'repertoire','Merely expanding the orchestra’s repertoire will not be enough.',
 '仅仅扩大乐团的曲目范围还不够。')
original(d,'for-the-most-part to-say-the-least',
 'For the most part, the response has been favorable, to say the least.',
 '总体而言，反响是积极的——这么说已经很保守了。',marked=('for-the-most-part','to-say-the-least'))
for row in [
 ('incur','The decision incurred criticism from several musicians.','这个决定招致了几位音乐家的批评。','incurred'),
 ('suspicion','The sudden change raised suspicion among the staff.','这一突然的变化引起了员工的怀疑。','suspicion'),
 ('curiosity','The unusual concert title aroused my curiosity.','这个不同寻常的音乐会标题引起了我的好奇心。','curiosity'),
 ('modest','The talented musician remained modest about her achievements.','这位有才华的音乐家对自己的成就仍保持谦逊。','modest'),
 ('expense','Travel expenses made the concert more costly for visitors.','交通费用使观众参加这场音乐会的总花费更高。','expenses'),
 ('exaggerate','The advertisement exaggerated the variety of the performances.','这则广告夸大了演出的多样性。','exaggerated'),
 ('overestimate','We should not overestimate the value of a famous name.','我们不应高估名气的价值。','overestimate'),
]: supplement(d,*row)
change(d,'appointment',form='正文：his appointment；第21题题干也出现 appointment')
change(d,'exaggerate',note='exaggerate＝夸大。原题C项不是正确结论；补充例句只展示词义和搭配。')
change(d,'incur',note='incur criticism＝招致批评。原文中任命的总体反响是积极的，不要把原题干扰项记成文章事实。')
change(d,'suspicion',note='raise suspicion＝引起怀疑。此例另写；它不表示文中吉尔伯特的任命确实引起了怀疑。')
change(d,'curiosity',note='arouse curiosity＝引起好奇心。补充例句只帮助记忆搭配，不替代原题证据。')
change(d,'for-the-most-part',note='for the most part≈generally/mostly，表示总体而言；原句是第21题的定位依据。')
pairs(d, '''
announcement | announcement of his appointment | 公布对他的任命
unpretentious | an unpretentious musician | 一位谦逊朴实的音乐家
formidable | the formidable conductor | 令人敬畏的大指挥家
description | a description of the next music director | 对下一任音乐总监的描述
orchestra | an orchestra | 一支管弦乐队
hitherto | has hitherto been led | 此前一直由……领导
orchestral | orchestral music | 管弦乐
substitute | no substitute for live performance | 不能替代现场演出
instrumentalist | classical instrumentalists | 古典器乐演奏者
troupe | dance troupes | 舞团
museum | theater companies, and museums | 剧团和博物馆
vibrant | a markedly different, more vibrant organization | 一个明显不同、更有活力的组织
repertoire | expanding the orchestra’s repertoire | 扩大乐团的曲目范围
appointment | his appointment | 对他的任命
incur | incurred criticism | 招致了批评
suspicion | raised suspicion | 引起了怀疑
curiosity | aroused my curiosity | 引起了我的好奇心
modest | modest about her achievements | 对自己的成就保持谦逊
concertgoer | Devoted concertgoers | 忠实的音乐会观众
expense | Travel expenses | 交通费用
exaggerate | exaggerated the variety | 夸大了多样性
overestimate | overestimate the value | 高估价值
for-the-most-part | For the most part | 总体而言
to-say-the-least | to say the least | 这么说已经很保守
faint-praise | faint praise | 勉强的称赞
no-substitute-for | recordings are no substitute for live performance | 录音无法替代现场演出
miss-the-point | are missing the point | 没有抓住重点
''')

# 2011 English I Text 2: leaving before finding the next job.
d='2011-e1-text2'
original(d,'cloak-vague-excuses pursue',
 'Rather than cloaking his exit in the usual vague excuses, he came right out and said he was leaving “to pursue my goal of running a company.”',
 '他没有用惯常的含糊借口掩饰自己的离职，而是直言，离开是为了“追求我经营一家公司的目标”。')
original(d,'aspiration','It also sent a clear message to the outside world about his aspirations.',
 '这也向外界清楚地传达了他的抱负。')
original(d,'executive',
 'In recent weeks the No.2 executives at Avon and American Express quit with the explanation that they were looking for a CEO post.',
 '最近几周，雅芳和美国运通的二号高管也辞了职，并解释说，他们正在寻找首席执行官的职位。')
original(d,'scrutinize get-the-nod',
 'As boards scrutinize succession plans in response to shareholder pressure, executives who don’t get the nod also may wish to move on.',
 '随着董事会在股东压力下仔细审查继任计划，那些未获选中的高管也可能想另谋出路。')
original(d,'turbulent cautious',
 'A turbulent business environment also has senior managers cautious of letting vague pronouncements cloud their reputations.',
 '动荡的商业环境也使高级经理保持谨慎，避免让含糊的公开表态损害自己的声誉。')
original(d,'deputy-chief jump-without-net',
 'As the first signs of recovery begin to take hold, deputy chiefs may be more willing to make the jump without a net.',
 '随着经济复苏的初步迹象开始稳固，副主管们可能更愿意在没有下一份工作保障的情况下先离职。')
original(d,'abound aspiring','As the economy picks up, opportunities will abound for aspiring leaders.',
 '随着经济复苏，有抱负的领导者将迎来大量机会。')
original(d,'unconventional','The decision to quit a senior position to look for a better one is unconventional.',
 '辞去高级职位，再去寻找更好的职位，这种决定并不符合传统惯例。')
original(d,'adhere-to candidate poach',
 'For years executives and headhunters have adhered to the rule that the most attractive CEO candidates are the ones who must be poached.',
 '多年来，高管和猎头一直遵循这样一条规则：最有吸引力的首席执行官候选人，往往是那些需要从别处挖来的人。',marked=('adhere-to','candidate','poach'))
original(d,'recruiter disgrace-fading','Many recruiters say the old disgrace is fading for top performers.',
 '许多招聘人员说，对表现出色的人才而言，那种过去被认为丢脸的处境所带来的污名正在消退。')
original(d,'fundamentally-inverted',
 '“The traditional rule was it’s safer to stay where you are, but that’s been fundamentally inverted,” says one headhunter.',
 '一名猎头说：“传统观念认为留在原来的位置更安全，但这种观念已经被从根本上颠倒了。”')
original(d,'straight-up',
 'When Liam McGee departed as president of Bank of America in August, his explanation was surprisingly straight up.',
 '利亚姆·麦吉在8月卸任美国银行总裁时，给出的解释出奇地坦率直接。',marked=('straight-up',))
original(d,'line-up-position reflect-on',
 'McGee says leaving without a position lined up gave him time to reflect on what kind of company he wanted to run.',
 '麦吉说，没有预先落实下一份职位就离职，给了他时间认真思考自己想经营什么样的公司。',marked=('line-up-position','reflect-on'))
for row in [
 ('frank','She was frank about her reasons for leaving.','她坦率地说明了自己离开的原因。','frank'),
 ('arrogant','His arrogant manner made the discussion difficult.','他傲慢的态度使讨论难以进行。','arrogant'),
 ('impulsive','Quitting without considering the consequences would be impulsive.','不考虑后果就辞职会显得冲动。','impulsive'),
 ('approve-of','The board did not approve of the proposed changes.','董事会并不赞成这些拟议的修改。','approve of'),
 ('cling-to-post','Some managers cling to their posts even when change is needed.','即使需要作出改变，一些经理仍守着自己的职位不放。','cling to their posts'),
 ('out-dated','The company replaced its out-dated rules with new ones.','公司用新规则取代了过时的规则。','out-dated'),
]: supplement(d,*row)
change(d,'aspiration',term='aspiration',meaning='抱负，志向',form='原文复数：aspirations；搭配 career aspirations＝职业抱负',note='aspiration 是名词，aspire 是相关动词。本文指麦吉希望经营一家公司的抱负。')
change(d,'poach',meaning='挖走一位候选人；挖角',note='poach a candidate＝从别的公司挖走候选人。本文被动式 must be poached 表示“必须被挖角”；对应第28题的 hunted for。')
change(d,'frank',note='frank＝坦率的，与正文 straight up 对应；补充例句展示 frank about sth.。')
change(d,'arrogant',note='arrogant＝傲慢的。原题强调麦吉的表达坦率，并未说他傲慢；补充例句另设人物，不是文章事实。')
change(d,'impulsive',note='impulsive 是形容词“冲动的”，相关名词为 impulse。此例不表示文中的麦吉确实行事冲动。')
change(d,'approve-of',note='approve of＝赞成、认可。它不是 poach“挖角”的同义词；不再将原题错误选项拼成例句。')
change(d,'out-dated',note='out-dated＝过时的；与 up-to-date“最新的”对照。例句另写，不把“忠诚过时”当作文章结论。')
change(d,'cling-to-post',note='cling to one’s post＝守着职位不放。第29题结合旧规则“留在原位更安全”理解；补充例句只演示搭配。')
change(d,'disgrace-fading',meaning='污名正在消退；那种丢脸的感觉正在淡去',note='disgrace＝羞耻、耻辱；fade＝逐渐消失。结合下一句，这里指换工作空档期或离开差工作不再像过去那样被看作丢脸。')
pairs(d, '''
cloak-vague-excuses | cloaking his exit in the usual vague excuses | 用惯常的含糊借口掩饰离职
pursue | pursue my goal | 追求我的目标
aspiration | his aspirations | 他的抱负
executive | the No.2 executives | 二号高管
scrutinize | scrutinize succession plans | 仔细审查继任计划
turbulent | A turbulent business environment | 动荡的商业环境
cautious | cautious of letting vague pronouncements cloud their reputations | 谨慎避免让含糊表态损害声誉
deputy-chief | deputy chiefs | 副主管们
abound | opportunities will abound | 将会有大量机会
aspiring | aspiring leaders | 有抱负的领导者
unconventional | is unconventional | 不符合常规
adhere-to | have adhered to the rule | 一直遵循这项规则
candidate | CEO candidates | 首席执行官候选人
poach | must be poached | 必须被挖角
recruiter | Many recruiters | 许多招聘人员
disgrace-fading | the old disgrace is fading | 过去的污名正在淡去
fundamentally-inverted | fundamentally inverted | 被从根本上颠倒
straight-up | surprisingly straight up | 出奇地坦率直接
frank | frank about her reasons | 坦率说明她的理由
arrogant | arrogant manner | 傲慢的态度
impulsive | would be impulsive | 会显得冲动
approve-of | approve of the proposed changes | 赞成拟议的修改
cling-to-post | cling to their posts | 守着他们的职位不放
out-dated | out-dated rules | 过时的规则
line-up-position | without a position lined up | 没有预先落实职位
get-the-nod | don’t get the nod | 未被选中
jump-without-net | make the jump without a net | 没有保障就先冒险离职
reflect-on | reflect on what kind of company he wanted to run | 思考他想经营什么样的公司
''')

# 2011 English I Text 3: paid / owned / earned media and reputational risks.
d='2011-e1-text3'
original(d,'rough-guide marketing',
 'The rough guide to marketing success used to be that you got what you paid for.',
 '过去，营销成功的一条大致准则是：一分钱一分货。')
original(d,'commercial-advertisement exploit alternative',
 'While traditional “paid” media—such as television commercials and print advertisements—still play a major role, companies today can exploit many alternative forms of media.',
 '尽管电视广告和平面广告等传统“付费”媒体仍然发挥重要作用，如今企业也能利用许多其他可供选择的媒体形式。')
original(d,'leverage consumer',
 'Consumers passionate about a product may create “earned” media by willingly promoting it to friends, and a company may leverage “owned” media by sending e-mail alerts about products and sales to customers registered with its Web site.',
 '热爱某种产品的消费者可能自愿向朋友推荐它，从而创造“赢得媒体”；企业则可以向在其网站注册的顾客发送产品和促销信息邮件，借此充分利用“自有媒体”。',marked=('consumer',))
original(d,'conventional',
 'The way consumers now approach the process of making purchase decisions means that marketing’s impact stems from a broad range of factors beyond conventional paid media.',
 '消费者如今作出购买决定的方式意味着，营销的影响来自传统付费媒体之外的广泛因素。')
original(d,'retailer',
 'But in some cases, one marketer’s owned media become another marketer’s paid media—for instance, when an e-commerce retailer sells ad space on its Web site.',
 '但在某些情况下，一个营销者的自有媒体会成为另一个营销者的付费媒体，例如电子商务零售商出售自己网站上的广告位时。')
original(d,'ecommerce-engine',
 'We define such sold media as owned media whose traffic is so strong that other organizations place their content or e-commerce engines within that environment.',
 '我们把这种“出售媒体”定义为流量非常大的自有媒体，以至于其他组织会把内容或电商系统放进这一环境中。')
original(d,'infancy',
 'This trend, which we believe is still in its infancy, effectively began with retailers and travel providers such as airlines and hotels and will no doubt go further.',
 '我们认为，这种趋势仍处于初期；它实际上始于零售商以及航空公司、酒店等旅行服务提供者，并且无疑还会继续发展。')
original(d,'complementary',
 'Johnson & Johnson, for example, has created BabyCenter, a stand-alone media property that promotes complementary and even competitive products.',
 '例如，强生创建了BabyCenter，这是一个独立媒体平台，会推广互补产品，甚至竞争产品。')
original(d,'presence',
 'Besides generating income, the presence of other marketers makes the site seem objective, gives companies opportunities to learn valuable information about the appeal of other companies’ marketing, and may help expand user traffic for all companies concerned.',
 '除了带来收入，其他营销者的加入还使网站显得客观，让企业有机会了解其他企业营销吸引力的有价值信息，并可能帮助所有相关企业扩大用户流量。')
original(d,'become-hostage-to stakeholder allegation',
 'Such hijacked media are the opposite of earned media: an asset or campaign becomes hostage to consumers, other stakeholders, or activists who make negative allegations about a brand or product.',
 '这种“被劫持的媒体”与赢得媒体相反：一项资产或营销活动受制于消费者、其他利益相关者或活动人士，这些人会对品牌或产品提出负面指控。')
original(d,'originally',
 'Members of social networks, for instance, are learning that they can hijack media to apply pressure on the businesses that originally created them.',
 '例如，社交网络成员正在学会利用这些媒体，向最初创建它们的企业施压。',marked=('originally',))
original(d,'boycott',
 'If that happens, passionate consumers would try to persuade others to boycott products, putting the reputation of the target company at risk.',
 '如果发生这种情况，情绪强烈的消费者就会试图说服他人抵制产品，使目标公司的声誉面临风险。',marked=('boycott',))
original(d,'steep-learning-curve',
 'In such a case, the company’s response may not be sufficiently quick or thoughtful, and the learning curve has been steep.',
 '在这种情况下，公司的回应可能不够迅速或周全，而学习如何应对这一局面的过程一直很艰难。')
original(d,'campaign alleviate-damage well-orchestrated',
 'Toyota Motor, for example, alleviated some of the damage from its recall crisis earlier this year with a relatively quick and well-orchestrated social-media response campaign, which included efforts to engage with consumers directly on sites such as Twitter and the social-news site Digg.',
 '例如，丰田汽车通过一次相对迅速、组织协调良好的社交媒体回应行动，减轻了当年早些时候召回危机造成的部分损害；行动包括在Twitter和社交新闻网站Digg等平台上直接与消费者交流。')
for row in [
 ('certain','Certain websites allow customers to share product reviews.','某些网站允许顾客分享产品评价。','Certain'),
 ('enthusiastic','Customers were enthusiastic about recommending their favorite products.','顾客们热衷于推荐自己喜爱的产品。','enthusiastic'),
 ('competition','Online retailers face fierce competition for customers.','网络零售商面临争夺顾客的激烈竞争。','competition'),
 ('flexibility','The new system gives the team greater flexibility in planning its work.','新系统让团队在安排工作时拥有更大的灵活性。','flexibility'),
 ('constant','Constant complaints forced the company to review its service.','接连不断的投诉迫使公司重新审视其服务。','Constant'),
 ('fierce','The companies face fiercer competition than before.','这些公司面临比以往更激烈的竞争。','fiercer'),
]: supplement(d,*row)
change(d,'commercial-advertisement',meaning='commercial：电视或电台广告；advertisement：广告',note='两个名词都可表示广告，但 advertisement 本身不限定为平面广告。原句的 print advertisements 才是“平面广告”。')
change(d,'fierce',meaning='激烈的；猛烈的',note='fierce 是原级“激烈的”；fiercer 才是“更激烈的”。词条释义与例句中比较级的搭配义分开记。')
change(d,'certain',meaning='确定的，确信的；某些（置于名词前）',note='本例 certain 修饰 websites，取“某些”义。certain 单独表示“确定的”；它不自带 far less 的否定或程度含义。')
change(d,'flexibility',meaning='灵活性，可变通的余地',note='flexibility＝灵活性；本例展示 flexibility in doing sth.。同词跨篇仍共用原有编号与熟悉度。')
change(d,'steep-learning-curve',meaning='陡峭的学习曲线；此处比喻艰难的学习适应过程',note='steep＝陡的；curve＝曲线。原句强调企业学习应对媒体危机很不容易，并未给出具体时间或金钱成本。')
pairs(d, '''
rough-guide | rough guide to marketing success | 营销成功的大致准则
marketing | marketing success | 营销成功
commercial-advertisement | television commercials and print advertisements | 电视广告和平面广告
exploit | exploit many alternative forms of media | 利用许多替代性的媒体形式
alternative | alternative forms of media | 其他可供选择的媒体形式
leverage | leverage “owned” media | 充分利用自有媒体
conventional | conventional paid media | 传统付费媒体
retailer | an e-commerce retailer | 一家电子商务零售商
ecommerce-engine | e-commerce engines | 电商引擎或系统
infancy | in its infancy | 处于初期
complementary | complementary and even competitive products | 互补产品甚至竞争产品
presence | the presence of other marketers | 其他营销者的存在或加入
campaign | social-media response campaign | 社交媒体回应行动
become-hostage-to | becomes hostage to consumers | 受制于消费者
stakeholder | other stakeholders | 其他利益相关者
allegation | make negative allegations | 提出负面指控
originally | originally created them | 最初创建它们
boycott | persuade others to boycott products | 说服他人抵制产品
steep-learning-curve | the learning curve has been steep | 学习适应过程一直很艰难
alleviate-damage | alleviated some of the damage | 减轻了部分损害
well-orchestrated | well-orchestrated social-media response campaign | 组织协调良好的社交媒体回应行动
consumer | Consumers passionate about a product | 热爱某种产品的消费者
certain | Certain websites | 某些网站
enthusiastic | enthusiastic about recommending their favorite products | 热衷于推荐他们喜爱的产品
competition | fierce competition for customers | 争夺顾客的激烈竞争
flexibility | flexibility in planning its work | 安排工作时的灵活性
constant | Constant complaints | 接连不断的投诉
fierce | fiercer competition | 更激烈的竞争
''')

# 2011 English I Text 4: media representations of parenthood.
d='2011-e1-text4'
original(d,'insightful provocative chatter fulfilling',
 'It’s no surprise that Jennifer Senior’s insightful, provocative magazine cover story, “I love My Children, I Hate My Life,” is arousing much chatter—nothing gets people talking like the suggestion that child rearing is anything less than a completely fulfilling, life-enriching experience.',
 '詹妮弗·西尼尔那篇有见地、引人争议的杂志封面文章《我爱我的孩子，我恨我的生活》引发大量议论，并不奇怪——没有什么比“养育孩子并非完全令人满足、丰富人生的体验”这种说法更能让人议论纷纷。')
original(d,'past-tense-condition',
 'Rather than concluding that children make parents either happy or miserable, Senior suggests we need to redefine happiness: instead of thinking of it as something that can be measured by moment-to-moment joy, we should consider being happy as a past-tense condition.',
 '西尼尔并未断言孩子使父母幸福或痛苦，而是建议重新定义幸福：与其认为幸福可以用每一刻的快乐衡量，不如把它看作一种回顾过去时才体会到的状态。',marked=('past-tense-condition',))
original(d,'soul-crushingly-hard dampen gratification delight',
 'Even though the day-to-day experience of raising kids can be soul-crushingly hard, Senior writes that “the very things that in the moment dampen our moods can later be sources of intense gratification and delight.”',
 '西尼尔写道，尽管日常养育孩子可能艰难到令人身心俱疲，“正是那些当下使我们情绪低落的事情，日后却可能成为强烈满足感和快乐的来源”。')
original(d,'madonna-and-child',
 'The magazine cover showing an attractive mother holding a cute baby is hardly the only Madonna-and-child image on newsstands this week.',
 '这个展示漂亮母亲抱着可爱婴儿的杂志封面，远不是本周报摊上唯一的“圣母与圣婴”式母子形象。')
original(d,'newsstand',
 'Practically every week features at least one celebrity mom, or mom-to-be, smiling on the newsstands.',
 '几乎每周，报摊上的杂志都会展示至少一位面带笑容的明星妈妈或准妈妈。')
original(d,'persistently celebrate procreation equivalent-to',
 'In a society that so persistently celebrates procreation, is it any wonder that admitting you regret having children is equivalent to admitting you support kitten-killing?',
 '在一个如此持续颂扬生育的社会里，承认自己后悔生孩子，竟如同承认支持杀害小猫一样令人反感，这又有什么奇怪的呢？')
original(d,'regret','It doesn’t seem quite fair, then, to compare the regrets of parents to the regrets of the childless.',
 '因此，把有孩子者的后悔和无子女者的后悔直接比较，似乎并不十分公平。')
original(d,'provoke misery folk',
 'Unhappy parents rarely are provoked to wonder if they shouldn’t have had kids, but unhappy childless folks are bothered with the message that children are the single most important thing in the world: obviously their misery must be a direct result of the gaping baby-size holes in their lives.',
 '不幸福的父母很少会被促使去怀疑自己是不是不该生孩子；但不幸福的无子女者却受到“孩子是世上最重要的东西”这一信息的困扰：仿佛他们的痛苦显然就一定源于生活中那个缺少孩子的巨大空缺。',marked=('folk',))
original(d,'hugely',
 'Of course, the image of parenthood that celebrity magazines like Us Weekly and People present is hugely unrealistic, especially when the parents are single mothers like Bullock.',
 '当然，《美国周刊》和《人物》等明星杂志呈现的育儿形象极其不现实，尤其当其中的家长是像布洛克那样的单身母亲时。',marked=('hugely',))
original(d,'dumb glamorous haircut',
 'It’s hard to imagine that many people are dumb enough to want children just because Reese and Angelina make it look so glamorous: most adults understand that a baby is not a haircut.',
 '很难想象会有很多人，仅仅因为瑞茜和安吉丽娜把育儿呈现得如此光鲜迷人，就傻到因此想要孩子：大多数成年人都明白，生孩子可不像换个发型那么简单。')
original(d,'subconscious',
 'But it’s interesting to wonder if the images we see every week of stress-free, happiness-enhancing parenthood aren’t in some small, subconscious way contributing to our own dissatisfactions with the actual experience, in the same way that a small part of us hoped getting “the Rachel” might make us look just a little bit like Jennifer Aniston.',
 '但值得思考的是：我们每周看到的那些毫无压力、增添幸福的育儿形象，会不会正以某种轻微而潜意识的方式，加剧我们对真实育儿经历的不满？就像我们心里曾有一丝期待，认为剪个“瑞秋”发型可能让自己看起来有一点像詹妮弗·安妮斯顿一样。')
original(d,'pregnant',
 'There are also stories about newly adoptive — and newly single — mom Sandra Bullock, as well as the usual “Jennifer Aniston is pregnant” news.',
 '还有关于刚成为养母、也刚恢复单身的桑德拉·布洛克的报道，以及惯常的“詹妮弗·安妮斯顿怀孕了”之类的消息。')
for row in [
 ('in-retrospect','In retrospect, raising a child brought her great happiness.','回想起来，养育孩子给她带来了很大的幸福。','In retrospect'),
 ('permanent','The family is looking for a permanent home.','这个家庭正在寻找一个长期固定的住所。','permanent'),
 ('gossip','She prefers serious reporting to celebrity gossip.','比起明星八卦，她更喜欢严肃的新闻报道。','gossip'),
 ('entertaining','The television show was entertaining but not very realistic.','这档电视节目很有趣，却不太真实。','entertaining'),
 ('be-exposed-to','Public figures are often exposed to criticism.','公众人物经常面临批评。','exposed to'),
 ('compensatory','The company offered compensatory payments to affected customers.','公司向受影响的顾客提供了补偿性款项。','compensatory'),
 ('intensify','Unrealistic expectations can intensify dissatisfaction with everyday life.','不切实际的期望可能加剧人们对日常生活的不满。','intensify'),
 ('highly-valued','Honesty is highly valued by the team.','这个团队非常重视诚实。','highly valued'),
]: supplement(d,*row)
change(d,'past-tense-condition',meaning='一种“过去时”的状态；文中指回顾过去才体会到的幸福',note='past-tense 修饰 condition“状态”。Senior 在此重新界定幸福，并不是建议所有人都应该生孩子。')
change(d,'soul-crushingly-hard',meaning='艰难得令人身心俱疲、几乎崩溃')
change(d,'dampen',meaning='减弱，抑制；使低落',note='dampen 本身表示“减弱、抑制”；dampen our moods 整个搭配才是“使我们的情绪低落”。')
change(d,'subconscious',note='subconscious＝潜意识的。必须保留 wonder if … aren’t …：“是不是正在……”是一种试探性的反问，不是断言这些形象没有影响。')
change(d,'permanent',note='permanent＝永久的、长期固定的。原题A把现象概括为“永久的八卦来源”，没有抓住整段对生育的社会推崇；不要只凭 every week 判答案。')
change(d,'gossip',note='gossip＝八卦、闲话。原题A是干扰项；词义例句与原文结论分开，不把“明星妈妈是永久八卦来源”当作已证实的事实。')
change(d,'entertaining',note='entertaining＝有趣的、令人愉快的。原文并未评价明星怀孕新闻很有趣；第37题C是干扰项。')
change(d,'intensify',note='intensify＝加剧、增强。原题C把导致不满的因素偷换为生孩子本身；全文讨论的是理想化形象可能造成的影响。')
pairs(d, '''
insightful | insightful, provocative magazine cover story | 有见地、引人争议的杂志封面文章
provocative | provocative magazine cover story | 引人争议的杂志封面文章
chatter | arousing much chatter | 引发大量议论
fulfilling | a completely fulfilling, life-enriching experience | 一种完全令人满足、丰富人生的体验
past-tense-condition | a past-tense condition | 一种属于“过去时”的状态
soul-crushingly-hard | can be soul-crushingly hard | 可能艰难到令人身心俱疲
dampen | dampen our moods | 使我们的情绪低落
gratification | intense gratification and delight | 强烈的满足感和快乐
delight | gratification and delight | 满足感和快乐
madonna-and-child | Madonna-and-child image | “圣母与圣婴”式母子形象
newsstand | smiling on the newsstands | 在报摊上的杂志中面带笑容
persistently | persistently celebrates procreation | 持续颂扬生育
celebrate | celebrates procreation | 颂扬生育
procreation | celebrates procreation | 颂扬生育
equivalent-to | is equivalent to admitting | 等同于承认
regret | the regrets of parents | 有孩子者的后悔
provoke | are provoked to wonder | 被促使去怀疑
misery | their misery | 他们的痛苦
hugely | hugely unrealistic | 极其不现实
dumb | dumb enough to want children just because | 傻到仅仅因为……就想要孩子
glamorous | make it look so glamorous | 把它呈现得如此光鲜迷人
haircut | a baby is not a haircut | 生孩子不是换个发型
subconscious | in some small, subconscious way | 以某种轻微而潜意识的方式
in-retrospect | In retrospect | 回想起来
permanent | a permanent home | 一个长期固定的住所
gossip | celebrity gossip | 明星八卦
pregnant | Jennifer Aniston is pregnant | 詹妮弗·安妮斯顿怀孕了（报道中的说法）
entertaining | was entertaining but not very realistic | 很有趣却不太真实
folk | unhappy childless folks | 不幸福的无子女者
be-exposed-to | exposed to criticism | 面临批评
compensatory | compensatory payments | 补偿性款项
intensify | intensify dissatisfaction | 加剧不满
highly-valued | is highly valued by the team | 受到团队的高度重视
''')

# 2012 English I Text 1: peer pressure versus externally engineered intervention.
d='2012-e1-text1'
original(d,'peer-pressure whispered',
 'That whispered message, half invitation and half forcing, is what most of us think of when we hear the words peer pressure.',
 '那种低声说出、半是邀请半是强迫的话，就是我们大多数人在听到“同伴压力”一词时所想到的情景。')
original(d,'social-cure group-dynamics',
 'But in her new book Join the Club, Tina Rosenberg contends that peer pressure can also be a positive force through what she calls the social cure, in which organizations and officials use the power of group dynamics to help individuals improve their lives and possibly the world.',
 '但蒂娜·罗森伯格在新书《加入俱乐部》中主张，同伴压力也能通过她所谓的“社会疗法”成为积极力量：组织和官员利用群体互动的力量帮助个人改善生活，甚至可能改善世界。')
original(d,'recipient state-sponsored-antismoking cigarette',
 'Rosenberg, the recipient of a Pulitzer Prize, offers a host of examples of the social cure in action: In South Carolina, a state-sponsored antismoking program called Rage Against the Haze sets out to make cigarettes uncool.',
 '普利策奖获得者罗森伯格提供了许多社会疗法付诸实践的例子：在南卡罗来纳州，一个由州政府资助、名为Rage Against the Haze的反吸烟项目，致力于让抽烟变得不酷。')
original(d,'recruit',
 'In South Africa, an HIV-prevention initiative known as loveLife recruits young people to promote safe sex among their peers.',
 '在南非，一个名为loveLife的艾滋病病毒预防项目招募年轻人，让他们向同龄人宣传安全性行为。',marked=('recruit',))
original(d,'perceptive','The idea seems promising, and Rosenberg is a perceptive observer.',
 '这个想法似乎很有前景，而罗森伯格也是一位观察敏锐的人。')
original(d,'critique lameness spot-on mobilize flawed',
 'Her critique of the lameness of many public-health campaigns is spot-on: they fail to mobilize peer pressure for healthy habits, and they demonstrate a seriously flawed understanding of psychology.',
 '她对许多公共卫生宣传乏力的批评十分准确：这些宣传未能调动同伴压力来培养健康习惯，而且显示出对心理学的理解存在严重缺陷。')
original(d,'billboard fit-in',
 '“Dare to be different, please don’t smoke!” pleads one billboard campaign aimed at reducing smoking among teenagers – teenagers, who desire nothing more than fitting in.',
 '一则旨在减少青少年吸烟的大型广告牌宣传恳求道：“敢于与众不同，请不要吸烟！”——可青少年最想要的恰恰是合群。')
original(d,'convincingly ought-to take-a-page-from advocate',
 'Rosenberg argues convincingly that public-health advocates ought to take a page from advertisers, so skilled at applying peer pressure.',
 '罗森伯格有说服力地主张，公共卫生倡导者应向广告商学习，因为后者非常善于运用同伴压力。')
original(d,'persuasive',
 'But on the general effectiveness of the social cure, Rosenberg is less persuasive.',
 '但在论证社会疗法的整体有效性时，罗森伯格就没有那么有说服力了。')
original(d,'irrelevant',
 'Join the Club is filled with too much irrelevant detail and not enough exploration of the social and biological factors that make peer pressure so powerful.',
 '《加入俱乐部》充斥着过多无关细节，却没有充分探究那些使同伴压力如此强大的社会和生物因素。')
original(d,'glaring-flaw',
 'The most glaring flaw of the social cure as it’s presented here is that it doesn’t work very well for very long.',
 '书中所呈现的社会疗法，最明显的缺陷是它难以长时间保持良好效果。')
original(d,'exert-enormous-influence',
 'There’s no doubt that our peer groups exert enormous influence on our behavior.',
 '毫无疑问，我们的同伴群体对我们的行为施加着巨大的影响。')
original(d,'subtle imitate',
 'This is a subtle form of peer pressure: we unconsciously imitate the behavior we see every day.',
 '这是一种不易察觉的同伴压力：我们会无意识地模仿每天看到的行为。',marked=('subtle','imitate'))
original(d,'certain bureaucrat virtuous',
 'Far less certain, however, is how successfully experts and bureaucrats can select our peer groups and steer their activities in virtuous directions.',
 '然而，专家和行政人员究竟能在多大程度上成功地替我们选择同伴群体，并将这些群体的活动引向良性方向，就远没有那么确定了。')
original(d,'troublemaker pair-with',
 'It’s like the teacher who breaks up the troublemakers in the back row by pairing them with better-behaved classmates.',
 '这就像老师把后排的捣蛋学生拆开，分别让他们与表现更好的同学配对一样。')
original(d,'tactic','The tactic never really works.',
 '这种策略实际上从来就没有真正奏效。')
original(d,'insist-on',
 'And that’s the problem with a social cure engineered from the outside: in the real world, as in school, we insist on choosing our own friends.',
 '这正是从外部设计社会疗法的问题所在：在现实世界中，和在学校里一样，我们坚持自己选择朋友。')
for row in [
 ('adequately-probe','The study did not adequately probe the reasons for the change.','这项研究没有充分探究变化的原因。','adequately probe'),
 ('evade','The speaker tried to evade the difficult question.','发言者试图回避这个棘手的问题。','evade'),
 ('imitation','Imitation of friends can influence our everyday habits.','模仿朋友可能影响我们的日常习惯。','Imitation'),
 ('emerge-as','Peer pressure can emerge as a force for change.','同伴压力可以表现为促成改变的一股力量。','emerge as'),
 ('stimulus','The project acted as a stimulus to cooperation.','这个项目起到了促进合作的作用。','stimulus'),
 ('obstacle','A lack of trust is an obstacle to cooperation.','缺乏信任是合作的障碍。','obstacle'),
 ('undesirable','The campaign aims to reduce undesirable behaviors.','这场宣传活动旨在减少不良行为。','undesirable'),
 ('commercial','Commercial advertisers try to attract potential customers.','商业广告商努力吸引潜在顾客。','Commercial advertisers'),
 ('desirable','A lasting improvement would be a desirable outcome.','持久的改善会是一个理想的结果。','desirable'),
 ('profound','Friends can have a profound influence on our behavior.','朋友可能对我们的行为产生深远的影响。','profound'),
 ('questionable','The long-term effectiveness of the plan is questionable.','这项计划的长期有效性值得怀疑。','questionable'),
]: supplement(d,*row)
change(d,'persuasive',meaning='有说服力的，令人信服的',mark='persuasive',note='persuasive 本身是肯定义“有说服力的”。原句的 less persuasive 才是“没那么有说服力”，不能把 less 的意思塞进单词释义。')
change(d,'certain',meaning='确定的，确信的；某些（置于名词前）',mark='certain',note='本句 certain 取“确定的”义；far less certain 整体才是“远没有那么确定”。倒装句把不确定性前置，并不是肯定专家能成功。')
change(d,'cigarette',term='cigarette',form='原文复数：cigarettes')
change(d,'bureaucrat',term='bureaucrat',form='原文复数：bureaucrats；与 bureaucracy 对照')
change(d,'troublemaker',term='troublemaker',form='原文复数：troublemakers')
change(d,'advocate',term='advocate',form='原文复数：public-health advocates；此处作名词')
change(d,'commercial',mark='Commercial advertisers')
change(d,'pair-with',term='pair A with B',form='原文：pairing them with better-behaved classmates',note='pair A with B＝把A与B配成一对；A、B为占位符。原句 them 指捣蛋学生，B是表现更好的同学。',spokenText='pair someone with someone')
change(d,'adequately-probe',note='adequately probe＝充分探究；对应原文 not enough exploration。原题问书的论证不足，不是直接问社会疗法能否产生持久效果。')
change(d,'virtuous',note='virtuous 与 virtue 相关，指有道德的、良性的。原句将 steer their activities 放在“不确定能否成功”的从句中，不能摘出来变成肯定结论。')
change(d,'stimulus',note='stimulus 是名词“刺激物、促进因素”，与动词 stimulate 相关；不要把它当作动词。')
pairs(d, '''
peer-pressure | peer pressure | 同伴压力
group-dynamics | the power of group dynamics | 群体互动的力量
social-cure | the social cure | 这种社会疗法
whispered | That whispered message | 那句低声说出的话
recipient | the recipient of a Pulitzer Prize | 普利策奖获得者
state-sponsored-antismoking | a state-sponsored antismoking program | 一个州政府资助的反吸烟项目
cigarette | make cigarettes uncool | 让抽烟变得不酷
recruit | recruits young people | 招募年轻人
perceptive | a perceptive observer | 一位观察敏锐的人
critique | Her critique of the lameness | 她对宣传乏力的批评
lameness | the lameness of many public-health campaigns | 许多公共卫生宣传的乏力
spot-on | is spot-on | 非常准确
mobilize | mobilize peer pressure for healthy habits | 调动同伴压力来培养健康习惯
flawed | a seriously flawed understanding of psychology | 对心理学存在严重缺陷的理解
billboard | one billboard campaign | 一项广告牌宣传
convincingly | argues convincingly | 有说服力地论证
ought-to | ought to take a page from advertisers | 应该向广告商学习
take-a-page-from | take a page from advertisers | 借鉴广告商的做法
fit-in | desire nothing more than fitting in | 最渴望合群
persuasive | less persuasive | 没那么有说服力
irrelevant | too much irrelevant detail | 太多不相关的细节
adequately-probe | did not adequately probe | 未能充分探究
evade | evade the difficult question | 回避棘手的问题
glaring-flaw | The most glaring flaw | 最明显的缺陷
exert-enormous-influence | exert enormous influence on our behavior | 对我们的行为施加巨大影响
subtle | a subtle form of peer pressure | 一种不易察觉的同伴压力
imitate | unconsciously imitate the behavior | 无意识地模仿行为
imitation | Imitation of friends | 对朋友的模仿
certain | Far less certain | 远没有那么确定
bureaucrat | experts and bureaucrats | 专家和行政人员
virtuous | in virtuous directions | 朝良性的方向
troublemaker | the troublemakers in the back row | 后排的捣蛋学生
pair-with | pairing them with better-behaved classmates | 将他们与表现更好的同学配对
tactic | The tactic never really works | 这种策略从来没有真正奏效
insist-on | insist on choosing our own friends | 坚持自己选择朋友
emerge-as | emerge as a force for change | 表现为促成改变的一股力量
stimulus | a stimulus to cooperation | 促进合作的因素
obstacle | an obstacle to cooperation | 合作的障碍
undesirable | undesirable behaviors | 不良行为
advocate | public-health advocates | 公共卫生倡导者
commercial | Commercial advertisers | 商业广告商
desirable | a desirable outcome | 一个理想的结果
profound | a profound influence | 深远的影响
questionable | effectiveness of the plan is questionable | 计划的有效性值得怀疑
''')


def blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def build():
    catalog_path = ROOT/'data/catalog.json'
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    if catalog['version'] == VERSION:
        print('Audit revision already applied; no changes.')
        return {}, None
    if {e['id'] for e in catalog['decks']} != set(BASE_SHAS):
        raise ValueError('Catalog changed since audit; review new decks before applying.')
    outputs, report = {}, {'version':VERSION,'scope':'all published reading decks','decks':[]}
    for entry in catalog['decks']:
        path = ROOT/entry['file']
        data = path.read_bytes()
        if blob_sha(data) != BASE_SHAS[entry['id']]:
            raise ValueError('Concurrent content change: ' + entry['file'])
        before = json.loads(data)
        after = copy.deepcopy(before)
        changes = PATCH[entry['id']]
        if {c['id'] for c in after['cards']} != set(changes):
            raise ValueError('The audit must explicitly cover every card: ' + entry['id'])
        rows=[]
        for old,card in zip(before['cards'],after['cards']):
            card.update(changes[card['id']])
            if card['id'] != old['id'] or card['book'] != old['book']:
                raise ValueError('IDs and source-book records must be preserved.')
            if not card['mark'] or card['mark'] not in card['quote']:
                raise ValueError('Invalid highlight: '+entry['id']+'/'+card['id'])
            if card['collocation'] not in card['quote']:
                raise ValueError('Collocation absent from example: '+entry['id']+'/'+card['id'])
            if len(re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*",card['quote'])) < 4:
                raise ValueError('Example is not a complete sentence: '+card['id'])
            # Do not publish learner-specific mistakes as general content metadata.
            if '错题' in card['kind']:
                card['kind']=card['kind'].replace('错题','题目')
            rows.append({'id':card['id'],'term':card['term'],
                'changedFields':[k for k in card if old.get(k)!=card[k]],
                'exampleType':card['exampleType'],
                'pronunciationChanged':old['term']!=card['term'] or old.get('spokenText')!=card.get('spokenText')})
        entry['updated']='2026-09-27'
        outputs[path]=json.dumps(after,ensure_ascii=False,indent=2)+'\n'
        report['decks'].append({'id':entry['id'],'count':len(rows),'cards':rows})
    catalog['version']=VERSION
    outputs[catalog_path]=json.dumps(catalog,ensure_ascii=False,indent=2)+'\n'
    report['totalCards']=sum(d['count'] for d in report['decks'])
    report['idChanges']=0
    report['bookReferenceChanges']=0
    report['pronunciationChanges']=sum(c['pronunciationChanged'] for d in report['decks'] for c in d['cards'])
    report['supplementalExamples']=sum(c['exampleType']=='supplemental' for d in report['decks'] for c in d['cards'])
    report['originalExamples']=report['totalCards']-report['supplementalExamples']
    outputs[ROOT/'docs/content-audit-20260927.json']=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    return outputs, report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='Write audited changes; otherwise validate only.')
    args=parser.parse_args()
    outputs,report=build()
    if args.apply:
        for path,text in outputs.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text,encoding='utf-8')
    if report:
        print(json.dumps({k:v for k,v in report.items() if k!='decks'},ensure_ascii=False))
        print('Applied.' if args.apply else 'Validated only; pass --apply to write.')

if __name__=='__main__':main()
