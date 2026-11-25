#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图推大分片切分：qk-tuitui-82..91 → ≤1MB 小片（新名 96 起），同步索引与 idmap。
只重排文件边界，不改任何题目内容与 id；旧分片保留在服务器一个版本周期。
带 #h 高亮查找表的分片（84/85/86/90/91），每个新片携带裁剪到本片所用哈希的查找表。
新片不跨旧分片边界，保证 L 表完整覆盖。"""
import json, os, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(REPO, "assets")
OLD = list(range(82, 92))
KEEP = [92, 93, 94, 95]
LIMIT = 1024 * 1024
PREFIX = "window.YC_MORE_QBANKS=window.YC_MORE_QBANKS||[];window.YC_MORE_QBANKS.push("
HASH_RE = re.compile(r"#h([0-9a-f]{10})")

def dump_q(q):
    return json.dumps(q, ensure_ascii=False, separators=(",", ":"))

def parse_shard(raw, name):
    """→ (题目数组, appendix模板或None, L字典或None)"""
    assert raw.startswith(PREFIX), f"{name} 前缀不符"
    body = raw[len(PREFIX):]
    anchor = "]);(function(){var L="
    i = body.find(anchor)
    if i < 0:
        b = body.rstrip()
        assert b.endswith("]);"), f"{name} 尾部异常"
        return json.loads(b[:-2]), None, None
    arr = json.loads(body[:i + 1])
    appendix = body[i + 3:]
    k = appendix.find("var L=") + 6
    L, end = json.JSONDecoder().raw_decode(appendix[k:])
    template = appendix[:k] + "__L__" + appendix[k + end:]
    return arr, template, L

def main():
    # 1. 解析全部旧分片
    shards = []  # [(旧名, [(qid,q,qsz,hashes)], template, L, hash_entry_size)]
    for n in OLD:
        name = f"qk-tuitui-{n}"
        raw = open(os.path.join(A, name + ".js"), encoding="utf-8").read()
        arr, template, L = parse_shard(raw, name)
        items = []
        for q in arr:
            assert q.get("id") and q.get("module") == "tuitui", f"异常题: {q.get('id')}"
            s = dump_q(q)
            hashes = set(HASH_RE.findall(s))
            if template is None:
                assert not hashes, f"{name} 存在无表的 #h 引用"
            items.append((q["id"], q, len(s.encode("utf-8")) + 1, hashes))
        shards.append((name, items, template, L))
    total = sum(len(it) for _, it, _, _ in shards)
    print(f"旧分片 {len(OLD)} 个，共 {total} 题")

    # 2. 逐旧分片独立切分（体积含裁剪后 L 表增量）
    parts = []  # [(ids, qs, template, L)]
    for name, items, template, L in shards:
        hsize = {h: len(json.dumps({h: v}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) - 1
                 for h, v in L.items()} if L else {}
        fixed_app = (len(template.replace("__L__", "")) if template else 0)
        cur, cur_qb, cur_hashes = [], 0, set()
        def flush():
            nonlocal cur, cur_qb, cur_hashes
            if cur:
                parts.append(([i[0] for i in cur], [i[1] for i in cur], template, L))
                cur, cur_qb, cur_hashes = [], 0, set()
        for qid, q, qsz, hashes in items:
            new_hashes = cur_hashes | hashes
            app_sz = (fixed_app + sum(hsize[h] for h in new_hashes)) if template and new_hashes else 0
            est = len(PREFIX) + cur_qb + qsz + 3 + app_sz + 1
            if cur and est > LIMIT:
                flush()
                new_hashes = set(hashes)
                app_sz = (fixed_app + sum(hsize[h] for h in new_hashes)) if template and new_hashes else 0
            cur.append((qid, q, qsz, hashes)); cur_qb += qsz; cur_hashes = new_hashes
        flush()

    # 3. 写新分片
    new_names = []
    start = 96
    for i, (ids, qs, template, L) in enumerate(parts):
        name = f"qk-tuitui-{start + i}"
        body = PREFIX + "[" + ",".join(dump_q(q) for q in qs) + "]);"
        if template:
            used = set()
            for q in qs:
                used |= set(HASH_RE.findall(dump_q(q)))
            pruned = {h: L[h] for h in sorted(used) if h in L}
            missing = used - set(L.keys())
            assert not missing, f"{name} 缺哈希: {missing}"
            if pruned:
                body += template.replace("__L__", json.dumps(pruned, ensure_ascii=False, separators=(",", ":")))
        body += "\n"
        with open(os.path.join(A, name + ".js"), "w", encoding="utf-8") as f:
            f.write(body)
        actual = os.path.getsize(os.path.join(A, name + ".js"))
        assert actual <= LIMIT, f"{name} 超 1MB: {actual}"
        new_names.append(name)
        print(f"  {name}: {len(qs)} 题, {actual} bytes")

    # 4. 更新索引
    ip = os.path.join(A, "qbank-index.json")
    idx = json.load(open(ip, encoding="utf-8"))
    tt = idx["modules"]["tuitui"]
    old_count = tt["count"]
    for n in OLD:
        idx["files"].pop(f"qk-tuitui-{n}", None)
    for i, (ids, qs, _, _) in enumerate(parts):
        name = f"qk-tuitui-{start + i}"
        idx["files"][name] = {"module": "tuitui", "count": len(qs),
                              "bytes": os.path.getsize(os.path.join(A, name + ".js"))}
    tt["files"] = new_names + [f"qk-tuitui-{n}" for n in KEEP]
    assert tt["count"] == old_count == sum(idx["files"][f]["count"] for f in tt["files"]), "count 不一致"
    idx["v"] = "tt85"
    json.dump(idx, open(ip, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"索引更新: v=tt85, tuitui files={len(tt['files'])} 个, count={tt['count']}")

    # 5. 更新 idmap（仅 tuitui 段）
    mp = os.path.join(A, "qbank-idmap.json")
    idmap = json.load(open(mp, encoding="utf-8"))
    changed = 0
    for i, (ids, _, _, _) in enumerate(parts):
        name = f"qk-tuitui-{start + i}"
        for qid in ids:
            assert idmap.get(qid, "").startswith("qk-tuitui-"), f"idmap 缺 {qid}"
            idmap[qid] = name; changed += 1
    json.dump(idmap, open(mp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"idmap 更新: {changed} 条")

    # 6. 终检
    seen = set()
    for _, items, _, _ in shards:
        for qid, _, _, _ in items:
            assert qid not in seen, f"重复 id: {qid}"
            seen.add(qid)
    assert len(seen) == total
    tt_ids = [k for k in idmap if k.startswith("tt-")]
    assert len(tt_ids) == 6262, f"tuitui idmap 总数 {len(tt_ids)}"
    print("终检通过：id 无重复无丢失，总数不变")

if __name__ == "__main__":
    main()
