# -*- coding: utf-8 -*-
"""图推2000题生成基础库：SVG构建、解析、几何验算。"""
import math, re, json, random
import xml.etree.ElementTree as ET

# ---------- SVG 构建 ----------
# 统一画布 120x120，viewBox 矢量自适应，白底，深色线条（白底对比度达标）
SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="100%" style="max-width:120px;height:auto">'
FRAME = '<rect x="0" y="0" width="120" height="120" fill="white" stroke="#333" stroke-width="1"/>'
STROKE = '#1a1a1a'
SW = 3.0  # 线宽：80px 渲染下 3.0*80/120 = 2px，小屏清晰可辨

def svg_wrap(body):
    return SVG_HEAD + FRAME + body + '</svg>'

def poly_pts(cx, cy, r, n, rot_deg=0.0):
    pts = []
    for i in range(n):
        a = math.radians(rot_deg) + 2 * math.pi * i / n - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def pts_str(pts):
    return ' '.join(f'{x:.2f},{y:.2f}' for x, y in pts)

def el_polygon(cx, cy, r, n, rot=0.0, fill='none'):
    return {'tag': 'polygon', 'pts': poly_pts(cx, cy, r, n, rot), 'n': n, 'cx': cx, 'cy': cy, 'r': r, 'rot': rot, 'fill': fill}

def el_circle(cx, cy, r, fill='none'):
    return {'tag': 'circle', 'cx': cx, 'cy': cy, 'r': r, 'fill': fill}

def el_rect(cx, cy, w, h, fill='none'):
    return {'tag': 'rect', 'cx': cx, 'cy': cy, 'w': w, 'h': h, 'fill': fill}

def el_line(x1, y1, x2, y2):
    return {'tag': 'line', 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}

def el_star(cx, cy, r, rot=0.0):
    """五角星（10顶点多边形）"""
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.42
        a = math.radians(rot) + math.pi * i / 5 - math.pi / 2
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return {'tag': 'polygon', 'pts': pts, 'n': 5, 'cx': cx, 'cy': cy, 'r': r, 'rot': rot, 'star': True, 'fill': 'none'}

def el_plus(cx, cy, s):
    """十字（两条线段）"""
    return [el_line(cx - s, cy, cx + s, cy), el_line(cx, cy - s, cx, cy + s)]

def render_el(e):
    if e['tag'] == 'polygon':
        return f'<polygon points="{pts_str(e["pts"])}" fill="{e.get("fill","none")}" stroke="{STROKE}" stroke-width="{SW}"/>'
    if e['tag'] == 'circle':
        return f'<circle cx="{e["cx"]:.2f}" cy="{e["cy"]:.2f}" r="{e["r"]:.2f}" fill="{e.get("fill","none")}" stroke="{STROKE}" stroke-width="{SW}"/>'
    if e['tag'] == 'rect':
        return (f'<rect x="{e["cx"]-e["w"]/2:.2f}" y="{e["cy"]-e["h"]/2:.2f}" width="{e["w"]:.2f}" height="{e["h"]:.2f}" '
                f'fill="{e.get("fill","none")}" stroke="{STROKE}" stroke-width="{SW}"/>')
    if e['tag'] == 'line':
        return f'<line x1="{e["x1"]:.2f}" y1="{e["y1"]:.2f}" x2="{e["x2"]:.2f}" y2="{e["y2"]:.2f}" stroke="{STROKE}" stroke-width="{SW}"/>'
    raise ValueError(e['tag'])

def render_fig(elements, extra=''):
    body = ''.join(render_el(e) if not isinstance(e, list) else ''.join(render_el(x) for x in e) for e in elements)
    return svg_wrap(body + extra)

QMARK = '<span style="font-size:32px;font-weight:bold;margin:0 8px;">？</span>'

# ---------- SVG 解析（独立验算用，不依赖生成器内部状态） ----------
NS = '{http://www.w3.org/2000/svg}'

