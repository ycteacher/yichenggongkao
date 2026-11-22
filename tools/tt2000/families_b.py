# -*- coding: utf-8 -*-
"""题型族B：空间类（折纸盒/三视图）、属性类（对称/曲直/开闭）、一笔画。"""
import math, random
from gen_lib import *

C = 60.0

# ============ 空间类：折纸盒 ============
# 面编号（十字展开）：
#       [0]
#   [1][2][3][4]
#       [5]
# 折叠后（2为底面）：2=底, 0=后, 5=前, 1=左, 3=右, 4=顶
# 对面：2-4, 1-3, 0-5
SYM = ['tri', 'circ', 'sq', 'star', 'plus', 'diam']
SYM_NAME = {'tri': '三角形', 'circ': '圆', 'sq': '正方形', 'star': '五角星', 'plus': '十字', 'diam': '菱形'}

# 立方体符号风格：空心（白底黑边）+ 独立线宽，保证同中心异形符号像素可辨
CUBE_SYM_S = 9        # 符号半径
CUBE_SYM_SW = 2.6     # 符号描边宽
CUBE_FACE_SW = 1.8    # 立方体棱线宽

def _cube_sym_svg(kind, cx, cy, s=None, sw=None):
    """立方体/展开图符号（空心风格）。"""
    s = CUBE_SYM_S if s is None else s
    sw = CUBE_SYM_SW if sw is None else sw
    fill = 'white'
    if kind == 'tri':
        return f'<polygon points="{pts_str(poly_pts(cx, cy, s, 3, 0))}" fill="{fill}" stroke="#1a1a1a" stroke-width="{sw}"/>'
    if kind == 'circ':
        return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{s}" fill="{fill}" stroke="#1a1a1a" stroke-width="{sw}"/>'
    if kind == 'sq':
        return f'<rect x="{cx-s:.2f}" y="{cy-s:.2f}" width="{2*s}" height="{2*s}" fill="{fill}" stroke="#1a1a1a" stroke-width="{sw}"/>'
    if kind == 'star':
        e = el_star(cx, cy, s + 1, 0)
        return f'<polygon points="{pts_str(e["pts"])}" fill="{fill}" stroke="#1a1a1a" stroke-width="{sw}"/>'
    if kind == 'plus':
        return (f'<line x1="{cx-s}" y1="{cy}" x2="{cx+s}" y2="{cy}" stroke="#1a1a1a" stroke-width="{sw}"/>'
                f'<line x1="{cx}" y1="{cy-s}" x2="{cx}" y2="{cy+s}" stroke="#1a1a1a" stroke-width="{sw}"/>')
    if kind == 'diam':
        return f'<polygon points="{pts_str(poly_pts(cx, cy, s, 4, 45))}" fill="{fill}" stroke="#1a1a1a" stroke-width="{sw}"/>'
    raise ValueError(kind)

def _fold_faces():
    """返回折叠后每个面的朝向法向量（立方体坐标）。"""
    return {2: (0, 0, -1), 0: (0, 1, 0), 5: (0, -1, 0), 1: (-1, 0, 0), 3: (1, 0, 0), 4: (0, 0, 1)}

def _corner_valid(top, front, right):
    """三个面能否构成一个可见角（顶/前/右），且手性正确。"""
    n = _fold_faces()
    if len({top, front, right}) != 3:
        return False
    faces = (top, front, right)
    # 两两不相对
    opp = {2: 4, 4: 2, 1: 3, 3: 1, 0: 5, 5: 0}
    for a in faces:
        if opp[a] in faces:
            return False
    # 手性：法向量混合积为正（右手系）
    t, f, r = n[top], n[front], n[right]
    cross = (f[1]*r[2]-f[2]*r[1], f[2]*r[0]-f[0]*r[2], f[0]*r[1]-f[1]*r[0])
    dot = t[0]*cross[0] + t[1]*cross[1] + t[2]*cross[2]
    return dot > 0

