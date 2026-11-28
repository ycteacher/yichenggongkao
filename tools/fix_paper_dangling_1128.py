#!/usr/bin/env python3
"""2026-11-28 修复非押题套卷悬空引用：
A) qbank-idmap.json 补录 21 个存在于 qk-yanyu-08.js 但漏登的 yy 题号；
B) index-b34.js 中 185 个真删题号的引用替换为同前缀（同模块）现存题，
   优先用 dedup_map 重定向，其余按模块难度分布随机（固定种子）选取，
   避开去重拟删名单与全部卷面已用题号。
"""
import json, re, random, glob, os, collections

random.seed(20261128)

IDMAP_FP = 'assets/qbank-idmap.json'
IDX_FP = 'assets/index-b34.js'

idmap = json.load(open(IDMAP_FP))
dm = json.load(open('tools/dedup_map.json'))

src = open(IDX_FP, encoding='utf-8').read()

# ---- parse papers ----
papers = {}   # pid -> (span_start, span_end, qids)
for m in re.finditer(r'\{"id":"(pp-[A-Za-z0-9_-]+)"[^{}]*?"qids":\[([^\]]*)\]', src):
    papers[m.group(1)] = (m.start(), m.end(), re.findall(r'"([^"]+)"', m.group(2)))
print('papers:', len(papers))

all_ref_ids = set()
for _,_,qids in papers.values(): all_ref_ids.update(qids)

missing = collections.defaultdict(list)  # id -> [(pid, pos)]
for pid,(_,_,qids) in papers.items():
    for pos,q in enumerate(qids):
        if q not in idmap: missing[q].append((pid,pos))
distinct_missing = sorted(missing)
print('distinct missing:', len(distinct_missing), 'refs:', sum(len(v) for v in missing.values()))

# ---- A) idmap backfill ----
BACKFILL = {'qk-yanyu-08': ['yy-102','yy-110','yy-111','yy-113','yy-114','yy-115','yy-116','yy-117','yy-118','yy-119','yy-120','yy-121','yy-122','yy-123','yy-124','yy-125','yy-126','yy-127','yy-128','yy-129','yy-130']}
added = 0
for f, ids in BACKFILL.items():
    for q in ids:
        assert q not in idmap, q
        idmap[q] = f
        added += 1
        if q in missing: del missing[q]
print('idmap backfilled:', added, 'idmap size ->', len(idmap))

# ---- candidate pools with diff ----
need_prefixes = collections.Counter(q.split('-')[0] for q in missing)
print('remaining missing prefixes:', dict(need_prefixes))

files_needed = set()
for k,v in idmap.items():
    if k.split('-')[0] in need_prefixes: files_needed.add(v)
print('shard files to load:', len(files_needed))

diff_by_id = {}
for f in sorted(files_needed):
    fp = 'assets/%s.js' % f
    if not os.path.exists(fp): continue
    s = open(fp, encoding='utf-8').read()
    for m in re.finditer(r'\{"id":"([A-Za-z]{1,4}-[0-9A-Za-z_-]{1,12})","module":"[^"]*"(?:(?!\{"id":").)*?"diff":(\d+)', s):
        diff_by_id[m.group(1)] = int(m.group(2))
print('diff known for', len(diff_by_id), 'ids')

pool = collections.defaultdict(lambda: collections.defaultdict(list))  # prefix -> diff -> [ids]
used_in_papers = set(all_ref_ids)
ref_count = collections.Counter()
for _,_,qids in papers.values():
    for q in qids: ref_count[q] += 1
for k, f in idmap.items():
    p = k.split('-')[0]
    if p not in need_prefixes: continue
    if k in dm: continue                    # 去重拟删名单不入选
    d = diff_by_id.get(k)
    if d is None: d = 2                     # 无难度字段的分片按中等档处理
    pool[p][d].append(k)
for p in pool:
    fresh = {d: [c for c in v if c not in used_in_papers] for d,v in pool[p].items()}
    print('pool', p, {d: len(v) for d,v in sorted(pool[p].items())},
          'fresh(unused in any paper):', {d: len(v) for d,v in sorted(fresh.items())})

# per-prefix diff distribution for weighted choice (based on fresh candidates; fall back to all)
dist = {}
for p in pool:
    src_map = {d: v for d,v in ((d, [c for c in pool[p][d] if c not in used_in_papers]) for d in pool[p]) if v}
    if not src_map: src_map = pool[p]
    tot = sum(len(v) for v in src_map.values())
    dist[p] = [(d, len(v)/tot) for d,v in sorted(src_map.items())]

def pick(prefix, taken):
    r = random.random(); acc = 0; chosen_diff = None
    for d,w in dist[prefix]:
        acc += w
        if r <= acc: chosen_diff = d; break
    if chosen_diff is None: chosen_diff = dist[prefix][0][0]
    # 首选：未被任何卷使用的题；不足时回退到卷面占用次数最少的题
    cands = [c for c in pool[prefix][chosen_diff] if c not in used_in_papers and c not in taken]
    if not cands:
        minref = min(ref_count[c] for c in pool[prefix][chosen_diff] if c not in taken) if any(c not in taken for c in pool[prefix][chosen_diff]) else None
        if minref is not None:
            cands = [c for c in pool[prefix][chosen_diff] if c not in taken and ref_count[c] == minref]
    if not cands:
        for d2 in pool[prefix]:
            cands = [c for c in pool[prefix][d2] if c not in taken]
            if cands: break
    assert cands, 'pool exhausted for ' + prefix
    return random.choice(cands)

# ---- build replacements ----
repl = {}   # (pid,pos) -> new_id
new_id_taken = set()
used_count = collections.Counter()
for q in sorted(missing):
    for pid,pos in missing[q]:
        cur_used = set(papers[pid][2]) | {repl.get((pid,p)) for p in range(len(papers[pid][2]))}
        nid = None
        tgt = dm.get(q)
        if tgt and tgt in idmap and tgt not in cur_used and tgt not in new_id_taken:
            nid = tgt   # dedup 重定向：内容最接近
        if nid is None:
            nid = pick(q.split('-')[0], cur_used | new_id_taken)
        repl[(pid,pos)] = nid
        new_id_taken.add(nid)
        used_count[nid] += 1
print('replacements:', len(repl), 'distinct new ids:', len(new_id_taken))
print('new ids reused across papers:', sum(1 for c in used_count.values() if c>1))

# ---- splice edits (from end to start to keep offsets) ----
edits = collections.defaultdict(dict)  # pid -> {pos: new}
for (pid,pos), nid in repl.items(): edits[pid][pos] = nid

out = src
for pid in sorted(edits, key=lambda p: papers[p][0], reverse=True):
    s0, s1, qids = papers[pid]
    for pos, nid in edits[pid].items(): qids[pos] = nid
    body = ','.join('"%s"' % q for q in qids)
    new_seg = src[s0:s1]
    new_seg = re.sub(r'"qids":\[[^\]]*\]', '"qids":[%s]' % body, new_seg, count=1)
    out = out[:s0] + new_seg + out[s1:]
open(IDX_FP, 'w', encoding='utf-8').write(out)
json.dump(idmap, open(IDMAP_FP,'w'), ensure_ascii=False, separators=(',',':'))
print('written. index size:', len(out), 'idmap size:', len(idmap))