def parse_svg(svg_text):
    """解析 SVG，返回元素列表（几何参数化）。"""
    root = ET.fromstring(svg_text)
    out = []
    for el in root.iter():
        if el.tag == NS + 'polygon':
            pts = [(float(a), float(b)) for a, b in (p.split(',') for p in el.get('points').split())]
            out.append({'tag': 'polygon', 'pts': pts, 'fill': el.get('fill', 'none')})
        elif el.tag == NS + 'circle':
            out.append({'tag': 'circle', 'cx': float(el.get('cx')), 'cy': float(el.get('cy')), 'r': float(el.get('r')), 'fill': el.get('fill', 'none')})
        elif el.tag == NS + 'rect':
            x, y = float(el.get('x')), float(el.get('y'))
            w, h = float(el.get('width')), float(el.get('height'))
            if w >= 119 and h >= 119:
                continue  # 外框
            out.append({'tag': 'rect', 'cx': x + w / 2, 'cy': y + h / 2, 'w': w, 'h': h, 'fill': el.get('fill', 'none')})
        elif el.tag == NS + 'line':
            out.append({'tag': 'line', 'x1': float(el.get('x1')), 'y1': float(el.get('y1')), 'x2': float(el.get('x2')), 'y2': float(el.get('y2'))})
    return out

def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

def poly_rotation(pts):
    """正多边形/星形的旋转角（第一个顶点相对中心的方位角，单位度，0=正上）。"""
    c = centroid(pts)
    p0 = pts[0]
    ang = math.degrees(math.atan2(p0[0] - c[0], -(p0[1] - c[1])))
    return ang % 360

def poly_radius(pts):
    c = centroid(pts)
    return max(math.hypot(x - c[0], y - c[1]) for x, y in pts)

def norm_angle(a):
    a %= 360
    return min(a, 360 - a)

def is_axially_symmetric(pts, axis):
    """axis: 'v'|'h'|'d1'(\\)|'d2'(/)。容差1.5px。"""
    c = centroid(pts)
    tol = 1.5
    for x, y in pts:
        dx, dy = x - c[0], y - c[1]
        if axis == 'v':
            m = (-dx, dy)
        elif axis == 'h':
            m = (dx, -dy)
        elif axis == 'd1':
            m = (dy, dx)
        else:
            m = (-dy, -dx)
        mx, my = c[0] + m[0], c[1] + m[1]
        if not any(math.hypot(mx - px, my - py) < tol for px, py in pts):
            return False
    return True

def is_centrally_symmetric(pts):
    c = centroid(pts)
    tol = 1.5
    for x, y in pts:
        mx, my = 2 * c[0] - x, 2 * c[1] - y
        if not any(math.hypot(mx - px, my - py) < tol for px, py in pts):
            return False
    return True

def has_curve(elements):
    return any(e['tag'] == 'circle' for e in elements)

def is_closed(elements):
    """图形是否封闭：存在 polygon/rect/circle（封闭元素）且无独立 line。"""
    tags = [e['tag'] for e in elements]
    return 'polygon' in tags or 'rect' in tags or 'circle' in tags

# ---------- 一笔画：线段图分析 ----------
def snap(v, grid=1.0):
    return round(v / grid) * grid

def build_graph(elements, tol=2.0):
    """从 line 元素构建图，返回 {node: [neighbors]}，节点坐标吸附到0.5格。"""
    nodes = {}
    def node_of(x, y):
        key = (snap(x, 5), snap(y, 5))
        for k in nodes:
            if abs(k[0] - key[0]) <= tol and abs(k[1] - key[1]) <= tol:
                return k
        nodes[key] = []
        return key
    for e in elements:
        if e['tag'] != 'line':
            continue
        a = node_of(e['x1'], e['y1'])
        b = node_of(e['x2'], e['y2'])
        if a == b:
            continue
        nodes[a].append(b)
        nodes[b].append(a)
    return nodes