def _cube_svg(sym_map, top, front, right):
    """画等距立方体：三个可见面（顶/前/右），每面中央画符号。"""
    # 顶点（等距投影）
    def iso(x, y, z):
        return (60 + (x - y) * 0.866 * 28, 60 - (x + y) * 0.5 * 28 + (1 - z) * 48)
    A = iso(0, 0, 1); B = iso(1, 0, 1); Cc = iso(1, 1, 1); D = iso(0, 1, 1)
    E = iso(0, 0, 0); F = iso(1, 0, 0); G = iso(1, 1, 0); H = iso(0, 1, 0)
    parts = []
    def poly(pts, fill='white'):
        p = ' '.join(f'{x:.2f},{y:.2f}' for x, y in pts)
        parts.append(f'<polygon points="{p}" fill="{fill}" stroke="#1a1a1a" stroke-width="{CUBE_FACE_SW}"/>')
    poly([D, Cc, G, H])          # 前面 (0,1)-面
    poly([B, Cc, G, F])          # 右面
    poly([A, B, Cc, D])          # 顶面
    def center(pts):
        return (sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4)
    for face, pts in ((top, [A, B, Cc, D]), (front, [D, Cc, G, H]), (right, [B, Cc, G, F])):
        cx, cy = center(pts)
        parts.append(_cube_sym_svg(sym_map[face], cx, cy))
    return svg_wrap(''.join(parts))

def gen_cube(rng, diff):
    """折纸盒：展开图→立体图。"""
    syms = SYM[:]
    rng.shuffle(syms)
    sym_map = {i: syms[i] for i in range(6)}
    # 展开图
    def net_svg():
        pos = {0: (1, 0), 1: (0, 1), 2: (1, 1), 3: (2, 1), 4: (3, 1), 5: (1, 2)}
        cell = 26
        parts = []
        for face, (cx, cy) in pos.items():
            ox, oy = 6 + cx * cell, 6 + cy * cell
            parts.append(f'<rect x="{ox}" y="{oy}" width="{cell}" height="{cell}" fill="white" stroke="#1a1a1a" stroke-width="{CUBE_FACE_SW}"/>')
            k = sym_map[face]
            mx, my = ox + cell / 2, oy + cell / 2
            parts.append(_cube_sym_svg(k, mx, my, s=CUBE_SYM_S - 2))
        return svg_wrap(''.join(parts))
    # 正确选项：随机取一个合法角
    import itertools
    corners = [(t, f, r) for t in range(6) for f in range(6) for r in range(6) if _corner_valid(t, f, r)]
    top, front, right = rng.choice(corners)
    correct = _cube_svg(sym_map, top, front, right)
    # 结构区分度：任意两选项的可见(面,符号)集合交集≤1（保证像素可辨）
    def vis_set(tri):
        return frozenset((face, sym_map[face]) for face in tri)
    def pairwise_ok(cands):
        ss = [vis_set(c) for c in cands]
        return all(len(a & b) <= 1 for a, b in itertools.combinations(ss, 2))
    # 干扰：含对面组合 / 非法角 / 符号错位
    distractors = []
    d_tris = []
    invalid = [(t, f, r) for t in range(6) for f in range(6) for r in range(6)
               if (t, f, r) not in corners and len({t, f, r}) == 3]
    opp = {2: 4, 4: 2, 1: 3, 3: 1, 0: 5, 5: 0}
    opp_pairs = [(t, f, r) for t in range(6) for f in range(6) for r in range(6)
                 if len({t, f, r}) == 3 and (opp[t] == f or opp[f] == r or opp[t] == r)]
    pool = opp_pairs + invalid
    rng.shuffle(pool)
    for t, f, r in pool:
        if len(distractors) >= 2:
            break
        if not pairwise_ok([tuple(sorted((top, front, right))), (t, f, r)] + d_tris):
            continue
        d = _cube_svg(sym_map, t, f, r)
        if d != correct and d not in distractors:
            distractors.append(d)
            d_tris.append((t, f, r))
    # 符号错位干扰：交换两个可见面符号（两符号位置都改变）
    swaps = [(a, b) for a in range(6) for b in range(6)
             if a < b and a in (top, front, right) and b in (top, front, right)]
    rng.shuffle(swaps)
    for a, b in swaps:
        if len(distractors) >= 3:
            break
        sm2 = dict(sym_map)
        sm2[a], sm2[b] = sm2[b], sm2[a]
        tri = tuple(sorted((top, front, right)))
        vis2 = frozenset((face, sm2[face]) for face in tri)
        if any(len(vis2 & s2) > 1 for s2 in [vis_set(tri)] + [vis_set(d) for d in d_tris]):
            continue
        d = _cube_svg(sm2, top, front, right)
        if d != correct and d not in distractors:
            distractors.append(d)
            d_tris.append(tri)
    if len(distractors) < 3:
        return None
    opts = distractors[:3] + [correct]
    rng.shuffle(opts)
    ans = opts.index(correct)
    prompt = '左边是给定纸盒的外表面展开图，右边四项中哪一项能由它折叠而成？'
    face_names = {0: '后面', 5: '前面', 1: '左面', 3: '右面', 4: '顶面', 2: '底面'}
    expl = (f'【折纸盒】展开图折叠后：{SYM_NAME[sym_map[2]]}（底）与{SYM_NAME[sym_map[4]]}（顶）相对，'
            f'{SYM_NAME[sym_map[1]]}（左）与{SYM_NAME[sym_map[3]]}（右）相对，'
            f'{SYM_NAME[sym_map[0]]}（后）与{SYM_NAME[sym_map[5]]}（前）相对，相对面不能同时可见。'
            f'正确选项展示的三个面两两相邻且符号方位与展开图一致；'
            f'干扰项中有的让相对面同时出现、有的符号错位，排除。')
    return {'prompt': prompt, 'figs': [net_svg()], 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '折纸盒', 'family': 'spa_cube',
            'params': (tuple(syms),), 'diff': diff}

