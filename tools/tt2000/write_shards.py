# -*- coding: utf-8 -*-
"""把 out/questions.json 写成上架分片 qk-tuitui-82.js 起，id tt-20001~22000。"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
ASSETS = os.path.join(ROOT, 'assets')
OUT = os.path.join(HERE, 'out', 'questions.json')

qs = json.load(open(OUT, encoding='utf-8'))
assert len(qs) == 2000

# id 唯一性预检：与现有 idmap 全量核对
idmap = json.load(open(os.path.join(ASSETS, 'qbank-idmap.json'), encoding='utf-8'))
new_ids = ['tt-%05d' % (20001 + i) for i in range(2000)]
clash = [i for i in new_ids if i in idmap]
assert not clash, f'id冲突: {clash[:5]}'
assert len(set(new_ids)) == 2000

PER = 400
for s in range(5):
    chunk = qs[s * PER:(s + 1) * PER]
    items = []
    for gi, q in enumerate(chunk):
        figs = q['figs'] if isinstance(q['figs'], list) else [q['figs']]
        items.append({
            'id': new_ids[s * PER + gi],
            'module': 'tuitui',
            'prompt': q['prompt'],
            'fig': ''.join(figs),
            'options': q['options'],
            'answer': q['answer'],
            'explanation': q['explanation'],
            'diff': q['diff'],
            '__sub': q['__sub'],
        })
    name = 'qk-tuitui-%02d' % (82 + s)
    payload = json.dumps(items, ensure_ascii=False, separators=(',', ':'))
    text = 'window.YC_MORE_QBANKS=window.YC_MORE_QBANKS||[];window.YC_MORE_QBANKS.push(' + payload + ');'
    path = os.path.join(ASSETS, name + '.js')
    open(path, 'w', encoding='utf-8', newline='').write(text)
    print(name, len(items), '题,', len(text.encode('utf-8')), 'bytes')

print('id范围:', new_ids[0], '~', new_ids[-1])
