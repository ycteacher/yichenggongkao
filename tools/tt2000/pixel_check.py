# -*- coding: utf-8 -*-
"""像素校验（80px手机口径全量 + 140/200px抽验）。
双口径：
  full  —— 整幅像素差异率（含白底，作参考）
  ink   —— 墨迹掩码 Jaccard 距离（图形覆盖区差异率，主门槛 ≥15%）
方案：分批整页截图，Pillow 切片后逐对比较。"""
import json, os, itertools, random, time
from PIL import Image
from playwright.sync_api import sync_playwright

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
CHROME = '/usr/local/bin/chromium'
CELL = {'80': 80, '140': 140, '200': 200}
COLS = 10
MAX_H = 2400

def batch_for(size):
    rows = MAX_H // CELL[str(size)]
    return max(1, (rows * COLS) // 4)

PAGE_TMPL = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:#fff;font-family:sans-serif;font-size:0;line-height:0}}
.opt{{display:inline-block;overflow:hidden;vertical-align:top}}
</style></head><body>{body}</body></html>"""

def page_html(questions, size):
    s = CELL[str(size)]
    parts = []
    for q in questions:
        for svg in q['options']:
            parts.append(f'<div class="opt" style="width:{s}px;height:{s}px">{svg}</div>')
    return PAGE_TMPL.format(s=s, body=''.join(parts))

import numpy as np

BORDER = 5  # 统一外框为渲染边框，比较时排除四边5px

def metrics(ca, cb):
    a = np.asarray(ca, dtype=np.uint8)
    b = np.asarray(cb, dtype=np.uint8)
    if BORDER:
        a = a[BORDER:-BORDER, BORDER:-BORDER]
        b = b[BORDER:-BORDER, BORDER:-BORDER]
    a = a.reshape(-1, 3)
    b = b.reshape(-1, 3)
    n = a.shape[0]
    ia = ~np.all(a == 255, axis=1)
    ib = ~np.all(b == 255, axis=1)
    full = float(np.count_nonzero(np.any(a != b, axis=1))) / n
    uni = np.count_nonzero(ia | ib)
    ink = float(np.count_nonzero(ia ^ ib)) / uni if uni else 0.0
    return full, ink

def _cell_ink(cell):
    """格内墨迹像素数（去5px边框后）。合法选项必有内容，全白=渲染故障。"""
    a = np.asarray(cell, dtype=np.uint8)
    if BORDER:
        a = a[BORDER:-BORDER, BORDER:-BORDER]
    return int(np.count_nonzero(np.any(a != 255, axis=2)))

def check_batch(page, questions, size):
    fails = []
    s = CELL[str(size)]
    shot = os.path.join(OUT_DIR, f'.tmp_shot_{size}.png')
    n_cells = len(questions) * 4
    cells_all = None
    for attempt in range(4):
        page.set_content(page_html(questions, size))
        page.wait_for_timeout(300)
        try:
            page.screenshot(path=shot, full_page=True)
            img = Image.open(shot).convert('RGB')
        except Exception as e:
            if attempt == 3:
                raise
            print(f'  [retry] screenshot failed ({e}), retrying', flush=True)
            page.wait_for_timeout(2000)
            continue
        cells_all = []
        blanks = []
        for ci in range(n_cells):
            col = ci % COLS
            row = ci // COLS
            c = img.crop((col * s, row * s, (col + 1) * s, (row + 1) * s))
            cells_all.append(c)
            if _cell_ink(c) == 0:
                blanks.append(ci)
        if blanks:
            if attempt == 3:
                # 持续空白＝结构缺陷（空SVG）或环境异常：判为不合格，交由修复环节重建
                print(f'  [blank] {len(blanks)} cells persist as blank, marking as fails', flush=True)
                break
            print(f'  [glitch] {len(blanks)} blank cells, retry {attempt + 1}', flush=True)
            page.wait_for_timeout(1500)
            continue
        break
    img_cells = cells_all
    blank_qis = set(ci // 4 for ci in blanks) if blanks else set()
    for bi, q in enumerate(questions):
        if bi in blank_qis:
            fails.append({'qi': bi, 'pair': 'blank', 'ink': 0.0, 'full': 0.0})
            continue
        cells = img_cells[bi * 4:bi * 4 + 4]
        for a, b in itertools.combinations(range(4), 2):
            full, ink = metrics(cells[a], cells[b])
            if ink < 0.15:
                fails.append({'qi': bi, 'pair': f'{a}-{b}', 'ink': round(ink, 3), 'full': round(full, 3)})
    os.remove(shot)
    return fails

def run(questions, size, label):
    all_fails = []
    batch = batch_for(size)
    with sync_playwright() as p:
        for start in range(0, len(questions), batch):
            sub_qs = questions[start:start + batch]
            fails = None
            for attempt in range(5):
                browser = p.chromium.launch(executable_path=CHROME, args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--disable-software-rasterizer'])
                try:
                    page = browser.new_page(viewport={'width': CELL[str(size)] * COLS + 40, 'height': 1200})
                    fails = check_batch(page, sub_qs, size)
                    break
                except Exception as e:
                    if attempt == 4:
                        raise
                    print(f'  [retry] batch@{start} failed ({type(e).__name__}), relaunching browser', flush=True)
                    time.sleep(2)
                finally:
                    try:
                        browser.close()
                    except Exception:
                        pass
            for f in fails:
                f['gi'] = start + f['qi']
            all_fails.extend(fails)
            print(f'  [{label}] {start + len(sub_qs)}/{len(questions)} 不合格+{len(fails)}', flush=True)
    return all_fails

def main():
    questions = json.load(open(os.path.join(OUT_DIR, 'questions.json'), encoding='utf-8'))
    print(f'载入 {len(questions)} 题（门槛：墨迹差异率≥0.15）', flush=True)

    f80 = run(questions, 80, '80px全量')
    print(f'80px 全量: 不合格 {len(f80)}/{len(questions)*6} 对')
    for f in f80[:15]:
        print('  ', f)

    rng = random.Random(77)
    by_diff = {}
    for i, q in enumerate(questions):
        by_diff.setdefault(q['diff'], []).append(i)
    sample_idx = []
    for d, idxs in by_diff.items():
        sample_idx.extend(rng.sample(idxs, min(40, len(idxs))))
    sub = [questions[i] for i in sample_idx]
    spot_fails = []
    for size in (140, 200):
        fs = run(sub, size, f'{size}px抽验')
        for f in fs:
            f['size'] = size
        spot_fails.extend(fs)
    print(f'140/200px 抽验({len(sub)}题×2): 不合格 {len(spot_fails)}')
    for f in spot_fails[:15]:
        print('  ', f)

    json.dump({'full80_fails': len(f80), 'spot_fails': len(spot_fails), 'sample_n': len(sub),
               'fails80': f80, 'fails_spot': spot_fails},
              open(os.path.join(OUT_DIR, 'pixel_report.json'), 'w'))
    print('像素校验完成' if not f80 and not spot_fails else '存在不合格项，需修复')

if __name__ == '__main__':
    main()