def _sym_groups(root):
    """把SVG元素按中心聚类成符号组，返回[(cx,cy,kind)]。"""
    items = []
    for el in root.iter():
        if el.tag == NS + 'polygon':
            pts = [(float(a), float(b)) for a, b in (p.split(',') for p in el.get('points').split())]
            c = centroid(pts)
            spread = max(max(p[0] for p in pts) - min(p[0] for p in pts),
                         max(p[1] for p in pts) - min(p[1] for p in pts))
            if spread > 30:
                continue  # 立方体大面，不是符号
            kind = {3: 'tri', 4: 'diam', 10: 'star'}.get(len(pts))
            if kind:
                items.append((c[0], c[1], kind))
        elif el.tag == NS + 'circle':
            items.append((float(el.get('cx')), float(el.get('cy')), 'circ'))
        elif el.tag == NS + 'rect':
            x, y = float(el.get('x')), float(el.get('y'))
            w, h = float(el.get('width')), float(el.get('height'))
            if w >= 119:
                continue
            if 8 < w < 24 and 8 < h < 24:
                items.append((x + w / 2, y + h / 2, 'sq'))
        elif el.tag == NS + 'line':
            items.append(((float(el.get('x1')) + float(el.get('x2'))) / 2,
                          (float(el.get('y1')) + float(el.get('y2'))) / 2, 'halfplus'))
    # 聚类：中心相近的合并（十字=两条线）
    groups = []
    for cx, cy, kind in items:
        for g in groups:
            if abs(g[0] - cx) < 3 and abs(g[1] - cy) < 3:
                if kind == 'halfplus':
                    g[2] = 'plus' if g[2] in ('halfplus', 'plus') else g[2]
                break
        else:
            groups.append([cx, cy, kind])
    return [(g[0], g[1], g[2]) for g in groups if g[2] != 'halfplus']

