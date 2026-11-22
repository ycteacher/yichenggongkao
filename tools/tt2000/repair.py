# -*- coding: utf-8 -*-
"""像素不合格题修复循环：
逐题重新生成（同族同难度）→ 验算 → 查重 → 像素校验，直到全部通过。"""
import json, os, sys, random, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate as G
from gen_lib import struct_key, fig_in_frame, parse_svg
from pixel_check import check_batch, metrics
from playwright.sync_api import sync_playwright

def svg_content_ok(svg):
    """选项/图形必须至少含1个内容元素（排除外框）。"""
    try:
        return len(parse_svg(svg)) >= 1
    except Exception:
        return False

def structurally_broken(q):
    """结构缺陷：任何选项为空，或非末位题干图为空。"""
    if not all(svg_content_ok(o) for o in q['options']):
        return True
    figs = q['figs'] if isinstance(q['figs'], list) else [q['figs']]
    for k, f in enumerate(figs):
        if k < len(figs) - 1 and not svg_content_ok(f):
            return True
    return False

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
CHROME = '/usr/local/bin/chromium'

LAUNCH_ARGS = ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--disable-software-rasterizer']

class PageHolder:
    """带自愈的页面：渲染故障（空白格持续）时重建页面重试，全部走批量渲染口径。"""
    def __init__(self, browser):
        self.browser = browser
        self.page = browser.new_page(viewport={'width': 80 * 10 + 40, 'height': 1200})

    def _vp(self, size):
        from pixel_check import CELL, COLS
        self.page.set_viewport_size({'width': CELL[str(size)] * COLS + 40, 'height': 1200})

    def check(self, qs, size):
        try:
            self._vp(size)
            return check_batch(self.page, qs, size)
        except Exception:
            try:
                self.page.close()
            except Exception:
                pass
            from pixel_check import CELL, COLS
            self.page = self.browser.new_page(viewport={'width': CELL[str(size)] * COLS + 40, 'height': 1200})
            return check_batch(self.page, qs, size)

def failing_indices(questions, browser):
    """返回不合格题号集合（80px口径，墨迹差异率<0.15）。"""
    page = browser.new_page(viewport={'width': 80 * 10 + 40, 'height': 1200})
    fails = set()
    batch = 180
    for start in range(0, len(questions), batch):
        sub = questions[start:start + batch]
        for f in check_batch(page, sub, 80):
            fails.add(start + f['qi'])
    page.close()
    return fails

def main():
    questions = json.load(open(os.path.join(OUT_DIR, 'questions.json'), encoding='utf-8'))
    print('加载全库查重键...')
    existing_keys = G.load_existing_keys()
    rng = random.Random(20261123)

    # 初始不合格清单：像素报告（80px全量 + 140/200px抽验）∪ 结构缺陷（空选项等）
    report_path = os.path.join(OUT_DIR, 'pixel_report.json')
    if os.path.exists(report_path):
        rep = json.load(open(report_path))
        fails = set(f['gi'] for f in rep['fails80']) | set(f['gi'] for f in rep['fails_spot'])
        print(f'从报告载入像素不合格题数: {len(fails)}', flush=True)
    else:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME, args=LAUNCH_ARGS)
            fails = failing_indices(questions, browser)
            browser.close()
        print(f'初始像素不合格题数: {len(fails)}', flush=True)
    broken = set(i for i, q in enumerate(questions) if structurally_broken(q))
    print(f'结构缺陷题数: {len(broken)}', flush=True)
    fails |= broken

    # 抽验不合格（140/200px）映射回全局题号：抽样逻辑须与 pixel_check 完全一致（按 diff 首次出现顺序分组）
    if rep.get('fails_spot'):
        rng2 = random.Random(77)
        by_diff = {}
        for i, q in enumerate(questions):
            by_diff.setdefault(q['diff'], []).append(i)
        sample_idx = []
        for d, idxs in by_diff.items():
            sample_idx.extend(rng2.sample(idxs, min(40, len(idxs))))
        spot_gis = {sample_idx[f['gi']] for f in rep['fails_spot'] if f['gi'] < len(sample_idx)}
        print(f'抽验不合格映射全局题号: {sorted(spot_gis)}', flush=True)
        fails |= spot_gis

    # 当前题目的查重状态
    seen_keys = set()
    param_count = {}
    def pk_of(q):
        return (q['family'], json.dumps(q['params'], ensure_ascii=False, sort_keys=True, default=str))
    for q in questions:
        key = struct_key(q['prompt'], q['figs'] if isinstance(q['figs'], list) else [q['figs']])
        seen_keys.add(key)
        pk = pk_of(q)
        param_count[pk] = param_count.get(pk, 0) + 1

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=LAUNCH_ARGS)
        pc = PageHolder(browser)

        round_no = 0
        while fails and round_no < 8:
            round_no += 1
            still = set()
            for gi in sorted(fails):
                old = questions[gi]
                fam, diff = old['family'], old['diff']
                # 记住原答案槽位，替换后保持答案分布
                target = old['answer']
                replaced = False
                attempt = 0
                while attempt < 120 and not replaced:
                    # 批量生成逻辑合格的候选，一次渲染校验 8 题
                    cands = []
                    while len(cands) < 8 and attempt < 120:
                        attempt += 1
                        q = G.GEN[fam](rng, diff)
                        if q is None:
                            continue
                        q['family'] = fam
                        q['diff'] = diff
                        try:
                            ok = G.VERIFY[fam](q)
                        except Exception:
                            ok = []
                        if ok != [q['options'].index(q['correct_svg'])]:
                            continue
                        key = struct_key(q['prompt'], q['figs'] if isinstance(q['figs'], list) else [q['figs']])
                        if key in existing_keys or key in seen_keys:
                            continue
                        pk = pk_of(q)
                        if param_count.get(pk, 0) >= 3:
                            continue
                        if not all(fig_in_frame(s) for s in (q['figs'] if isinstance(q['figs'], list) else [q['figs']]) + q['options']):
                            continue
                        if structurally_broken(q):
                            continue
                        cands.append(q)
                    if not cands:
                        break
                    # 像素校验：80px 批量 → 通过者再以 140/200px 批量确认（避免单题渲染口径）
                    bad80 = set(f['qi'] for f in pc.check(cands, 80))
                    alive = [i for i in range(len(cands)) if i not in bad80]
                    bad = set(bad80)
                    if alive:
                        sub = [cands[i] for i in alive]
                        for size in (140, 200):
                            for f in pc.check(sub, size):
                                bad.add(alive[f['qi']])
                    for idx, q in enumerate(cands):
                        if idx in bad:
                            continue
                        # 通过：轮转答案到原槽位并替换
                        G.rotate_options(q, target)
                        key = struct_key(q['prompt'], q['figs'] if isinstance(q['figs'], list) else [q['figs']])
                        pk = pk_of(q)
                        questions[gi] = q
                        seen_keys.add(key)
                        param_count[pk] = param_count.get(pk, 0) + 1
                        replaced = True
                        break
                if not replaced:
                    still.add(gi)
            fails = still
        print(f'第{round_no}轮后剩余不合格: {len(fails)}', flush=True)
        browser.close()

    if fails:
        print(f'警告：仍有 {len(fails)} 题未修复: {sorted(fails)[:20]}')
    json.dump([{k: v for k, v in q.items() if k != 'correct_svg'} for q in questions],
              open(os.path.join(OUT_DIR, 'questions.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('修复完成，已写回 questions.json', flush=True)

if __name__ == '__main__':
    main()
