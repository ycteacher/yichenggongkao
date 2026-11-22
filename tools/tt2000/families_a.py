# -*- coding: utf-8 -*-
"""题型族A：数量类、位置类、样式类。每族生成 + 独立验算（从SVG几何重算，不信任生成参数）。"""
import math, random
from gen_lib import *

C = 60.0  # 画布中心

# ============ 数量类 ============

def _scatter_positions(n, rng, r_min=18, r_max=42):
    """在画布内散布n个不重叠位置（间距≥26px）。"""
    pts = []
    tries = 0
    while len(pts) < n and tries < 400:
        tries += 1
        p = (rng.uniform(20, 100), rng.uniform(20, 100))
        if all(math.hypot(p[0]-q[0], p[1]-q[1]) >= 26 for q in pts):
            pts.append(p)
    while len(pts) < n:  # 兜底网格
        i = len(pts)
        pts.append((25 + (i % 3) * 35, 25 + (i // 3) * 35))
    return pts

SHAPE_GEN = {
    'circle': lambda rng: el_circle(C, C, 16),
    'tri': lambda rng: el_polygon(C, C, 18, 3, rng.uniform(0, 120)),
    'sq': lambda rng: el_rect(C, C, 28, 28),
    'pent': lambda rng: el_polygon(C, C, 18, 5, rng.uniform(0, 72)),
    'star': lambda rng: el_star(C, C, 18, rng.uniform(0, 72)),
}

def gen_count_shapes(rng, diff):
    """元素个数递增/递减。困难版混入干扰元素（数量恒定）。"""
    shape = rng.choice(list(SHAPE_GEN))
    step = rng.choice([1, 1, 2])
    start = rng.randint(1, 3)
    dec = rng.random() < 0.4
    counts = [start + step * i for i in range(4)] if not dec else [start + step * (3 - i) for i in range(4)]
    if max(counts) > 6 or min(counts) < 0:
        return None
    distract_extra = diff == 3
    de_shape = rng.choice([s for s in SHAPE_GEN if s != shape])
    figs = []
    scatter_sig = None
    for k in counts[:3]:
        els = []
        pos = _scatter_positions(max(k, 1), rng)
        if scatter_sig is None:
            scatter_sig = tuple(round(v) for p in pos for v in p)
        for i in range(k):
            e = dict(SHAPE_GEN[shape](rng))
            if e['tag'] == 'circle':
                e['cx'], e['cy'] = pos[i]
            elif e['tag'] == 'rect':
                e['cx'], e['cy'] = pos[i]
            elif shape == 'star':
                e = el_star(pos[i][0], pos[i][1], 14, e.get('rot', 0))
            else:
                pts = poly_pts(pos[i][0], pos[i][1], 14, e['n'], e.get('rot', 0))
                e['pts'] = pts
            els.append(e)
        if distract_extra:
            dp = _scatter_positions(2, rng)
            for p in dp:
                e2 = dict(SHAPE_GEN[de_shape](rng))
                if e2['tag'] in ('circle', 'rect'):
                    e2['cx'], e2['cy'] = p
                elif de_shape == 'star':
                    e2 = el_star(p[0], p[1], 9, e2.get('rot', 0))
                else:
                    e2['pts'] = poly_pts(p[0], p[1], 9, e2['n'], e2.get('rot', 0))
                els.append(e2)
        figs.append(render_fig(els))
    correct_n = counts[2] + (step if not dec else -step)
    if correct_n < 0 or correct_n > 7:
        return None
    # 选项：不同数量
    cand = [correct_n]
    for d in (step, -step, 2 * step, -2 * step, 1, -1, 2):
        v = correct_n + d
        if 0 <= v <= 8 and v not in cand:
            cand.append(v)
        if len(cand) == 4:
            break
    if len(cand) < 4:
        return None
    rng.shuffle(cand)
    opts = []
    for v in cand:
        els = []
        pos = _scatter_positions(max(v, 1), rng)
        for i in range(v):
            e = dict(SHAPE_GEN[shape](rng))
            if e['tag'] in ('circle', 'rect'):
                e['cx'], e['cy'] = pos[i]
            elif shape == 'star':
                e = el_star(pos[i][0], pos[i][1], 14, e.get('rot', 0))
            else:
                e['pts'] = poly_pts(pos[i][0], pos[i][1], 14, e['n'], e.get('rot', 0))
            els.append(e)
        opts.append(render_fig(els))
    name = {'circle': '圆', 'tri': '三角形', 'sq': '正方形', 'pent': '五边形', 'star': '五角星'}[shape]
    dname = {'circle': '圆', 'tri': '三角形', 'sq': '正方形', 'pent': '五边形', 'star': '五角星'}[de_shape]
    if distract_extra:
        prompt = f'观察下列图形，{name}的数量依次变化（图中另有{dname}作干扰元素，数量不变）。问号处图形中{name}的数量应为：'
        expl = (f'【数量规律】图1→图2→图3：{name}数量依次为 {counts[0]}、{counts[1]}、{counts[2]}，'
                f'{"递增" if not dec else "递减"}{step}个；{dname}恒为2个（干扰项）。故问号处{name}应为 {correct_n} 个。'
                f'A/B/C/D中仅一项为{correct_n}个{name}，其余选项数量不符，排除。')
    else:
        prompt = f'观察下列图形中{name}的数量变化规律，问号处应填入：'
        expl = (f'【数量规律】图1→图2→图3：{name}数量依次为 {counts[0]}、{counts[1]}、{counts[2]}，'
                f'每次{"增加" if not dec else "减少"}{step}个。故问号处应为 {correct_n} 个{name}，'
                f'其余选项数量为{"、".join(str(v) for v in cand if v != correct_n)}，均不符合递变规律，排除。')
    return {'prompt': prompt, 'figs': figs + [QMARK], 'options': opts, 'correct_svg': opts[cand.index(correct_n)],
            'explanation': expl, '__sub': '数量规律', 'family': 'cnt_shape',
            'params': (shape, step, dec, distract_extra, scatter_sig), 'diff': diff}

def verify_count_shapes(q):
    """独立验算：解析各图元素数（剔除恒定数量的干扰元素），检查等差且唯一选项匹配。"""
    def type_of(e):
        if e['tag'] == 'polygon':
            return ('polygon', len(e['pts']))
        return (e['tag'],)
    fig_els = [parse_svg(f) for f in q['figs'][:3]]
    from collections import Counter
    counters = [Counter(type_of(e) for e in els) for els in fig_els]
    all_types = set().union(*[set(c) for c in counters])
    if len(all_types) > 2:
        return []
    main_type = None
    distract_type = None
    for t in all_types:
        cts = [c[t] for c in counters]
        if len(set(cts)) == 1 and len(all_types) == 2:
            distract_type = t
        else:
            main_type = t
    if main_type is None:
        return []
    counts = [c[main_type] for c in counters]
    opts = []
    for o in q['options']:
        opts.append(sum(1 for e in parse_svg(o) if type_of(e) == main_type))
    if len(set(counts)) != 3:
        return []
    d1, d2 = counts[1] - counts[0], counts[2] - counts[1]
    if d1 != d2 or d1 == 0:
        return []
    expect = counts[2] + d1
    return [i for i, n in enumerate(opts) if n == expect]

def gen_count_regions(rng, diff):
    """封闭区域数：嵌套图形。"""
    shape = rng.choice(['sq', 'circ', 'tri'])
    start = rng.randint(1, 2)
    rot = rng.uniform(0, 72)
    r_base = rng.uniform(6, 9)
    spacing = rng.uniform(5.5, 6.8)
    dcx, dcy = rng.uniform(-6, 6), rng.uniform(-6, 6)
    counts = [start + i for i in range(4)]
    if max(counts) > 6:
        return None
    figs = []
    for k in counts:
        els = []
        for i in range(k):
            r = r_base + i * spacing
            if shape == 'sq':
                els.append(el_rect(C + dcx, C + dcy, 2 * r, 2 * r))
            elif shape == 'circ':
                els.append(el_circle(C + dcx, C + dcy, r))
            else:
                els.append(el_polygon(C + dcx, C + dcy, r + 4, 3, rot))
        figs.append(render_fig(els))
    correct_n = counts[2] + 1
    if correct_n > 7:
        return None
    cand = [correct_n]
    for v in (correct_n - 2, correct_n + 2, correct_n - 3, correct_n + 1, correct_n - 1):
        if 1 <= v <= 8 and v not in cand:
            cand.append(v)
        if len(cand) == 4:
            break
    if len(cand) < 4:
        return None
    rng.shuffle(cand)
    opts = []
    for v in cand:
        els = []
        for i in range(v):
            r = r_base + i * spacing
            if shape == 'sq':
                els.append(el_rect(C + dcx, C + dcy, 2 * r, 2 * r))
            elif shape == 'circ':
                els.append(el_circle(C + dcx, C + dcy, r))
            else:
                els.append(el_polygon(C + dcx, C + dcy, r + 4, 3, rot))
        opts.append(render_fig(els))
    name = {'sq': '正方形', 'circ': '圆', 'tri': '三角形'}[shape]
    prompt = f'观察下列图形中封闭区域（面）的数量变化规律，问号处应填入：'
    expl = (f'【面数量规律】图1→图2→图3：封闭区域数依次为 {counts[0]}、{counts[1]}、{counts[2]}，每次增加1个'
            f'（每个{name}内部嵌套一层即多一个区域）。故问号处应为 {correct_n} 个封闭区域，其余选项区域数不符，排除。')
    return {'prompt': prompt, 'figs': figs + [QMARK], 'options': opts, 'correct_svg': opts[cand.index(correct_n)],
            'explanation': expl, '__sub': '封闭区域', 'family': 'cnt_region',
            'params': (shape, start, round(rot), round(r_base), round(spacing)), 'diff': diff}

def verify_count_regions(q):
    def regions(f):
        return len([e for e in parse_svg(f) if e['tag'] in ('polygon', 'rect', 'circle')])
    counts = [regions(f) for f in q['figs'][:3]]
    if len(set(counts)) != 3:
        return []
    if counts[1] - counts[0] != 1 or counts[2] - counts[1] != 1:
        return []
    expect = counts[2] + 1
    return [i for i, o in enumerate(q['options']) if regions(o) == expect]

def gen_count_intersections(rng, diff):
    """交点数：横线×竖线网格，交点数=h*v，可精确验算。
    每个选项网格位置随机（交点数只由线数决定），保证选项间像素差异充足。"""
    h0 = rng.randint(1, 2)
    v = rng.randint(2, 3)
    step_h = 1
    hs = [h0, h0 + step_h, h0 + 2 * step_h]
    if max(hs) > 4 or hs[2] + step_h > 4:
        return None
    def rand_rows(n, rng):
        """n条横线的y坐标：范围内随机、间距≥14。"""
        for _ in range(60):
            ys = sorted(rng.uniform(24, 96) for _ in range(n))
            if all(ys[i + 1] - ys[i] >= 14 for i in range(n - 1)):
                return ys
        return [26 + i * (70 / max(n - 1, 1)) for i in range(n)]
    def rand_cols(n, rng):
        for _ in range(60):
            xs = sorted(rng.uniform(26, 94) for _ in range(n))
            if all(xs[i + 1] - xs[i] >= 14 for i in range(n - 1)):
                return xs
        return [28 + i * (64 / max(n - 1, 1)) for i in range(n)]
    def grid_fig(h, vv, rng):
        ys = rand_rows(h, rng)
        xs = rand_cols(vv, rng)
        els = [el_line(20, y, 100, y) for y in ys]
        els += [el_line(x, 20, x, 100) for x in xs]
        return render_fig(els), ys, xs
    figs, ly, lx = grid_fig(hs[0], v, rng)
    figs = [figs] + [grid_fig(h, v, rng)[0] for h in hs[1:]]
    base_counts = [h * v for h in hs]
    if len(set(base_counts)) != 3:
        return None
    expect = base_counts[2] + step_h * v
    correct, _, _ = grid_fig(hs[2] + step_h, v, rng)
    cand = [correct]
    tried = {hs[2] + step_h}
    others = [h for h in (1, 2, 3, 4) if h not in tried]
    rng.shuffle(others)
    for h2 in others:
        if len(cand) == 4:
            break
        tried.add(h2)
        cand.append(grid_fig(h2, v, rng)[0])
    if len(cand) < 4:
        return None
    rng.shuffle(cand)
    correct_svg = next(s for s in cand if len(seg_intersections(parse_svg(s))) == expect)
    prompt = '观察下列图形中线条交点数量的变化规律，问号处应填入：'
    expl = (f'【交点数规律】图1→图2→图3：横线与竖线相交，交点数依次为 {base_counts[0]}、{base_counts[1]}、'
            f'{base_counts[2]}，每次增加{step_h*v}个（每加一条横线多{v}个交点）。'
            f'故问号处交点数应为 {expect}，其余选项交点数不符，排除。')
    return {'prompt': prompt, 'figs': figs + [QMARK], 'options': cand, 'correct_svg': correct_svg,
            'explanation': expl, '__sub': '交点数', 'family': 'cnt_inter',
            'params': (h0, v, diff, round(float(ly[0]), 1), round(float(lx[0]), 1)), 'diff': diff}

def verify_count_intersections(q):
    counts = [len(seg_intersections(parse_svg(f))) for f in q['figs'][:3]]
    if len(set(counts)) != 3:
        return []
    d = counts[1] - counts[0]
    if d != counts[2] - counts[1] or d == 0:
        return []
    expect = counts[2] + d
    return [i for i, o in enumerate(q['options']) if len(seg_intersections(parse_svg(o))) == expect]

# ============ 位置类 ============

ROT_SHAPES = {
    'tri': (3, 120), 'sq': (4, 90), 'pent': (5, 72), 'star': (5, 72), 'hex': (6, 60),
}

def _rot_shape_el(kind, cx, cy, r, rot):
    if kind == 'star':
        return el_star(cx, cy, r, rot)
    n, _ = ROT_SHAPES[kind]
    return el_polygon(cx, cy, r, n, rot)

def gen_rotation(rng, diff):
    """旋转：θ≥45°，选项间角度差显著。困难版：旋转+沿轨迹移动。"""
    kind = rng.choice(['tri', 'pent', 'star', 'sq', 'hex'])
    n, period = ROT_SHAPES[kind]
    theta = rng.choice([t for t in (45, 60, 90, 120, 135) if t % period != 0])
    ccw = rng.random() < 0.5
    if ccw:
        theta = -theta
    r0 = rng.uniform(0, 60)
    move = diff == 3
    # 三步后图形（r=20）须完整留在 120×120 画框内：|3*mvec| ≤ 60-20-边距
    mvec = (rng.choice([-1, 1]) * rng.uniform(7, 12), rng.choice([-1, 1]) * rng.uniform(5, 9)) if move else (0, 0)
    def rot_fig(cx, cy, rot):
        # 方向标记：第一个顶点方向外侧的实心小圆，随图形一起旋转，打破旋转对称
        shape = _rot_shape_el(kind, cx, cy, 20, rot)
        import math as _m
        mx = cx + 27 * _m.cos(_m.radians(rot - 90))
        my = cy + 27 * _m.sin(_m.radians(rot - 90))
        return render_fig([shape, el_circle(mx, my, 4.5, fill='#1a1a1a')])
    figs = []
    for i in range(3):
        rot = r0 + theta * i
        cx, cy = C + mvec[0] * i, C + mvec[1] * i
        figs.append(rot_fig(cx, cy, rot))
    exp_rot = r0 + theta * 3
    exp_pos = (C + mvec[0] * 3, C + mvec[1] * 3)
    def make_opt(rot, pos):
        return rot_fig(pos[0], pos[1], rot)
    correct = make_opt(exp_rot, exp_pos)
    # 干扰：角度偏 ±45/±90（模周期后仍不同）或位置错
    offs = [45, -45, 90, -90, 135, -135]
    rng.shuffle(offs)
    distractors = []
    for off in offs:
        if len(distractors) >= 3:
            break
        nr = exp_rot + off
        if (nr - exp_rot) % period == 0:
            continue
        if move and rng.random() < 0.5:
            p = (exp_pos[0] + rng.choice([-1, 1]) * 18, exp_pos[1] + rng.choice([-1, 1]) * 14)
            d_svg = make_opt(exp_rot, p)
            if not fig_in_frame(d_svg):
                continue
            distractors.append(d_svg)
        else:
            distractors.append(make_opt(nr, exp_pos))
    if len(distractors) < 3:
        return None
    opts = distractors + [correct]
    # 出框守卫：题干图与选项图形必须完整落在画框内
    if not all(fig_in_frame(s) for s in figs + opts):
        return None
    rng.shuffle(opts)
    ans = opts.index(correct)
    name = {'tri': '三角形', 'sq': '正方形', 'pent': '五边形', 'star': '五角星', 'hex': '六边形'}[kind]
    dirn = '逆时针' if ccw else '顺时针'
    if move:
        prompt = f'观察下列图形的旋转与移动规律（{name}每次{dirn}旋转{abs(theta)}°，同时沿直线移动），问号处应填入：'
        expl = (f'【位置规律】图1→图2→图3：{name}每次{dirn}旋转{abs(theta)}°，且中心沿固定方向每次移动'
                f'（位移恒定）。故问号处应在继续旋转{abs(theta)}°的基础上再移动一步。'
                f'正确选项旋转角度与位置均延续规律；其余选项或角度差{abs(theta)}°以上、或位置偏离，排除。')
    else:
        prompt = f'观察下列图形的旋转规律（{name}绕中心每次{dirn}旋转{abs(theta)}°），问号处应填入：'
        expl = (f'【旋转规律】图1→图2→图3：{name}绕中心每次{dirn}旋转{abs(theta)}°。'
                f'故问号处应在图3基础上继续{dirn}旋转{abs(theta)}°。其余选项旋转角度为{abs(theta)}°的偏移量'
                f'（±45°/±90°），与规律不符，排除。')
    return {'prompt': prompt, 'figs': figs + [QMARK], 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '旋转', 'family': 'pos_rot',
            'params': (kind, abs(theta), ccw, move, round(r0)), 'diff': diff}

def verify_rotation(q):
    """独立验算：从SVG重算各图旋转角，检查等差且唯一选项延续。"""
    def rot_of(svg):
        els = [e for e in parse_svg(svg) if e['tag'] == 'polygon']
        if not els:
            return None, None
        e = els[0]
        c = centroid(e['pts'])
        return poly_rotation(e['pts']), c
    rots, cens = [], []
    for f in q['figs'][:3]:
        r, c = rot_of(f)
        if r is None:
            return []
        rots.append(r)
        cens.append(c)
    d1 = (rots[1] - rots[0] + 180) % 360 - 180
    d2 = (rots[2] - rots[1] + 180) % 360 - 180
    if abs(d1 - d2) > 0.5 or abs(d1) < 44.5:
        return []
    exp = rots[2] + d1
    # 位置校验：中心点也需等差移动（静止时位移为0）
    vx, vy = cens[1][0] - cens[0][0], cens[1][1] - cens[0][1]
    exp_c = (cens[2][0] + vx, cens[2][1] + vy)
    res = []
    for o in q['options']:
        r, c = rot_of(o)
        if r is None:
            continue
        diff_a = abs((r - exp + 180) % 360 - 180)
        if diff_a >= 20:
            continue
        if math.hypot(c[0] - exp_c[0], c[1] - exp_c[1]) > 8:
            continue
        res.append(q['options'].index(o))
    return res

def gen_translation(rng, diff):
    """平移：位移≥15px（80px渲染下≥10px，肉眼可辨），位置由构造保证不出界。困难版：平移+大小缩放。"""
    kind = rng.choice(['tri', 'sq', 'pent', 'star'])
    scale_mode = diff == 3
    # 位移方向固定，步长25-35px；起点保证3步后不出界
    dx = rng.choice([-1, 1]) * rng.uniform(15, 19)
    dy = rng.choice([-1, 1]) * rng.uniform(12, 16)
    # 起点选在使 1..3 步都落在安全范围（缩放版图形更大，范围更紧）
    lo_c, hi_c = (30, 90) if scale_mode else (26, 94)
    lo_x, hi_x = lo_c - min(0, 3 * dx), hi_c - max(0, 3 * dx)
    lo_y, hi_y = lo_c - min(0, 3 * dy), hi_c - max(0, 3 * dy)
    if lo_x > hi_x or lo_y > hi_y:
        return None
    bx = rng.uniform(lo_x, hi_x)
    by = rng.uniform(lo_y, hi_y)
    r0 = 16.0 if scale_mode else 20.0
    growth = 0.2 if scale_mode else 0.0
    figs = []
    for i in range(3):
        cx, cy = bx + dx * i, by + dy * i
        r = r0 * (1 + growth * i)
        figs.append(render_fig([_rot_shape_el(kind, cx, cy, r, 0)]))
    exp_c = (bx + dx * 3, by + dy * 3)
    exp_r = r0 * (1 + growth * 3)
    def make_opt(cx, cy, r):
        return render_fig([_rot_shape_el(kind, cx, cy, r, 0)])
    correct = make_opt(exp_c[0], exp_c[1], exp_r)
    distractors = []
    offs = [(30, 0), (-30, 0), (0, 28), (0, -28), (25, 25), (-25, -25)]
    rng.shuffle(offs)
    for ox, oy in offs:
        if len(distractors) >= 3:
            break
        if scale_mode and rng.random() < 0.5:
            distractors.append(make_opt(exp_c[0], exp_c[1], exp_r * rng.choice([0.6, 1.4])))
        else:
            nc = (exp_c[0] + ox * 0.6, exp_c[1] + oy * 0.6)
            d_svg = make_opt(nc[0], nc[1], exp_r)
            if not fig_in_frame(d_svg):
                continue
            distractors.append(d_svg)
    if len(distractors) < 3:
        return None
    opts = distractors + [correct]
    # 出框守卫：题干图与选项图形必须完整落在画框内
    if not all(fig_in_frame(s) for s in figs + opts):
        return None
    rng.shuffle(opts)
    ans = opts.index(correct)
    name = {'tri': '三角形', 'sq': '正方形', 'pent': '五边形', 'star': '五角星'}[kind]
    if scale_mode:
        prompt = f'观察下列图形的移动与大小变化规律（{name}沿固定方向平移，同时逐渐变大），问号处应填入：'
        expl = (f'【位置+大小规律】图1→图2→图3：{name}中心沿固定方向每次平移相同距离，且尺寸逐级放大约20%。'
                f'故问号处应继续平移一步并放大。正确选项位置与大小均延续规律；其余选项或位置偏移明显、'
                f'或大小不变/突变，排除。')
    else:
        prompt = f'观察下列图形的平移规律（{name}沿固定方向每次移动相同距离），问号处应填入：'
        expl = (f'【平移规律】图1→图2→图3：{name}中心每次沿同一方向平移（位移大小与方向恒定）。'
                f'故问号处应继续沿该方向移动一步。其余选项位置偏移明显（方向不符），排除。')
    return {'prompt': prompt, 'figs': figs + [QMARK], 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '平移', 'family': 'pos_trans',
            'params': (kind, round(dx), round(dy), scale_mode), 'diff': diff}

def verify_translation(q):
    def cen_of(svg):
        els = parse_svg(svg)
        if not els:
            return None, None
        e = els[0]
        if e['tag'] == 'polygon':
            return centroid(e['pts'])
        if e['tag'] in ('circle', 'rect'):
            return (e['cx'], e['cy'])
        return None, None
    cens = []
    for f in q['figs'][:3]:
        c = cen_of(f)
        if c is None:
            return []
        cens.append(c)
    d1 = (cens[1][0] - cens[0][0], cens[1][1] - cens[0][1])
    d2 = (cens[2][0] - cens[1][0], cens[2][1] - cens[1][1])
    if math.hypot(d1[0] - d2[0], d1[1] - d2[1]) > 2 or math.hypot(*d1) < 15:
        return []
    exp = (cens[2][0] + d1[0], cens[2][1] + d1[1])
    def size_of(svg):
        e = parse_svg(svg)[0]
        if e['tag'] == 'circle':
            return e['r']
        if e['tag'] == 'rect':
            return e['w'] / 2
        pts = e['pts']
        c = centroid(pts)
        return max(math.hypot(p[0] - c[0], p[1] - c[1]) for p in pts)
    sizes = [size_of(f) for f in q['figs'][:3]]
    exp_size = sizes[2] + (sizes[2] - sizes[1])
    res = []
    for i, o in enumerate(q['options']):
        c = cen_of(o)
        if not c or math.hypot(c[0] - exp[0], c[1] - exp[1]) >= 12:
            continue
        if abs(size_of(o) - exp_size) > 3:
            continue
        res.append(i)
    return res

def gen_flip(rng, diff):
    """翻转：带标记图形左右/上下交替镜像。"""
    # 不对称图形：直角三角形+小圆标记
    bx1 = rng.uniform(38, 52); by1 = rng.uniform(34, 46)
    by2 = rng.uniform(74, 86); bx3 = rng.uniform(72, 88)
    base_pts = [(bx1, by1), (bx1, by2), (bx3, by2)]
    marker_off = (10, -8)
    mode = rng.choice(['h', 'v'])
    figs = []
    states = []
    for i in range(3):
        flip_h = (i % 2 == 1) if mode == 'h' else False
        flip_v = (i % 2 == 1) if mode == 'v' else False
        pts = [(120 - x if flip_h else x, 120 - y if flip_v else y) for x, y in base_pts]
        mk = (120 - base_pts[0][0] - marker_off[0] if flip_h else base_pts[0][0] + marker_off[0],
              120 - base_pts[0][1] - marker_off[1] if flip_v else base_pts[0][1] + marker_off[1])
        els = [{'tag': 'polygon', 'pts': pts}, el_circle(mk[0], mk[1], 4, fill='#1a1a1a')]
        figs.append(render_fig(els))
        states.append((flip_h, flip_v))
    fh, fv = states[2]
    nfh, nfv = (not fh, fv) if mode == 'h' else (fh, not fv)
    def make(flip_h, flip_v):
        pts = [(120 - x if flip_h else x, 120 - y if flip_v else y) for x, y in base_pts]
        mk = (120 - base_pts[0][0] - marker_off[0] if flip_h else base_pts[0][0] + marker_off[0],
              120 - base_pts[0][1] - marker_off[1] if flip_v else base_pts[0][1] + marker_off[1])
        return render_fig([{'tag': 'polygon', 'pts': pts}, el_circle(mk[0], mk[1], 4, fill='#1a1a1a')])
    correct = make(nfh, nfv)
    distractors = [make(not nfh, nfv), make(nfh, not nfv), make(not nfh, not nfv)]
    opts = distractors + [correct]
    rng.shuffle(opts)
    ans = opts.index(correct)
    mname = '左右翻转' if mode == 'h' else '上下翻转'
    prompt = f'观察下列图形的翻转规律（图形与黑点标记交替{mname}），问号处应填入：'
    expl = (f'【翻转规律】图1→图2→图3：图形每次交替{mname}（黑点标记随之镜像）。'
            f'故问号处应在图3基础上再次{mname}。其余选项分别为不翻转、双向翻转等状态，与交替规律不符，排除。')
    return {'prompt': prompt, 'figs': figs + [QMARK], 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '翻转', 'family': 'pos_flip',
            'params': (mode, round(bx1), round(by1), round(bx3), round(by2)), 'diff': diff}

def verify_flip(q):
    """验算：黑点相对三角形位置交替。"""
    def state_of(svg):
        els = parse_svg(svg)
        poly = next((e for e in els if e['tag'] == 'polygon'), None)
        circ = next((e for e in els if e['tag'] == 'circle'), None)
        if not poly or not circ:
            return None
        c = centroid(poly['pts'])
        return (circ['cx'] > c[0], circ['cy'] > c[1])  # (右侧?, 下侧?)
    sts = [state_of(f) for f in q['figs'][:3]]
    if any(s is None for s in sts):
        return []
    if not (sts[0] != sts[1] and sts[1] != sts[2]):
        return []
    # 推断翻转轴：sts[0]与sts[1]不同的那个坐标即翻转维度
    if sts[0][0] != sts[1][0]:
        exp = (not sts[2][0], sts[2][1])
    elif sts[0][1] != sts[1][1]:
        exp = (sts[2][0], not sts[2][1])
    else:
        return []
    res = []
    for i, o in enumerate(q['options']):
        s = state_of(o)
        if s == exp:
            res.append(i)
    return res

# ============ 样式类 ============

def _slot_el(kind, slot):
    """固定槽位元素（4x2槽位网格），签名稳定。"""
    positions = [(30, 40), (60, 40), (90, 40), (30, 80), (60, 80), (90, 80)]
    cx, cy = positions[slot]
    if kind == 'circ':
        return el_circle(cx, cy, 11)
    if kind == 'sq':
        return el_rect(cx, cy, 20, 20)
    if kind == 'tri':
        return el_polygon(cx, cy, 13, 3, 0)
    if kind == 'star':
        return el_star(cx, cy, 13, 0)
    if kind == 'diam':
        return el_polygon(cx, cy, 13, 4, 45)
    if kind == 'pent':
        return el_polygon(cx, cy, 13, 5, 0)
    raise ValueError(kind)

def gen_xor(rng, diff):
    """去同存异：图1⊕图2=答案。元素集对称差。保证有交集且各有独有元素。"""
    pool = ['circ', 'sq', 'tri', 'star', 'diam', 'pent']
    n_slots = 6
    slots = rng.sample(range(n_slots), n_slots)
    n_inter = rng.randint(1, 2)
    n_1only = rng.randint(1, 2)
    n_2only = rng.randint(1, 2)
    if n_inter + n_1only + n_2only > n_slots:
        return None
    inter = set(slots[:n_inter])
    s1only = set(slots[n_inter:n_inter + n_1only])
    s2only = set(slots[n_inter + n_1only:n_inter + n_1only + n_2only])
    s1 = inter | s1only
    s2 = inter | s2only
    kinds1 = {s: rng.choice(pool) for s in s1}
    kinds2 = {s: rng.choice(pool) for s in s2}
    for s in inter:
        kinds2[s] = kinds1[s]  # 重叠槽位同种图形才能消去
    def fig_of(kinds):
        return render_fig([_slot_el(kinds[s], s) for s in sorted(kinds)])
    f1, f2 = fig_of(kinds1), fig_of(kinds2)
    ans_slots = sorted(s1only | s2only)
    kinds_ans = {s: (kinds1 if s in s1 else kinds2)[s] for s in ans_slots}
    correct = fig_of(kinds_ans)
    def variant(slotset, source):
        return fig_of({s: source[s] for s in sorted(slotset)})
    distractors = []
    all_kinds = {**kinds2, **kinds1}
    distractors.append(variant(s1 | s2, all_kinds))          # 并集（未消去）
    if inter:
        distractors.append(variant(inter, kinds1))            # 交集（只留相同）
    distractors.append(variant(s1only, kinds1))               # 仅图一独有
    seen = {f1, f2, correct}
    uniq_d = []
    for d in distractors:
        if d not in seen:
            uniq_d.append(d)
            seen.add(d)
    if len(uniq_d) < 3:
        return None
    opts = uniq_d[:3] + [correct]
    rng.shuffle(opts)
    ans = opts.index(correct)
    prompt = '图一与图二按「去同存异」叠加后（相同元素消去、不同元素保留），问号处应得到什么图形？'
    expl = (f'【去同存异】逐槽位比对图一与图二：相同位置的相同图形叠加后消去，只保留仅出现一次的元素。'
            f'消去{len(inter)}个相同元素后，剩余{len(ans_slots)}个元素即问号处图形。'
            f'其余选项分别为并集（未消去）、交集（只留相同）或单侧残缺，均不符合去同存异，排除。')
    return {'prompt': prompt, 'figs': [f1, f2, QMARK], 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '去同存异', 'family': 'sty_xor',
            'params': (tuple(sorted(s1)), tuple(sorted(s2))), 'diff': diff}

def verify_xor(q):
    s1 = {elem_sig(e) for e in parse_svg(q['figs'][0])}
    s2 = {elem_sig(e) for e in parse_svg(q['figs'][1])}
    expect = s1 ^ s2
    res = []
    for i, o in enumerate(q['options']):
        s = {elem_sig(e) for e in parse_svg(o)}
        if s == expect:
            res.append(i)
    return res

def gen_latin(rng, diff):
    """遍历：拉丁方每行每列各图形出现一次。简单/中等3x3三图形，困难4x4四图形。"""
    if diff == 3:
        kinds = ['circ', 'sq', 'tri', 'star']
        N = 4
        cell = 27
        origin = 6.0
    else:
        kinds = ['circ', 'sq', 'tri']
        N = 3
        cell = 36
        origin = 8.0
    base = list(range(N))
    rng.shuffle(base)
    grid = [[(base[(r + c) % N]) for c in range(N)] for r in range(N)]
    if rng.random() < 0.5:  # 列也打乱
        perm = list(range(N))
        rng.shuffle(perm)
        grid = [[grid[r][perm[c]] for c in range(N)] for r in range(N)]
    miss_r, miss_c = rng.randint(0, N - 1), rng.randint(0, N - 1)
    def draw_grid(hide):
        parts = []
        for r in range(N):
            for c in range(N):
                ox, oy = origin + c * cell, origin + r * cell
                parts.append(f'<rect x="{ox}" y="{oy}" width="{cell}" height="{cell}" fill="white" stroke="#333" stroke-width="1.8"/>')
                if (r, c) == hide:
                    parts.append(f'<text x="{ox+cell/2}" y="{oy+cell/2+8}" font-size="24" text-anchor="middle" fill="#1a1a1a">?</text>')
                else:
                    ccx, ccy = ox + cell / 2, oy + cell / 2
                    k = kinds[grid[r][c]]
                    if k == 'circ':
                        e = el_circle(ccx, ccy, 11)
                    elif k == 'sq':
                        e = el_rect(ccx, ccy, 20, 20)
                    elif k == 'diam':
                        e = el_polygon(ccx, ccy, 13, 4, 45)
                    elif k == 'star':
                        e = el_star(ccx, ccy, 13, 0)
                    else:
                        e = el_polygon(ccx, ccy, 13, 3, 0)
                    parts.append(render_el(e))
        return svg_wrap(''.join(parts))
    figs = [draw_grid((miss_r, miss_c))]
    exp_k = grid[miss_r][miss_c]
    def big_el(kind_name):
        cx, cy = 60.0, 60.0
        if kind_name == 'circ':
            return el_circle(cx, cy, 30)
        if kind_name == 'sq':
            return el_rect(cx, cy, 48, 48)
        if kind_name == 'tri':
            return el_polygon(cx, cy, 34, 3, 0)
        if kind_name == 'star':
            return el_star(cx, cy, 34, 0)
        if kind_name == 'diam':
            return el_polygon(cx, cy, 34, 4, 45)
        return el_polygon(cx, cy, 34, 5, 0)
    def single(k):
        kind_name = kinds[k] if k < len(kinds) else 'star'
        return render_fig([big_el(kind_name)])
    correct = single(exp_k)
    distractors = [single(k) for k in range(N) if k != exp_k]
    if len(distractors) < 3:  # 3×3 只有2个同类干扰，补一个不在遍历中的图形
        distractors.append(single(3))
    opts = distractors[:3] + [correct]
    rng.shuffle(opts)
    ans = opts.index(correct)
    kn = {'circ': '圆', 'sq': '正方形', 'tri': '三角形', 'diam': '菱形', 'star': '五角星'}
    kind_name = kn[kinds[exp_k]]
    if diff == 3:
        prompt = '4×4方格中每行、每列均包含四种图形各一个。问号处应填入的图形是：'
        row_kinds = [kinds[grid[miss_r][c]] for c in range(4) if c != miss_c]
        col_kinds = [kinds[grid[r][miss_c]] for r in range(4) if r != miss_r]
        expl = (f'【遍历规律】每行、每列四种图形（圆、正方形、三角形、五角星）各出现一次。'
                f'问号所在行已含{"、".join(kn[k] for k in row_kinds)}，缺{kind_name}；'
                f'所在列已含{"、".join(kn[k] for k in col_kinds)}，同样缺{kind_name}，行列互相验证。'
                f'故问号处应为{kind_name}，其余图形在行列中均已出现，排除。')
    else:
        prompt = '九宫格中每行、每列均包含三种图形各一个。问号处应填入的图形是：'
        row_kinds = [kinds[grid[miss_r][c]] for c in range(3) if c != miss_c]
        col_kinds = [kinds[grid[r][miss_c]] for r in range(3) if r != miss_r]
        expl = (f'【遍历规律】每行、每列三种图形（圆、正方形、三角形）各出现一次。'
                f'问号所在行已含{"、".join(kn[k] for k in row_kinds)}，缺{kind_name}；'
                f'所在列已含{"、".join(kn[k] for k in col_kinds)}，同样缺{kind_name}，行列互相验证。'
                f'故问号处应为{kind_name}，其余图形均非所缺图形（或在行列中已出现），排除。')
    return {'prompt': prompt, 'figs': [figs[0]], 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '遍历', 'family': 'sty_latin',
            'params': (N, tuple(tuple(row) for row in grid), (miss_r, miss_c)), 'diff': diff}

def verify_latin(q):
    """验算：解析拉丁方，检查行列遍历并确定唯一缺项。支持3×3与4×4。"""
    svg = q['figs'][0]
    root = ET.fromstring(svg)
    # 先从格子矩形检测网格规格
    geom = None
    for el in root.iter():
        if el.tag == NS + 'rect':
            w = float(el.get('width'))
            if 30 < w < 40:
                geom = (3, 36.0, 8.0)
                break
            if 22 < w < 32:
                geom = (4, 27.0, 6.0)
                break
    if geom is None:
        return []
    N, cell, origin = geom
    cells = {}
    for el in root.iter():
        if el.tag in (NS + 'polygon', NS + 'circle', NS + 'rect'):
            if el.tag == NS + 'rect':
                x, y = float(el.get('x')), float(el.get('y'))
                w = float(el.get('width'))
                if not (10 < w < 25):
                    continue
                cx, cy = x + 10, y + 10
                kind = 'rect'
            elif el.tag == NS + 'circle':
                cx, cy = float(el.get('cx')), float(el.get('cy'))
                kind = 'circ'
            else:
                pts = [(float(a), float(b)) for a, b in (p.split(',') for p in el.get('points').split())]
                cx, cy = centroid(pts)
                kind = f'poly{len(pts)}'
            r_, c_ = int((cy - origin) // cell), int((cx - origin) // cell)
            if 0 <= r_ < N and 0 <= c_ < N:
                cells.setdefault((r_, c_), set()).add(kind)
    if len(cells) != N * N - 1:
        return []
    grid = {}
    for k, v in cells.items():
        if len(v) != 1:
            return []
        grid[k] = next(iter(v))
    kinds_present = set(grid.values())
    if len(kinds_present) != N:
        return []
    miss = [(r, c) for r in range(N) for c in range(N) if (r, c) not in grid]
    if len(miss) != 1:
        return []
    mr, mc = miss[0]
    row = [grid[(mr, c)] for c in range(N) if (mr, c) in grid]
    col = [grid[(r, mc)] for r in range(N) if (r, mc) in grid]
    if len(set(row)) != N - 1 or len(set(col)) != N - 1:
        return []
    def norm(k):
        return ('poly', int(k[4:])) if k.startswith('poly') else k
    exp_kind = norm((kinds_present - set(row)).pop())
    if exp_kind != norm((kinds_present - set(col)).pop()):
        return []
    def opt_kind(o):
        els = [e for e in parse_svg(o)]
        if not els:
            return None
        s = elem_sig(els[0])
        return (s[0], s[1]) if s[0] == 'poly' else s[0]
    res = []
    for i, o in enumerate(q['options']):
        if opt_kind(o) == exp_kind:
            res.append(i)
    return res

BW_RULES = {
    'same_black': {('b', 'b'): 'b', ('b', 'w'): 'w', ('w', 'b'): 'w', ('w', 'w'): 'b'},
    'xor_black': {('b', 'b'): 'w', ('b', 'w'): 'b', ('w', 'b'): 'b', ('w', 'w'): 'w'},
    'or_black': {('b', 'b'): 'b', ('b', 'w'): 'b', ('w', 'b'): 'b', ('w', 'w'): 'w'},
    'and_black': {('b', 'b'): 'b', ('b', 'w'): 'w', ('w', 'b'): 'w', ('w', 'w'): 'w'},
}
RULE_DESC = {
    'same_black': '同色得黑、异色得白', 'xor_black': '异色得黑、同色得白',
    'or_black': '有黑得黑、全白得白', 'and_black': '全黑得黑、有白得白',
}

def _bw_grid_svg(black_cells, cell=36):
    parts = []
    for r in range(3):
        for c in range(3):
            ox, oy = 8 + c * cell, 8 + r * cell
            fill = '#1a1a1a' if (r, c) in black_cells else 'white'
            parts.append(f'<rect x="{ox}" y="{oy}" width="{cell}" height="{cell}" fill="{fill}" stroke="#333" stroke-width="2.2"/>')
    return svg_wrap(''.join(parts))

def parse_bw(svg):
    root = ET.fromstring(svg)
    blacks = set()
    for el in root.iter():
        if el.tag == NS + 'rect':
            x, y = float(el.get('x')), float(el.get('y'))
            if float(el.get('width')) >= 119:
                continue
            if el.get('fill') == '#1a1a1a':
                blacks.add((int((y - 8) // 36), int((x - 8) // 36)))
    return blacks

def gen_bw(rng, diff):
    """黑白叠加：图1+图2=图3（规则表）。"""
    rule = rng.choice(list(BW_RULES))
    tbl = BW_RULES[rule]
    while True:
        g1 = {(i // 3, i % 3) for i in rng.sample(range(9), rng.randint(3, 5))}
        g2 = {(i // 3, i % 3) for i in rng.sample(range(9), rng.randint(3, 5))}
        g3 = {(i // 3, i % 3) for i in range(9) if tbl[('b' if (i // 3, i % 3) in g1 else 'w', 'b' if (i // 3, i % 3) in g2 else 'w')] == 'b'}
        if 2 <= len(g3) <= 7 and g1 != g2:
            outs = set()
            for t2 in BW_RULES.values():
                outs.add(frozenset((i // 3, i % 3) for i in range(9) if t2[('b' if (i // 3, i % 3) in g1 else 'w', 'b' if (i // 3, i % 3) in g2 else 'w')] == 'b'))
            if len(outs) == len(BW_RULES):
                break
    f1, f2, f3 = _bw_grid_svg(g1), _bw_grid_svg(g2), _bw_grid_svg(g3)
    correct = f3
    distractors = []
    tries = 0
    while len(distractors) < 3 and tries < 40:
        tries += 1
        bad = {(i // 3, i % 3) for i in rng.sample(range(9), len(g3))}
        if bad != g3 and len(bad ^ g3) >= 3:
            d = _bw_grid_svg(bad)
            if d not in distractors:
                distractors.append(d)
    if len(distractors) < 3:
        return None
    opts = distractors + [correct]
    rng.shuffle(opts)
    ans = opts.index(correct)
    prompt = f'图一与图二叠加得到图三（叠加规律：{RULE_DESC[rule]}）。问号处应填入：'
    expl = (f'【黑白叠加】逐格套用规则「{RULE_DESC[rule]}」：图一与图二同为黑→{"黑" if tbl[("b","b")]=="b" else "白"}，'
            f'一黑一白→{"黑" if tbl[("b","w")]=="b" else "白"}，同为白→{"黑" if tbl[("w","w")]=="b" else "白"}。'
            f'逐格叠加后共{len(g3)}格为黑。正确选项与逐格叠加结果完全一致；其余选项至少3格颜色不符，排除。')
    return {'prompt': prompt, 'figs': [f1, f2, QMARK], 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '黑白叠加', 'family': 'sty_bw',
            'params': (rule, tuple(sorted(g1))), 'diff': diff}

def verify_bw(q):
    g1, g2 = parse_bw(q['figs'][0]), parse_bw(q['figs'][1])
    # 反推规则表：用9格的输入输出对确定唯一规则
    matched_rules = []
    for name, tbl in BW_RULES.items():
        g3 = {(r, c) for r in range(3) for c in range(3)
              if tbl[('b' if (r, c) in g1 else 'w', 'b' if (r, c) in g2 else 'w')] == 'b'}
        matched_rules.append((name, g3))
    if len({frozenset(g) for _, g in matched_rules}) != len(BW_RULES):
        return []  # 样例无法唯一确定规则
    res = []
    for i, o in enumerate(q['options']):
        go = parse_bw(o)
        if any(go == g3 for _, g3 in matched_rules):
            res.append(i)
    return res

def gen_addsub(rng, diff):
    """加减同位：图1+图2=图3（并集）或 图1−图2（差集）。"""
    pool = ['circ', 'sq', 'tri', 'star', 'diam', 'pent']
    mode = rng.choice(['union', 'diff'])
    slots = rng.sample(range(6), 6)
    s1 = set(slots[:rng.randint(3, 4)])
    s2 = set(slots[3:]) & s1 if mode == 'diff' else set(slots[2:])
    if mode == 'diff':
        s2 = set(slots[2:5])
        if not (s1 & s2):
            return None
        ans_slots = s1 - s2
    else:
        s2 = set(slots[2:])
        ans_slots = s1 | s2
    if len(ans_slots) < 2:
        return None
    kinds = {s: rng.choice(pool) for s in range(6)}
    def fig_of(ss):
        return render_fig([_slot_el(kinds[s], s) for s in sorted(ss)])
    f1, f2 = fig_of(s1), fig_of(s2)
    correct = fig_of(ans_slots)
    distractors = []
    if mode == 'union':
        distractors.append(fig_of(s1 & s2) if s1 & s2 else fig_of(s1 ^ s2))
        distractors.append(fig_of(s1 - s2) if s1 - s2 else fig_of(s2 - s1))
        distractors.append(fig_of(set(range(6)) - ans_slots))
    else:
        distractors.append(fig_of(s1 & s2))
        distractors.append(fig_of(s1 | s2))
        distractors.append(fig_of(s2 - s1))
    seen = {f1, f2, correct}
    uniq_d = []
    for d in distractors:
        if d not in seen:
            uniq_d.append(d)
            seen.add(d)
    if len(uniq_d) < 3:
        return None
    opts = uniq_d[:3] + [correct]
    rng.shuffle(opts)
    ans = opts.index(correct)
    if mode == 'union':
        prompt = '图一与图二按「相加」规律叠加（所有元素保留、重合位置合并），问号处应得到什么图形？'
        expl = (f'【求同叠加】图一有{len(s1)}个元素、图二有{len(s2)}个元素，叠加取并集共{len(ans_slots)}个元素'
                f'（重合位置合并为一个）。正确选项元素数与位置均符合；其余选项分别为交集、差集或补集，排除。')
    else:
        prompt = '图一与图二按「相减」规律叠加（图一中与图二相同位置的元素消去，其余保留），问号处应得到什么图形？'
        expl = (f'【相减规律】图一{len(s1)}个元素中，与图二重合的{len(s1 & s2)}个消去，保留{len(ans_slots)}个。'
                f'正确选项即图一去掉重合部分；其余选项分别为交集、并集或反向相减，排除。')
    return {'prompt': prompt, 'figs': [f1, f2, QMARK], 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '加减同位', 'family': 'sty_addsub',
            'params': (mode, tuple(sorted(s1)), tuple(sorted(s2))), 'diff': diff}

def verify_addsub(q):
    s1 = {elem_sig(e) for e in parse_svg(q['figs'][0])}
    s2 = {elem_sig(e) for e in parse_svg(q['figs'][1])}
    # 模式由题干声明（相加/相减），独立验算对应集合运算的唯一选项
    if '相加' in q['prompt']:
        expect = s1 | s2
    elif '相减' in q['prompt']:
        expect = s1 - s2
    else:
        return []
    if not expect:
        return []
    res = []
    for i, o in enumerate(q['options']):
        s = {elem_sig(e) for e in parse_svg(o)}
        if s == expect:
            res.append(i)
    return res