def verify_cube(q):
    """独立验算：解析展开图符号→面映射，再解析每个选项的可见三角，
    判断该符号组合是否构成合法角（两两不相对+手性正确）。"""
    net = q['figs'][0]
    root = ET.fromstring(net)
    pos = {(1, 0): 0, (0, 1): 1, (1, 1): 2, (2, 1): 3, (3, 1): 4, (1, 2): 5}
    cell = 26
    face_syms = {}
    for cx, cy, kind in _sym_groups(root):
        col, row = int((cx - 6) // cell), int((cy - 6) // cell)
        face = pos.get((col, row))
        if face is not None:
            face_syms[face] = kind
    if len(face_syms) != 6 or len(set(face_syms.values())) != 6:
        return []
    sym2face = {v: k for k, v in face_syms.items()}
    res = []
    for i, o in enumerate(q['options']):
        try:
            oroot = ET.fromstring(o)
            syms = _sym_groups(oroot)
        except Exception:
            return []
        if len(syms) != 3:
            continue  # 该选项符号不完整，视为无效
        syms.sort(key=lambda s: (s[1], s[0]))
        top = syms[0]
        rest = sorted(syms[1:], key=lambda s: s[0])
        t = sym2face.get(top[2])
        f = sym2face.get(rest[0][2])
        r = sym2face.get(rest[1][2])
        if t is None or f is None or r is None:
            return []
        if _corner_valid(t, f, r):
            res.append(i)
    return res

# ============ 空间类：三视图 ============

def _voxel_svg(heights):
    """斜二测画法：heights[x][y] 为柱高(0-3)。x:0-2 左→右, y:0-2 前→后。"""
    parts = []
    cw, ch = 24, 24
    for y in range(2, -1, -1):      # 后排先画
        for x in range(3):
            h = heights[x][y]
            for z in range(h):
                ox = 22 + x * cw * 0.85 - y * 10
                oy = 94 - x * 8 - y * 14 - z * ch
                parts.append(f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{cw}" height="{ch}" fill="white" stroke="#1a1a1a" stroke-width="2.5"/>')
    return svg_wrap(''.join(parts))

def _front_svg(heights):
    """主视图（从前看）：每列x的最大高度。"""
    parts = []
    cw = 30
    for x in range(3):
        hmax = max(heights[x][y] for y in range(3))
        for z in range(hmax):
            ox, oy = 15 + x * cw, 100 - (z + 1) * 30
            parts.append(f'<rect x="{ox}" y="{oy}" width="{cw}" height="{cw}" fill="white" stroke="#1a1a1a" stroke-width="2.8"/>')
    return svg_wrap(''.join(parts))

def gen_frontview(rng, diff):
    """三视图：给出立体图，选主视图。"""
    while True:
        heights = [[rng.randint(0, 3) for _ in range(3)] for _ in range(3)]
        if sum(sum(r) for r in heights) >= 6 and any(heights[x][y] > 0 for x in range(3) for y in range(3)):
            break
    stem = _voxel_svg(heights)
    proj = [max(heights[x][y] for y in range(3)) for x in range(3)]
    correct = _front_svg(heights)
    distractors = []
    tries = 0
    while len(distractors) < 3 and tries < 60:
        tries += 1
        bad = proj[:]
        cols = rng.sample(range(3), 2)
        for i in cols:
            bad[i] = rng.choice([h for h in range(4) if h != bad[i]])
        if bad == proj:
            continue
        d = sum(1 for a, b in zip(bad, proj) if a != b)
        if d < 2:
            continue
        fake = [[0] * 3 for _ in range(3)]
        for x in range(3):
            for z in range(bad[x]):
                fake[x][0] = max(fake[x][0], z + 1)
        dd = _front_svg(fake)
        if dd != correct and dd not in distractors:
            distractors.append(dd)
    if len(distractors) < 3:
        return None
    opts = distractors[:3] + [correct]
    rng.shuffle(opts)
    ans = opts.index(correct)
    prompt = '左边是立体图形（斜二测画法），从正前方（箭头方向）观察，得到的主视图是：'
    expl = (f'【三视图】主视图=从前向后看每列的最大高度：左列{proj[0]}层、中列{proj[1]}层、右列{proj[2]}层。'
            f'正确选项三列高度依次为 {proj[0]}、{proj[1]}、{proj[2]}；'
            f'其余选项至少一列高度不符（被前排遮挡或漏数），排除。')
    return {'prompt': prompt, 'figs': [stem], 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '三视图', 'family': 'spa_view',
            'params': (tuple(tuple(r) for r in heights),), 'diff': diff}

def verify_frontview(q):
    """验算：从立体图SVG按斜二测公式反解每柱高度，重算主视图与选项比对。"""
    svg = q['figs'][0]
    root = ET.fromstring(svg)
    heights = [[0] * 3 for _ in range(3)]
    for el in root.iter():
        if el.tag == NS + 'rect':
            x, y = float(el.get('x')), float(el.get('y'))
            w = float(el.get('width'))
            if w >= 119:
                continue
            if abs(w - 24) > 1:
                return []
            # 反解 (gx, gy, z)：ox = 22 + 20.4gx - 10gy；oy = 94 - 8gx - 14gy - 24z
            found = False
            for gy in range(3):
                for gx in range(3):
                    ox = 22 + gx * 20.4 - gy * 10
                    if abs(ox - x) > 1.0:
                        continue
                    z = (94 - 8 * gx - 14 * gy - y) / 24
                    if abs(z - round(z)) < 0.1 and 0 <= round(z) <= 2:
                        heights[gx][gy] = max(heights[gx][gy], round(z) + 1)
                        found = True
            if not found:
                return []
    proj = [max(heights[x][y] for y in range(3)) for x in range(3)]
    def opt_proj(o):
        root2 = ET.fromstring(o)
        zs = {}
        for el in root2.iter():
            if el.tag == NS + 'rect':
                x, y = float(el.get('x')), float(el.get('y'))
                if float(el.get('width')) >= 119:
                    continue
                col = int(round((x - 15) / 30))
                z = (100 - y) / 30 - 1
                if abs(z - round(z)) > 0.1 or not (0 <= round(z) <= 3):
                    return None
                zs.setdefault(col, set()).add(round(z))
        out = []
        for c in range(3):
            s = zs.get(c)
            out.append(max(s) + 1 if s else 0)
        return out
    res = []
    for i, o in enumerate(q['options']):
        p = opt_proj(o)
        if p == proj:
            res.append(i)
    return res

# ============ 属性类 ============

def gen_symmetry(rng, diff):
    """对称性：题干图形均轴对称，选同样轴对称的选项。"""
    axis = rng.choice(['v', 'h'])
    n_stem = 3
    figs = []
    stem_kinds = []
    for _ in range(n_stem):
        kind = rng.choice(['tri_iso', 'sq', 'circ', 'pent_iso', 'star', 'diam', 'hex'])
        stem_kinds.append(kind)
        figs.append(render_fig([_sym_el(kind, axis)]))
    correct_kind = rng.choice(['tri_iso', 'sq', 'circ', 'pent_iso', 'star', 'diam', 'hex'])
    correct = render_fig([_sym_el(correct_kind, axis)])
    # 干扰：不对称图形（带偏移标记）
    distractors = []
    base_kinds = ['tri_s', 'quad_s', 'lshape', 'flag']
    rng.shuffle(base_kinds)
    for k in base_kinds:
        if len(distractors) >= 3:
            break
        d = render_fig([_sym_el(k, None)])
        if d != correct and not _fig_axis_symmetric(d):
            distractors.append(d)
    if len(distractors) < 3:
        return None
    opts = distractors[:3] + [correct]
    rng.shuffle(opts)
    ans = opts.index(correct)
    an = '左右' if axis == 'v' else '上下'
    prompt = f'题干中的图形都具有{an}对称性（沿{an}方向的对称轴折叠后两侧重合）。四个选项中同样具有该对称性的是：'
    expl = (f'【对称性】题干三个图形均关于{an}方向对称轴成轴对称。'
            f'逐项检验：正确选项沿{an}对称轴折叠后两侧完全重合；'
            f'其余三个图形均不对称（带偏移标记/不规则轮廓），排除。')
    return {'prompt': prompt, 'figs': figs, 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '对称性', 'family': 'attr_sym',
            'params': (axis, correct_kind, tuple(stem_kinds)), 'diff': diff}

def _sym_el(kind, axis):
    """生成对称/不对称元素。axis=None 时不保证对称。"""
    if kind == 'tri_iso':
        return {'tag': 'polygon', 'pts': [(60, 35), (35, 85), (85, 85)]}
    if kind == 'sq':
        return el_rect(C, C, 44, 44)
    if kind == 'circ':
        return el_circle(C, C, 24)
    if kind == 'pent_iso':
        return el_polygon(C, C, 26, 5, 0)
    if kind == 'star':
        return el_star(C, C, 26, 0)
    if kind == 'diam':
        return el_polygon(C, C, 26, 4, 45)
    if kind == 'hex':
        return el_polygon(C, C, 26, 6, 0)
    if kind == 'tri_s':  # 不对称：斜三角形
        return {'tag': 'polygon', 'pts': [(40, 35), (30, 85), (88, 70)]}
    if kind == 'quad_s':  # 不对称：不规则四边形
        return {'tag': 'polygon', 'pts': [(35, 40), (80, 30), (90, 75), (30, 80)]}
    if kind == 'lshape':  # 不对称：不等臂L形
        return {'tag': 'polygon', 'pts': [(40, 35), (40, 85), (85, 85), (85, 62), (62, 62), (62, 35)]}
    if kind == 'flag':  # 旗形（带偏移杆）
        return [{'tag': 'line', 'x1': 45, 'y1': 30, 'x2': 45, 'y2': 90},
                {'tag': 'polygon', 'pts': [(45, 30), (85, 40), (45, 52)]}]
    raise ValueError(kind)

def _fig_axis_symmetric(svg):
    """整图是否轴对称（v或h）：所有元素均对称。圆恒对称；矩形看v/h；多边形逐点检验。"""
    for e in parse_svg(svg):
        if e['tag'] == 'circle':
            continue
        if e['tag'] == 'rect':
            if not (abs(e['cx'] - C) < 1.5 and abs(e['cy'] - C) < 1.5):
                return False
            continue
        if e['tag'] == 'polygon':
            if not (is_axially_symmetric(e['pts'], 'v') or is_axially_symmetric(e['pts'], 'h')):
                return False
        else:
            return False
    return True

def verify_symmetry(q):
    """验算：题干图形均轴对称（v或h），且恰有一个选项轴对称。"""
    for f in q['figs']:
        if not _fig_axis_symmetric(f):
            return []
    res = []
    for i, o in enumerate(q['options']):
        if _fig_axis_symmetric(o):
            res.append(i)
    return res

def gen_curved(rng, diff):
    """曲直性：题干图形全直线或全含曲线，选同类。"""
    curved = rng.random() < 0.5
    figs = []
    fig_sigs = []
    for _ in range(3):
        if curved:
            r1 = rng.uniform(18, 28)
            els = [el_circle(C, C, r1)]
            sig = round(r1)
            if rng.random() < 0.5:
                r2 = rng.uniform(8, 14)
                els.append(el_circle(C, C, r2))
                sig = (sig, round(r2))
        else:
            n = rng.randint(3, 6)
            rot = rng.uniform(0, 90)
            els = [el_polygon(C, C, 24, n, rot)]
            sig = (n, round(rot))
        fig_sigs.append(sig)
        figs.append(render_fig(els))
    correct = render_fig([el_circle(C, C, 24)] if curved else [el_polygon(C, C, 24, rng.randint(3, 6), rng.uniform(0, 90))])
    distractors = []
    tries = 0
    while len(distractors) < 3 and tries < 30:
        tries += 1
        if curved:
            d = render_fig([el_polygon(C, C, 24, rng.randint(3, 6), rng.uniform(0, 90))])
        else:
            d = render_fig([el_circle(C, C, rng.uniform(16, 28))])
        if d != correct and d not in distractors:
            distractors.append(d)
    if len(distractors) < 3:
        return None
    opts = distractors[:3] + [correct]
    rng.shuffle(opts)
    ans = opts.index(correct)
    t = '全由曲线构成（含圆/弧）' if curved else '全由直线段构成（无曲线）'
    tt = '全由曲线构成' if curved else '全由直线构成'
    prompt = f'题干中的图形{t}。四个选项中同样{tt}的是：'
    expl = (f'【曲直性】题干三个图形{t}。逐项检验轮廓线条：正确选项同样{"含曲线" if curved else "只含直线"}；'
            f'其余选项{"为纯直线图形" if curved else "含圆弧曲线"}，与题干属性不符，排除。')
    return {'prompt': prompt, 'figs': figs, 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '曲直性', 'family': 'attr_curve',
            'params': (curved, tuple(fig_sigs)), 'diff': diff}

def verify_curved(q):
    def is_curved(f):
        return has_curve(parse_svg(f))
    stem_curved = [is_curved(f) for f in q['figs']]
    if len(set(stem_curved)) != 1:
        return []
    res = []
    for i, o in enumerate(q['options']):
        if is_curved(o) == stem_curved[0]:
            res.append(i)
    return res

def gen_closed(rng, diff):
    """开闭性：题干全封闭或全开放，选同类。"""
    closed = rng.random() < 0.5
    figs = []
    fig_sigs = []
    for _ in range(3):
        if closed:
            n = rng.randint(3, 6)
            rr = rng.uniform(0, 60)
            fig_sigs.append((n, round(rr)))
            figs.append(render_fig([el_polygon(C, C, 24, n, rr)]))
        else:
            # 开放折线
            pts = []
            a = rng.uniform(0, 2 * math.pi)
            x, y = rng.uniform(30, 50), rng.uniform(30, 50)
            for i in range(rng.randint(3, 4)):
                pts.append((x, y))
                a += rng.uniform(0.6, 2.2)
                x = min(max(x + 28 * math.cos(a), 15), 105)
                y = min(max(y + 28 * math.sin(a), 15), 105)
            els = []
            for i in range(len(pts) - 1):
                els.append(el_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]))
            fig_sigs.append((round(a, 1), round(x), round(y)))
            figs.append(render_fig(els))
    correct = render_fig([el_polygon(C, C, 24, rng.randint(3, 6), rng.uniform(0, 60))]) if closed else None
    if not closed:
        pts = []
        a = rng.uniform(0, 2 * math.pi)
        x, y = rng.uniform(30, 50), rng.uniform(30, 50)
        for i in range(rng.randint(3, 4)):
            pts.append((x, y))
            a += rng.uniform(0.6, 2.2)
            x = min(max(x + 28 * math.cos(a), 15), 105)
            y = min(max(y + 28 * math.sin(a), 15), 105)
        els = [el_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(len(pts) - 1)]
        correct = render_fig(els)
    distractors = []
    tries = 0
    while len(distractors) < 3 and tries < 30:
        tries += 1
        if closed:
            # 干扰项为开放折线（与题干封闭相反）
            pts = []
            a = rng.uniform(0, 2 * math.pi)
            x, y = rng.uniform(30, 50), rng.uniform(30, 50)
            for i in range(rng.randint(3, 4)):
                pts.append((x, y))
                a += rng.uniform(0.6, 2.2)
                x = min(max(x + 28 * math.cos(a), 15), 105)
                y = min(max(y + 28 * math.sin(a), 15), 105)
            els = [el_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(len(pts) - 1)]
            d = render_fig(els)
        else:
            d = render_fig([el_polygon(C, C, 24, rng.randint(3, 6), rng.uniform(0, 60))])
        if d != correct and d not in distractors:
            distractors.append(d)
    if len(distractors) < 3:
        return None
    opts = distractors[:3] + [correct]
    rng.shuffle(opts)
    ans = opts.index(correct)
    t = '都是封闭图形（线条首尾相接围成区域）' if closed else '都是开放图形（线条未首尾相接）'
    prompt = f'题干中的图形{t}。四个选项中同样属于{"封闭" if closed else "开放"}图形的是：'
    expl = (f'【开闭性】题干三个图形{t}。逐项检验线条是否首尾相接：正确选项同样{"封闭" if closed else "开放"}；'
            f'其余选项{"为开放折线" if closed else "为封闭图形"}，与题干属性不符，排除。')
    return {'prompt': prompt, 'figs': figs, 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '开闭性', 'family': 'attr_closed',
            'params': (closed, tuple(fig_sigs)), 'diff': diff}

