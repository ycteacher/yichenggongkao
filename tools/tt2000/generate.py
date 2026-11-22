# -*- coding: utf-8 -*-
"""图推2000题主生成器：配额→生成→验算→像素校验→查重→答案均衡→分片输出。"""
import json, os, re, sys, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_lib import struct_key, fig_sig, parse_svg
import families_a as FA
import families_b as FB

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(ROOT, 'assets')
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT_DIR, exist_ok=True)

SEED = 20261122

# 家族配额（总量2000；任务书六类配比相加为105%，按比例折算回2000：
# 数量286/位置476/样式476/空间286/属性381/一笔画95，交付时说明）
FAMILY_QUOTA = {
    'cnt_shape': 143, 'cnt_region': 76, 'cnt_inter': 67,            # 数量类286
    'pos_rot': 248, 'pos_trans': 143, 'pos_flip': 85,               # 位置类476
    'sty_xor': 143, 'sty_latin': 114, 'sty_bw': 114, 'sty_addsub': 105,  # 样式类476
    'spa_cube': 143, 'spa_view': 143,                               # 空间类286
    'attr_sym': 143, 'attr_curve': 95, 'attr_closed': 143,          # 属性类381
    'euler': 95,                                                    # 一笔画95
}
GEN = {
    'cnt_shape': FA.gen_count_shapes, 'cnt_region': FA.gen_count_regions, 'cnt_inter': FA.gen_count_intersections,
    'pos_rot': FA.gen_rotation, 'pos_trans': FA.gen_translation, 'pos_flip': FA.gen_flip,
    'sty_xor': FA.gen_xor, 'sty_latin': FA.gen_latin, 'sty_bw': FA.gen_bw, 'sty_addsub': FA.gen_addsub,
    'spa_cube': FB.gen_cube, 'spa_view': FB.gen_frontview,
    'attr_sym': FB.gen_symmetry, 'attr_curve': FB.gen_curved, 'attr_closed': FB.gen_closed,
    'euler': FB.gen_euler,
}
VERIFY = {
    'cnt_shape': FA.verify_count_shapes, 'cnt_region': FA.verify_count_regions, 'cnt_inter': FA.verify_count_intersections,
    'pos_rot': FA.verify_rotation, 'pos_trans': FA.verify_translation, 'pos_flip': FA.verify_flip,
    'sty_xor': FA.verify_xor, 'sty_latin': FA.verify_latin, 'sty_bw': FA.verify_bw, 'sty_addsub': FA.verify_addsub,
    'spa_cube': FB.verify_cube, 'spa_view': FB.verify_frontview,
    'attr_sym': FB.verify_symmetry, 'attr_curve': FB.verify_curved, 'attr_closed': FB.verify_closed,
    'euler': FB.verify_euler,
}

def load_existing_keys():
    """全库查重键集。"""
    keys = set()
    shard_files = [f for f in os.listdir(ASSETS) if f.endswith('.js') and (f.startswith('qk-') or f.startswith('cs-bank-'))]
    dec = json.JSONDecoder()
    for name in shard_files:
        text = open(os.path.join(ASSETS, name), encoding='utf-8').read()
        for m in re.finditer(r'\.push\(', text):
            try:
                val, _ = dec.raw_decode(text, m.end())
            except ValueError:
                continue
            items = val if isinstance(val, list) else [val]
            for q in items:
                if not isinstance(q, dict):
                    continue
                prompt = str(q.get('prompt', ''))
                figs = re.findall(r'<svg.*?</svg>', str(q.get('fig', '')), re.S)
                keys.add((prompt[:20], tuple(fig_sig(f) for f in figs)))
    return keys

def gen_one(family, diff, rng):
    g = GEN[family](rng, diff)
    if g is None:
        return None
    q = g
    q['family'] = family
    q['diff'] = diff
    return q

def rotate_options(q, target_pos):
    """旋转选项数组使正确答案落在 target_pos。"""
    opts = q['options']
    cur = opts.index(q['correct_svg'])
    shift = (target_pos - cur) % 4
    if shift:
        q['options'] = opts[shift:] + opts[:shift]
    q['answer'] = q['options'].index(q['correct_svg'])

