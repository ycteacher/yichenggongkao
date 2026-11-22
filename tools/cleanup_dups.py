# -*- coding: utf-8 -*-
"""题库清理：删除 23 条题干重复死条目 + 12 条 id 重复次现条目。
只做删除，不改任何保留题内容。先 round-trip 校验再写回。"""
import json, os, re, sys

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
PREFIX = "window.YC_MORE_QBANKS=window.YC_MORE_QBANKS||[];window.YC_MORE_QBANKS.push("
SUFFIX = ");"

def load(name):
    text = open(os.path.join(ASSETS, name + ".js"), encoding="utf-8").read()
    assert text.startswith(PREFIX) and text.endswith(SUFFIX), name + " format mismatch"
    payload = text[len(PREFIX):-len(SUFFIX)]
    items = json.loads(payload)
    # round-trip 校验：重序列化必须与原文字节一致
    rt = PREFIX + json.dumps(items, ensure_ascii=False, separators=(",", ":")) + SUFFIX
    assert rt == text, name + " round-trip mismatch"
    return items

def save(name, items):
    out = PREFIX + json.dumps(items, ensure_ascii=False, separators=(",", ":")) + SUFFIX
    with open(os.path.join(ASSETS, name + ".js"), "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    return len(out.encode("utf-8"))

def pkey(q):
    return (q.get("module") or "") + "|" + re.sub(r"\s+", "", str(q.get("prompt") or ""))[:200]

report = {}

# --- 任务一：题干重复（分片内保留首条） ---
for name, expect in (("qk-yanyu-01", 15), ("qk-panduan-01", 8)):
    items = load(name)
    seen, keep, removed = set(), [], []
    for q in items:
        dd = q.get("module") in ("yanyu", "panduan") and not q.get("fig") and not q.get("optFig")
        if dd and q.get("prompt") and len(str(q["prompt"])) >= 8:
            k = pkey(q)
            if k in seen:
                removed.append(q["id"])
                continue
            seen.add(k)
        keep.append(q)
    assert len(removed) == expect, (name, len(removed), expect)
    save(name, keep)
    report[name] = removed

# --- 任务二：id 重复次现条目（按任务单位置逐一核对后删除） ---
id_dups = {
    "qk-tuitui-36": [("tt-9032", 75)],
    "qk-tuitui-37": [("tt-9176", 52), ("tt-9177", 53), ("tt-9180", 54)],
    "qk-tuitui-38": [("tt-9322", 11), ("tt-9323", 12), ("tt-9325", 13)],
    "qk-tuitui-48": [("tt-9211", 53), ("tt-9284", 54), ("tt-9430", 56), ("tt-9066", 61), ("tt-9212", 63)],
}
for name, pairs in id_dups.items():
    items = load(name)
    drop_idx = set()
    for qid, idx in pairs:
        assert items[idx].get("id") == qid, (name, qid, idx, items[idx].get("id"))
        drop_idx.add(idx)
    keep = [q for i, q in enumerate(items) if i not in drop_idx]
    save(name, keep)
    report[name] = [p[0] for p in pairs]

total_removed = sum(len(v) for v in report.values())
print("REMOVED", total_removed)
for k, v in report.items():
    print(k, len(v), ",".join(v))
