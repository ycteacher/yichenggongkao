# -*- coding: utf-8 -*-
"""四类卷各10套押题卷：从全库质量过滤池组卷。
组成（129题）：常识20（含政治理论5）、言语40、数量15、判断推理29＋图推10（全中等难度）、资料15。
约束：卷内题干唯一、全卷答案分布每字母≈25%（±6）、图推仅diff=2、跨新卷同一题最多复用3次、
优先选用历史卷引用次数少的题。输出：out/papers_draft.json + 校验报告。"""
import json, os, re, random, glob
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
ASSETS = os.path.join(ROOT, 'assets')
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

def norm(s):
    return re.sub(r'[\s，。、；：？！“”"\'（）()\[\]《》<>·,.;:?!]', '', str(s))

def load_all():
    dec = json.JSONDecoder()
    qs = []
    for f in sorted(glob.glob(os.path.join(ASSETS, 'qk-*.js'))) + \
             sorted(glob.glob(os.path.join(ASSETS, 'cs-bank-*.js'))):
        t = open(f, encoding='utf-8').read()
        for m in re.finditer(r'\.push\(', t):
            try:
                val, _ = dec.raw_decode(t, m.end())
            except ValueError:
                continue
            for q in (val if isinstance(val, list) else [val]):
                if isinstance(q, dict) and q.get('id'):
                    qs.append(q)
    return qs

def base_ok(q):
    try:
        if not q.get('id') or q.get('module') in ('shenlun', 'zongying'): return False
        if not isinstance(q.get('options'), list) or len(q['options']) != 4: return False
        if not isinstance(q.get('answer'), int) or not 0 <= q['answer'] <= 3: return False
        if len(str(q.get('prompt', ''))) < 8: return False
        if len(str(q.get('explanation', ''))) < 10: return False
        if any(str(o).strip().startswith('．') for o in q['options']): return False
        if len(set(norm(o) for o in q['options'])) < 4: return False
        return True
    except Exception:
        return False

def main():
    random.seed(20261124)
    allq = load_all()
    print('全库题数:', len(allq))
    # 历史卷引用计数
    t = open(os.path.join(ASSETS, '..', 'assets', 'index-b34.js'), encoding='utf-8').read() \
        if False else open(os.path.join(ROOT, 'assets', 'index-b34.js'), encoding='utf-8').read()
    hist = Counter()
    for m in re.finditer(r'"qids":\[([^\]]*)\]', t):
        for qid in re.findall(r'"([^"]+)"', m.group(1)):
            hist[qid] += 1
    # 质量池
    pools = defaultdict(list)
    for q in allq:
        if not base_ok(q): continue
        mod = q['module']
        if mod == 'tuitui' and q.get('diff') != 2: continue      # 图形题只取中等难度
        if mod == 'ziliao' and not (q.get('fig') or q.get('optFig')): continue  # 资料分析须有图表材料
        pools[mod].append(q)
    for k, v in pools.items(): print('池:', k, len(v))
    # 组卷
    CATS = [
        ('gk', '27国考行测押题卷', '对标27国考大纲与最新命题趋势 · 考前必刷'),
        ('sk', '27省考行测押题卷', '对标27省考联考命题趋势 · 考前必刷'),
        ('sy', '事业单位联考押题卷', '对标事业单位联考职测命题趋势 · 考前必刷'),
        ('cc', '考前冲刺押题卷', '全模块混合实战 · 考前查漏补缺'),
    ]
    used = Counter()          # 新卷内复用计数
    used_keys = set()         # 全局题干键（跨新卷防重复？允许复用3次，用计数）
    key_count = Counter()
    papers = []
    for ck, cname, cnote in CATS:
        for i in range(10):
            paper = {'slots': [('changshi', 15), ('zhengzhi', 5), ('yanyu', 40),
                               ('shuliang', 15), ('panduan', 29), ('tuitui', 10), ('ziliao', 15)],
                     'name': f'{cname}（{"终极版" if i == 0 else "第%d套" % i}）' if False else '',
                     }
            papers.append(paper)
    # 实际挑选
    result = []
    for ck, cname, cnote in CATS:
        for i in range(10):
            qs, dist = [], [0, 0, 0, 0]
            keys_in_paper = set()
            def pick(mod, n):
                got = 0
                cand = pools[mod][:]
                random.shuffle(cand)
                cand.sort(key=lambda q: (used[q['id']], hist.get(q['id'], 0), random.random()))
                for q in cand:
                    if got >= n: break
                    if used[q['id']] >= 3: continue
                    k = (norm(q['prompt']) + '|' + norm(q.get('fig') or ''))
                    if k in keys_in_paper or key_count[k] >= 3: continue
                    a = q['answer']
                    if dist[a] >= 34: continue   # 单卷单字母上限（129题约32均值）
                    qs.append(q); used[q['id']] += 1; key_count[k] += 1
                    keys_in_paper.add(k); dist[a] += 1; got += 1
                return got
            plan = [('changshi', 15), ('zhengzhi', 5), ('yanyu', 40),
                    ('shuliang', 15), ('panduan', 29), ('tuitui', 10), ('ziliao', 15)]
            shortage = []
            for mod, n in plan:
                g = pick(mod, n)
                if g < n: shortage.append((mod, n - g))
            # 缺口用同池其他题补（放宽单字母上限）
            if shortage:
                for mod, n in shortage:
                    cand = pools[mod][:]; random.shuffle(cand)
                    cand.sort(key=lambda q: (used[q['id']], hist.get(q['id'], 0)))
                    need = n
                    for q in cand:
                        if need <= 0: break
                        if used[q['id']] >= 3: continue
                        k = (norm(q['prompt']) + '|' + norm(q.get('fig') or ''))
                        if k in keys_in_paper or key_count[k] >= 3: continue
                        qs.append(q); used[q['id']] += 1; key_count[k] += 1
                        keys_in_paper.add(k); dist[q['answer']] += 1; need -= 1
                    if need: print(f'警告: {cname}第{i+1}套 {mod} 缺 {need}')
            random.shuffle(qs)
            tag = {'gk': '国考卷', 'sk': '省考卷', 'sy': '事业编卷', 'cc': '冲刺卷'}[ck]
            name = f"{cname}（终极版）" if i == 0 else f"{cname}（第{i+1}套）"
            note = ('按今年命题趋势命制 · 此版为终极版，具有极大的参考价值 · ' if i == 0 else '按今年命题趋势命制 · ') + cnote
            result.append({'id': f'pp-yt-{ck}-{i+1:02d}', 'name': name, 'tag': tag,
                           'note': note, 'qids': [q['id'] for q in qs]})
            print(f'{name}: {len(qs)}题 答案分布{dist}')
    json.dump(result, open(os.path.join(OUT, 'papers_draft.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('共', len(result), '套，已写 out/papers_draft.json')

if __name__ == '__main__':
    main()