def main():
    rng = random.Random(SEED)
    print('加载全库查重键...')
    existing_keys = load_existing_keys()
    print(f'全库键数: {len(existing_keys)}')

    # 难度配额：全局 600/800/600，按家族比例分配
    total = sum(FAMILY_QUOTA.values())
    diff_quota = {1: 600, 2: 800, 3: 600}
    fam_diff = {}
    remain = dict(diff_quota)
    fams = list(FAMILY_QUOTA)
    total_alloc = {1: 0, 2: 0, 3: 0}
    for i, fam in enumerate(fams):
        n = FAMILY_QUOTA[fam]
        if i == len(fams) - 1:
            alloc = {1: remain[1], 2: remain[2], 3: remain[3]}
        else:
            a1 = round(n * 0.30)
            a2 = round(n * 0.40)
            a3 = n - a1 - a2
            alloc = {1: a1, 2: a2, 3: a3}
        for d in (1, 2, 3):
            total_alloc[d] += alloc[d]
            remain[d] = diff_quota[d] - total_alloc[d]
        fam_diff[fam] = alloc
    print('家族×难度配额:', json.dumps(fam_diff, ensure_ascii=False))

    questions = []
    seen_keys = set()
    param_count = {}
    fail_stats = {}
    for fam in fams:
        fam_qs = []
        tries = 0
        max_tries = FAMILY_QUOTA[fam] * 40
        while len(fam_qs) < FAMILY_QUOTA[fam] and tries < max_tries:
            tries += 1
            # 按剩余配额选难度
            alloc = fam_diff[fam]
            avail = [d for d in (1, 2, 3) if alloc[d] > sum(1 for q in fam_qs if q['diff'] == d)]
            if not avail:
                break
            diff = rng.choice(avail)
            q = gen_one(fam, diff, rng)
            if q is None:
                fail_stats[fam] = fail_stats.get(fam, 0) + 1
                continue
            # 唯一解验算
            try:
                ok = VERIFY[fam](q)
            except Exception:
                ok = []
            correct_idx = q['options'].index(q['correct_svg'])
            if ok != [correct_idx]:
                fail_stats[fam] = fail_stats.get(fam, 0) + 1
                continue
            # 结构门槛：选项与非末位题干图必须非空（排除空框干扰项）
            from repair import structurally_broken
            if structurally_broken(q):
                fail_stats[fam] = fail_stats.get(fam, 0) + 1
                continue
            # 查重
            key = struct_key(q['prompt'], q['figs'] if isinstance(q['figs'], list) else [q['figs']])
            if key in existing_keys or key in seen_keys:
                fail_stats[fam] = fail_stats.get(fam, 0) + 1
                continue
            pk = (fam, q['params'])
            if param_count.get(pk, 0) >= 3:
                fail_stats[fam] = fail_stats.get(fam, 0) + 1
                continue
            seen_keys.add(key)
            param_count[pk] = param_count.get(pk, 0) + 1
            fam_qs.append(q)
        got = len(fam_qs)
        print(f'{fam}: {got}/{FAMILY_QUOTA[fam]} (尝试{tries}次)')
        questions.extend(fam_qs)

    print(f'生成总数: {len(questions)}')
    print('生成失败统计:', fail_stats)

    # 答案均衡（分难度）
    ans_count = {1: [0, 0, 0, 0], 2: [0, 0, 0, 0], 3: [0, 0, 0, 0]}
    for q in questions:
        c = ans_count[q['diff']]
        target = c.index(min(c))
        rotate_options(q, target)
        c[target] += 1
        # 旋转后重验
        ok = VERIFY[q['family']](q)
        assert ok == [q['answer']], f'旋转后验算失败 {q["family"]}'
    for d in (1, 2, 3):
        print(f'难度{d} 答案分布: {ans_count[d]}')

    # 保存中间产物
    with open(os.path.join(OUT_DIR, 'questions.json'), 'w', encoding='utf-8') as f:
        json.dump([{k: v for k, v in q.items() if k != 'correct_svg'} for q in questions], f, ensure_ascii=False)
    print('中间产物已保存，待像素校验与上架。')

if __name__ == '__main__':
    main()
