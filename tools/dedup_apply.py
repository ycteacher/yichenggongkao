#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B3 删题：从言语分片删除 22 条重复题，重算 bytes，更新 qbank-index.json。"""
import json, collections

DELETE = {
    "qk-yanyu-01": ["yy-167","yy-175","yy-176","yy-178","yy-179","yy-180","yy-181","yy-182","yy-183","yy-184",
                    "yy-185","yy-186","yy-187","yy-188","yy-189","yy-190","yy-191","yy-192","yy-193","yy-194","yy-195"],
    "qk-yanyu-08": ["yy-174"],
}

def load_raw(path):
    txt = open(path, encoding="utf-8").read()
    p = txt.rindex("push(") + len("push(")
    val, end = json.JSONDecoder().raw_decode(txt[p:])
    return txt[:p], val, txt[p+end:]

idx_path = "assets/qbank-index.json"
idx = json.load(open(idx_path, encoding="utf-8"))
total_removed = 0

for shard, ids in DELETE.items():
    path = f"assets/{shard}.js"
    prefix, questions, suffix = load_raw(path)
    before = len(questions)
    questions = [q for q in questions if q["id"] not in set(ids)]
    removed = before - len(questions)
    assert removed == len(ids), f"{shard}: expect {len(ids)} removed, got {removed}"
    total_removed += removed
    body = json.dumps(questions, ensure_ascii=False, separators=(",", ":"))
    open(path, "w", encoding="utf-8").write(prefix + body + suffix)
    nbytes = len(body.encode("utf-8"))
    idx["files"][shard]["count"] = len(questions)
    idx["files"][shard]["bytes"] = nbytes
    print(f"{shard}: {before}->{len(questions)}  bytes={nbytes}")

idx["modules"]["yanyu"]["count"] -= total_removed
# total：索引原值 52038 已按去重后口径记账（实载 52060-22=52038），保持不变
print(f"TOTAL_REMOVED={total_removed}  index.total stays {idx['total']}  yanyu.count={idx['modules']['yanyu']['count']}")
json.dump(idx, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# 校验：重扫全库确认重复清零（言语范围）
import re, glob, hashlib
def norm(s):
    return re.sub(r"[\s\u3000，。、；：？！“”‘’\"\'()（）]", "", s) if isinstance(s, str) else ""
groups = {}
for path in sorted(glob.glob("assets/qk-yanyu-*.js")):
    _, qs, _ = load_raw(path)
    for q in qs:
        key = hashlib.md5((norm(q["prompt"]) + "||" + "||".join(sorted(norm(o) for o in q["options"]))).encode()).hexdigest()
        groups.setdefault(key, []).append(q["id"])
dups = {k: v for k, v in groups.items() if len(v) > 1}
print(f"YANYU_DUP_GROUPS_AFTER={len(dups)}")