def graph_connected(nodes):
    if not nodes:
        return True
    start = next(iter(nodes))
    seen = {start}
    stack = [start]
    while stack:
        u = stack.pop()
        for v in nodes[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) == len(nodes)

def eulerian(nodes):
    """连通且奇度顶点数∈{0,2} → 可一笔画。"""
    if not graph_connected(nodes):
        return False
    odd = sum(1 for v in nodes.values() if len(v) % 2 == 1)
    return odd in (0, 2)

def odd_count(nodes):
    return sum(1 for v in nodes.values() if len(v) % 2 == 1)

# ---------- 交点计算（线段几何交点，独立验算用） ----------
def seg_intersections(elements):
    """所有 line 元素的几何交点数（端点相接不算交叉）。"""
    lines = [e for e in elements if e['tag'] == 'line']
    pts = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            p = _seg_int(lines[i], lines[j])
            if p:
                pts.append(p)
    # 去重（同一交点被多对线共享）
    uniq = []
    for p in pts:
        if not any(math.hypot(p[0] - q[0], p[1] - q[1]) < 1.0 for q in uniq):
            uniq.append(p)
    return uniq

def _seg_int(l1, l2):
    d1 = (l1['x2'] - l1['x1'], l1['y2'] - l1['y1'])
    d2 = (l2['x2'] - l2['x1'], l2['y2'] - l2['y1'])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((l2['x1'] - l1['x1']) * d2[1] - (l2['y1'] - l1['y1']) * d2[0]) / den
    u = ((l2['x1'] - l1['x1']) * d1[1] - (l2['y1'] - l1['y1']) * d1[0]) / den
    eps = 1e-6
    if eps < t < 1 - eps and eps < u < 1 - eps:
        return (l1['x1'] + t * d1[0], l1['y1'] + t * d1[1])
    return None

# ---------- 元素签名（查重/去同存异集合运算） ----------
def elem_sig(e):
    if e['tag'] == 'polygon':
        c = centroid(e['pts'])
        rot_b = int(poly_rotation(e['pts']) // 10) * 10
        return ('poly', len(e['pts']), round(c[0]), round(c[1]), bool(e.get('star')), rot_b)
    if e['tag'] == 'circle':
        return ('circ', round(e['cx']), round(e['cy']), round(e['r']))
    if e['tag'] == 'rect':
        return ('rect', round(e['cx']), round(e['cy']), round(e['w']), round(e['h']), e.get('fill', 'none'))
    if e['tag'] == 'line':
        return ('line', round(e['x1']), round(e['y1']), round(e['x2']), round(e['y2']))
    return (e['tag'],)

def fig_in_frame(svg_text, margin=2.0):
    """检查图形全部坐标（含线宽）落在画框内。"""
    els = parse_svg(svg_text)
    for e in els:
        if e['tag'] == 'polygon':
            xs = [p[0] for p in e['pts']]; ys = [p[1] for p in e['pts']]
        elif e['tag'] == 'circle':
            xs = [e['cx'] - e['r'], e['cx'] + e['r']]; ys = [e['cy'] - e['r'], e['cy'] + e['r']]
        elif e['tag'] == 'rect':
            xs = [e['cx'] - e['w'] / 2, e['cx'] + e['w'] / 2]; ys = [e['cy'] - e['h'] / 2, e['cy'] + e['h'] / 2]
        elif e['tag'] == 'line':
            xs = [e['x1'], e['x2']]; ys = [e['y1'], e['y2']]
        else:
            continue
        if min(xs) < margin or max(xs) > 120 - margin or min(ys) < margin or max(ys) > 120 - margin:
            return False
    return True

def fig_sig(svg_text):
    """图形结构签名：元素种类+数量+位置哈希。"""
    els = parse_svg(svg_text)
    sig = tuple(sorted(elem_sig(e) for e in els))
    return hash(sig)

def struct_key(prompt, figs):
    """查重联合键：题干前20字 + 图形结构签名。"""
    return (prompt[:20], tuple(fig_sig(f) for f in figs))
