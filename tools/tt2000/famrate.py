# -*- coding: utf-8 -*-
"""各族像素通过率普查：每族生成N题，批量渲染80/140px，输出通过率。"""
import json, os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate as G
from gen_lib import struct_key, fig_in_frame
from pixel_check import check_batch
from playwright.sync_api import sync_playwright

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
CHROME = '/usr/local/bin/chromium'
ARGS = ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--disable-software-rasterizer']
N = 40

def main():
    rng = random.Random(991)
    existing = G.load_existing_keys()
    fams = list(G.GEN.keys())
    samples = {f: [] for f in fams}
    # 每族收集N题（逻辑合格即可，不做查重——测的是像素区分度）
    budget = {f: N * 30 for f in fams}
    for f in fams:
        tries = 0
        while len(samples[f]) < N and tries < budget[f]:
            tries += 1
            diff = rng.choice([1, 2, 3])
            try:
                q = G.GEN[f](rng, diff)
            except Exception:
                continue
            if q is None:
                continue
            q['family'] = f
            q['diff'] = diff
            try:
                ok = G.VERIFY[f](q)
            except Exception:
                ok = []
            if ok != [q['options'].index(q['correct_svg'])]:
                continue
            if not all(fig_in_frame(s) for s in (q['figs'] if isinstance(q['figs'], list) else [q['figs']]) + q['options']):
                continue
            samples[f].append(q)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=ARGS)
        report = {}
        for f in fams:
            qs = samples[f]
            if not qs:
                report[f] = {'n': 0, 'pass80': 0, 'pass140': 0}
                continue
            page = browser.new_page(viewport={'width': 80 * 10 + 40, 'height': 1200})
            fails80 = set(x['qi'] for x in check_batch(page, qs, 80))
            page.close()
            ok80 = [q for i, q in enumerate(qs) if i not in fails80]
            page = browser.new_page(viewport={'width': 140 * 10 + 40, 'height': 1200})
            fails140 = set(x['qi'] for x in check_batch(page, ok80, 140)) if ok80 else set()
            page.close()
            npass = sum(1 for i in range(len(ok80)) if i not in fails140)
            report[f] = {'n': len(qs), 'pass80': len(ok80), 'pass_both': npass}
            print(f"{f}: n={len(qs)} 过80px={len(ok80)} 过140px={npass}", flush=True)
        browser.close()
    json.dump(report, open(os.path.join(OUT_DIR, 'famrate.json'), 'w'), ensure_ascii=False, indent=1)
    print('完成')

if __name__ == '__main__':
    main()