def verify_closed(q):
    def is_closed_fig(f):
        return is_closed(parse_svg(f))
    stem = [is_closed_fig(f) for f in q['figs'] if parse_svg(f)]
    if not stem or len(set(stem)) != 1:
        return []
    res = []
    for i, o in enumerate(q['options']):
        if is_closed_fig(o) == stem[0]:
            res.append(i)
    return res

# ============ 一笔画 ============

def _line_fig(segs):
    return render_fig([el_line(*s) for s in segs])

def _affine_segs(segs, rng):
    """对线段组做随机旋转/缩放/平移（保持图结构）。"""
    ang = rng.uniform(0, 2 * math.pi)
    sc = rng.uniform(0.85, 1.12)
    tx, ty = rng.uniform(-8, 8), rng.uniform(-8, 8)
    ca, sa = math.cos(ang), math.sin(ang)
    out = []
    for x1, y1, x2, y2 in segs:
        def tr(p):
            return (60 + (p[0] - 60) * sc * ca - (p[1] - 60) * sc * sa + tx,
                    60 + (p[0] - 60) * sc * sa + (p[1] - 60) * sc * ca + ty)
        a, b = tr((x1, y1)), tr((x2, y2))
        out.append((a[0], a[1], b[0], b[1]))
    return out

def gen_euler(rng, diff):
    """一笔画：题干可一笔画；选项恰一个可一笔画（其余奇点≥4或不连通）。"""
    # 题干：经典可一笔画图形（生成后验算）
    stem_kind = rng.choice(['rect_diag', 'triangle_mid', 'hourglass', 'pentagram'])
    if stem_kind == 'rect_diag':
        segs = [(30, 30, 90, 30), (90, 30, 90, 90), (90, 90, 30, 90), (30, 90, 30, 30), (30, 30, 90, 90)]
    elif stem_kind == 'triangle_mid':
        segs = [(60, 25, 25, 90), (25, 90, 95, 90), (95, 90, 60, 25), (60, 25, 60, 90)]
    elif stem_kind == 'hourglass':
        segs = [(30, 30, 90, 30), (30, 30, 90, 90), (90, 90, 30, 90), (30, 90, 90, 30), (30, 30, 30, 90), (90, 30, 90, 90)]
    else:
        pts5 = poly_pts(C, C, 40, 5, 0)
        order = [(0, 2), (2, 4), (4, 1), (1, 3), (3, 0)]
        segs = [(pts5[i][0], pts5[i][1], pts5[j][0], pts5[j][1]) for i, j in order]
    ang = rng.uniform(0, 360)
    sc = rng.uniform(85, 112)
    segs = _affine_segs(segs, rng)
    stem = _line_fig(segs)
    if not eulerian(build_graph(parse_svg(stem))):
        return None
    # 正确选项：另一个可一笔画图形
    correct_kind = rng.choice([k for k in ['rect_diag', 'triangle_mid', 'hourglass', 'pentagram', 'double_tri'] if k != stem_kind])
    if correct_kind == 'double_tri':
        segs_c = [(30, 40, 90, 40), (30, 40, 60, 85), (60, 85, 90, 40), (60, 85, 30, 80), (30, 80, 90, 80), (90, 80, 60, 35)]
    elif correct_kind == 'rect_diag':
        segs_c = [(30, 30, 90, 30), (90, 30, 90, 90), (90, 90, 30, 90), (30, 90, 30, 30), (30, 30, 90, 90)]
    elif correct_kind == 'triangle_mid':
        segs_c = [(60, 25, 25, 90), (25, 90, 95, 90), (95, 90, 60, 25), (60, 25, 60, 90)]
    elif correct_kind == 'hourglass':
        segs_c = [(30, 30, 90, 30), (30, 30, 90, 90), (90, 90, 30, 90), (30, 90, 90, 30), (30, 30, 30, 90), (90, 30, 90, 90)]
    else:
        pts5 = poly_pts(C, C, 40, 5, 0)
        order = [(0, 2), (2, 4), (4, 1), (1, 3), (3, 0)]
        segs_c = [(pts5[i][0], pts5[i][1], pts5[j][0], pts5[j][1]) for i, j in order]
    segs_c = _affine_segs(segs_c, rng)
    correct = _line_fig(segs_c)
    if not eulerian(build_graph(parse_svg(correct))):
        return None
    # 干扰：奇点≥4 或不连通
    distractors = []
    cand_bad = [
        # 四个角+对角线两条 → 4奇点
        [(30, 30, 90, 30), (90, 30, 90, 90), (90, 90, 30, 90), (30, 90, 30, 30), (30, 30, 90, 90), (30, 90, 90, 30)],
        # 两个分离图形
        [(25, 25, 55, 25), (25, 25, 25, 55), (25, 55, 55, 55), (55, 55, 55, 25), (70, 70, 100, 70), (70, 70, 70, 100), (70, 100, 100, 100), (100, 100, 100, 70)],
        # 米字（中心+4角，8奇点）
        [(30, 30, 90, 90), (90, 30, 30, 90), (60, 30, 60, 90), (30, 60, 90, 60)],
        # 三角形+内部十字（多奇点）
        [(60, 25, 25, 90), (25, 90, 95, 90), (95, 90, 60, 25), (60, 25, 60, 90), (25, 90, 95, 90)],
    ]
    rng.shuffle(cand_bad)
    for segs_b in cand_bad:
        if len(distractors) >= 3:
            break
        d = _line_fig(segs_b)
        g = build_graph(parse_svg(d))
        if not eulerian(g):
            distractors.append(d)
    if len(distractors) < 3:
        return None
    opts = distractors[:3] + [correct]
    rng.shuffle(opts)
    ans = opts.index(correct)
    prompt = '下列四个图形中，只有一项可以不重复地一笔画成（每条线只经过一次）。它是：'
    expl = ('【一笔画】一笔画判定：图形连通且奇点（引出奇数条线的点）数为0或2。'
            '正确选项连通且奇点数为2（或0），可一笔画；'
            '其余选项奇点数≥4（需两笔以上）或由多个不连通部分组成，均不可一笔画，排除。')
    return {'prompt': prompt, 'figs': [stem], 'options': opts, 'correct_svg': correct,
            'explanation': expl, '__sub': '一笔画', 'family': 'euler',
            'params': (stem_kind, correct_kind, round(ang), round(sc)), 'diff': diff}

def verify_euler(q):
    """验算：题干可一笔画，且选项中恰一个可一笔画。"""
    if not eulerian(build_graph(parse_svg(q['figs'][0]))):
        return []
    res = []
    for i, o in enumerate(q['options']):
        if eulerian(build_graph(parse_svg(o))):
            res.append(i)
    return res
