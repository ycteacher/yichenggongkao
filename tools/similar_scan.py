#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""高相似题候选扫描：题干相似>0.85 或 选项重合>0.8，输出候选清单供人工抽样。"""
import json, re, glob, hashlib, sys
from collections import defaultdict

def norm(s):
    return re.sub(r"[\s\u3000，。、；：？！“”‘’\"\'()（）]", "", s) if isinstance(s, str) else ""

def load(path):
    txt = open(path, encoding="utf-8").read()
    p = txt.rindex("push(") + 5
    return json.JSONDecoder().raw_decode(txt[p:])[0]

def grams(s, n=6):
    return set(s[i:i+n] for i in range(0, max(0, len(s)-n+1))) if len(s) >= n else {s}

def sim(a, b):
    # 快速长度差预筛后用公共6-gram比例近似
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    inter = len(ga & gb)
    return inter / min(len(ga), len(gb))

def opt_jaccard(a, b):
    sa = set(norm(o) for o in a)
    sb = set(norm(o) for o in b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

by_mod = defaultdict(list)
for path in sorted(glob.glob("assets/qk-*.js")):
    for q in load(path):
        by_mod[q.get("module", "?")].append(q)

candidates = []
for mod, qs in by_mod.items():
    # 倒排索引：6-gram -> 题目下标；仅索引长度>=12的题干
    inv = defaultdict(list)
    for i, q in enumerate(qs):
        for g in grams(norm(q.get("prompt", ""))):
            inv[g].append(i)
    seen = set()
    for g, idxs in inv.items():
        if len(idxs) > 200:  # 高频词 gram 跳过，防爆炸
            continue
        for x in range(len(idxs)):
            for y in range(x+1, len(idxs)):
                pair = (min(idxs[x], idxs[y]), max(idxs[x], idxs[y]))
                if pair in seen:
                    continue
                seen.add(pair)
    for (i, j) in seen:
        a, b = qs[i], qs[j]
        pa, pb = norm(a.get("prompt", "")), norm(b.get("prompt", ""))
        if abs(len(pa) - len(pb)) > max(len(pa), len(pb)) * 0.3:
            continue
        s = sim(pa, pb)
        oj = opt_jaccard(a.get("options") or [], b.get("options") or [])
        if s > 0.85 or oj > 0.8:
            candidates.append({
                "module": mod, "psim": round(s, 3), "optj": round(oj, 3),
                "a": {"id": a["id"], "prompt": a.get("prompt", "")[:60]},
                "b": {"id": b["id"], "prompt": b.get("prompt", "")[:60]},
            })

# 去重（同对可能被多 gram 触发）
uniq = {}
for c in candidates:
    key = (c["module"], c["a"]["id"], c["b"]["id"])
    if key not in uniq or c["psim"] > uniq[key]["psim"]:
        uniq[key] = c
out = sorted(uniq.values(), key=lambda c: -max(c["psim"], c["optj"]))
with open("tools/similar_candidates.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"CANDIDATES={len(out)}")
from collections import Counter
print(dict(Counter(c["module"] for c in out)))
for c in out[:15]:
    print(f"[{c['module']}] psim={c['psim']} optj={c['optj']}  {c['a']['id']} vs {c['b']['id']}  {c['a']['prompt'][:36]}")
