#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全库完全相同题扫描：题干+选项归一化分组，输出重复组清单。"""
import json, re, glob, hashlib, sys

def norm(s):
    if not isinstance(s, str):
        return ""
    return re.sub(r"[\s\u3000，。、；：？！“”‘’\"'`~!@#$%^&*()_+\-=\[\]{}<>?/\\|,.;:?]", "", s)

def load_shard(path):
    txt = open(path, encoding="utf-8").read()
    m = re.search(r"\[.*\]\s*\)?\s*;?\s*$", txt, re.S)
    p = txt.rindex("push(") + len("push(")
    val, _ = json.JSONDecoder().raw_decode(txt[p:])
    return val

groups = {}
for path in sorted(glob.glob("assets/qk-*.js")):
    try:
        qs = load_shard(path)
    except Exception as e:
        print(f"LOAD_FAIL {path}: {e}", file=sys.stderr)
        continue
    for q in qs:
        opts = q.get("options") or []
        key = hashlib.md5((norm(q.get("prompt","")) + "||" + "||".join(sorted(norm(o) for o in opts))).encode("utf-8")).hexdigest()
        groups.setdefault(key, []).append({
            "id": q["id"], "file": path.split("/")[-1],
            "answer": q.get("answer"), "prompt": q.get("prompt","")[:40],
        })

dups = {k: v for k, v in groups.items() if len(v) > 1}
total_dup = sum(len(v) for v in dups.values())
print(f"EXACT_DUP_GROUPS={len(dups)}  ENTRIES={total_dup}")
for k, v in sorted(dups.items(), key=lambda x: -len(x[1])):
    ids = [e["id"] for e in v]
    keep = min(ids, key=lambda x: int(x.split("-")[-1]))
    print(f"GROUP keep={keep} n={len(v)} ids={','.join(ids)} files={','.join(sorted(set(e['file'] for e in v)))}")
    # 答案是否一致（选项集合相同但顺序可能不同，比较归一化正确项文本需回原题，此处仅报答案位置差异提示）
    if len(set(e["answer"] for e in v)) > 1:
        print(f"  ANSWER_POS_DIFFERS: {[ (e['id'], e['answer']) for e in v ]}")

# 输出映射文件供后续嵌入
mapping = {}
for v in dups.values():
    ids = [e["id"] for e in v]
    keep = min(ids, key=lambda x: int(x.split("-")[-1]))
    for i in ids:
        if i != keep:
            mapping[i] = keep
with open("tools/dedup_map.json", "w", encoding="utf-8") as f:
    json.dump(mapping, f, ensure_ascii=False, indent=0, sort_keys=True)
print(f"MAPPING_WRITTEN tools/dedup_map.json old={len(mapping)}")
