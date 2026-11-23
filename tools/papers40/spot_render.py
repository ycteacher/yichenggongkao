# -*- coding: utf-8 -*-
"""40套新卷抽题渲染校验（修正版）：
- 图推(tt-)：SVG选项，复用 tt2000/pixel_check.check_batch（墨迹差异率≥0.15）。
- 文字题：正常字号渲染题干+选项，检查各选项格非空白（pixel_check 的 body font-size:0 口径会使文字题全判空白，不适用）。
每套抽 3 图推 + 2 文字题。"""
import json, os, re, glob, random, sys, itertools
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tt2000')))
from playwright.sync_api import sync_playwright
from pixel_check import check_batch
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
papers = json.load(open(os.path.join(HERE, 'out', 'papers_draft.json'), encoding='utf-8'))

# 载入全库
dec = json.JSONDecoder()
bank = {}
for f in glob.glob(os.path.join(ROOT, 'assets', 'qk-*.js')) + glob.glob(os.path.join(ROOT, 'assets', 'cs-bank-*.js')):
    t = open(f, encoding='utf-8').read()
    for m in re.finditer(r'\.push\(', t):
        try:
            val, _ = dec.raw_decode(t, m.end())
        except ValueError:
            continue
        for q in (val if isinstance(val, list) else [val]):
            if isinstance(q, dict) and q.get('id'):
                bank[q['id']] = q

random.seed(77)
tt_sample, text_sample = [], []
for p in papers:
    tt = [q for q in p['qids'] if q.startswith('tt-')]
    others = [q for q in p['qids'] if not q.startswith('tt-')]
    tt_sample.extend(bank[q] for q in random.sample(tt, min(3, len(tt))))
    text_sample.extend(bank[q] for q in random.sample(others, 2))
print('抽渲染样本: 图推', len(tt_sample), '题 + 文字', len(text_sample), '题')

fails = []

# ---- 图推：SVG 像素校验 ----
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/local/bin/chromium',
                                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--disable-software-rasterizer'])
    page = browser.new_page(viewport={'width': 80 * 10 + 40, 'height': 1200})
    B = 100
    for i in range(0, len(tt_sample), B):
        sub = tt_sample[i:i + B]
        for f in check_batch(page, sub, 80):
            fails.append(('tt', tt_sample[i + f['qi']]['id'], f))
            print('图推不合格:', tt_sample[i + f['qi']]['id'], f)
    page.close()

    # ---- 文字题：正常字号渲染，选项格非空白 + 选项文本互异 ----
    page = browser.new_page(viewport={'width': 300 * 4 + 40, 'height': 1200})
    CELL, COLS = 300, 4
    def text_html(qs):
        parts = []
        for q in qs:
            for o in q['options']:
                parts.append(f'<div style="display:inline-block;width:{CELL}px;height:{CELL}px;box-sizing:border-box;'
                             f'padding:8px;font-size:16px;line-height:1.4;color:#000;overflow:hidden;vertical-align:top">{o}</div>')
        return '<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{margin:0;background:#fff;font-family:sans-serif}</style></head><body>' + ''.join(parts) + '</body></html>'

    shot = os.path.join(HERE, 'out', '.tmp_text_shot.png')
    for i in range(0, len(text_sample), 40):
        sub = text_sample[i:i + 40]
        for attempt in range(4):
            page.set_content(text_html(sub))
            page.wait_for_timeout(300)
            page.screenshot(path=shot, full_page=True)
            img = Image.open(shot).convert('RGB')
            blanks = []
            for bi in range(len(sub)):
                for oi in range(4):
                    ci = bi * 4 + oi
                    col, row = ci % COLS, ci // COLS
                    c = np.asarray(img.crop((col * CELL, row * CELL, (col + 1) * CELL, (row + 1) * CELL)), dtype=np.uint8)
                    c = c[5:-5, 5:-5]
                    if int(np.count_nonzero(np.any(c != 255, axis=2))) == 0:
                        blanks.append((bi, oi))
            if not blanks or attempt == 3:
                break
            page.wait_for_timeout(1500)
        for bi, oi in blanks:
            fails.append(('text', sub[bi]['id'], {'opt': oi, 'pair': 'blank'}))
            print('文字题不合格(选项空白):', sub[bi]['id'], '选项', oi)
        # 选项文本互异
        for q in sub:
            if len(set(str(o).strip() for o in q['options'])) < 4:
                fails.append(('text', q['id'], {'pair': 'dup-options'}))
                print('文字题不合格(选项重复):', q['id'])
    browser.close()

ids = sorted({x[1] for x in fails})
print('渲染校验:', '全部通过' if not fails else f'{len(fails)}项不合格，涉及{len(ids)}题: {ids[:20]}')
