# -*- coding: utf-8 -*-
"""按模块物理重组题库分片（一次性脚本，配合 build.py 使用）。

背景：旧分片（qbank-*.js / tuitui-*.js）模块混排，无法做到"进模块只加载该模块分片"。
本脚本把所有 YC_MORE_QBANKS 格式分片按 module 字段重组为 qk-<module>-NN.js 小分片
（单文件 ≤450KB），把 cs-bank-* 重新规范化并按 ≤480KB 切分；申论/综应分片保持不变。

校验：重组前后逐题 id 集合一致（按合并路径分开核对）、总题数一致、
每分片 JSON 可解析、id 无新增丢失。

用法：python3 tools/regroup_banks.py
"""
import json
import os
import re
import subprocess
import sys
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
INDEX_JS = os.path.join(ASSETS, "index-b34.js")
TMP = os.path.join(ROOT, ".tmp_regroup")
MORE_CHUNK = 450_000   # 单分片 JSON 目标上限（字符）
CS_CHUNK = 480_000


def loader_order():
    s = open(INDEX_JS, encoding="utf-8").read()
    m1 = re.search(r"var P1=\[(.*?)\];", s, re.S)
    m2 = re.search(r"var P2=\[(.*?)\];", s, re.S)
    return re.findall(r'"([^"]+)"', m1.group(1)) + re.findall(r'"([^"]+)"', m2.group(1))


def extract(order):
    os.makedirs(TMP, exist_ok=True)
    out = os.path.join(TMP, "banks_extract.json")
    script = (
        "const fs=require('fs');const files=%s;const out={};"
        "for(const f of files){const wnd={YC_MORE_QBANKS:[],YC_CS_BANK:[],YC_ESSAY_BANKS:[]};"
        "const code=fs.readFileSync('assets/'+f+'.js','utf8');"
        "try{new Function('window',code)(wnd);}catch(e){out[f]={error:String(e)};continue;}"
        "out[f]={more:wnd.YC_MORE_QBANKS,cs:wnd.YC_CS_BANK,essay:wnd.YC_ESSAY_BANKS};}"
        "fs.writeFileSync(%s,JSON.stringify(out));console.log('extracted',Object.keys(out).length);"
        % (json.dumps(order), json.dumps(out))
    )
    r = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit(1)
    print(r.stdout.strip())
    return json.load(open(out, encoding="utf-8"))


def main():
    order = loader_order()
    data = extract(order)
    for f, v in data.items():
        if "error" in v:
            print("ERROR extracting", f, v["error"])
            sys.exit(1)

    # ---- 基线：按路径收集原始 items ----
    cs_items, more_items, essay_items = [], [], []
    for f in order:
        cs_items += data[f]["cs"]
        for arr in data[f]["more"]:
            more_items += arr
        for arr in data[f]["essay"]:
            essay_items += arr

    def ids(items):
        return [q["id"] for q in items]

    base = {
        "cs": collections.Counter(ids(cs_items)),
        "more": collections.Counter(ids(more_items)),
        "essay": collections.Counter(ids(essay_items)),
    }

    # ---- 重组 MORE：按模块稳定分组 ----
    by_mod = collections.OrderedDict()
    for q in more_items:
        by_mod.setdefault(q["module"], []).append(q)

    new_files = {}   # name -> full text
    manifest = {}    # name -> {"path":"more"/"cs","module":str,"count":int}
    for mod, items in by_mod.items():
        chunk, chunk_len = [], 0
        seq = 0

        def flush():
            nonlocal chunk, chunk_len, seq
            if not chunk:
                return
            seq += 1
            name = "qk-%s-%02d" % (mod, seq)
            body = json.dumps(chunk, ensure_ascii=False, separators=(",", ":"))
            text = ("window.YC_MORE_QBANKS=window.YC_MORE_QBANKS||[];"
                    "window.YC_MORE_QBANKS.push(%s);" % body)
            new_files[name] = text
            manifest[name] = {"path": "more", "module": mod, "count": len(chunk)}
            chunk, chunk_len = [], 0

        for q in items:
            l = len(json.dumps(q, ensure_ascii=False, separators=(",", ":")))
            if chunk and chunk_len + l > MORE_CHUNK:
                flush()
            chunk.append(q)
            chunk_len += l
        flush()

    # ---- 重组 CS：规范化 + 按大小切分（保持原相对顺序）----
    seq, chunk, chunk_len = 0, [], 0

    def flush_cs():
        nonlocal seq, chunk, chunk_len
        if not chunk:
            return
        seq += 1
        name = "cs-bank-%d" % seq
        parts = []
        for q in chunk:
            parts.append("(window.YC_CS_BANK=window.YC_CS_BANK||[]).push(%s);"
                         % json.dumps(q, ensure_ascii=False, separators=(",", ":")))
        new_files[name] = "".join(parts)
        manifest[name] = {"path": "cs", "module": "changshi", "count": len(chunk)}
        chunk, chunk_len = [], 0

    for q in cs_items:
        l = len(json.dumps(q, ensure_ascii=False, separators=(",", ":")))
        if chunk and chunk_len + l > CS_CHUNK:
            flush_cs()
        chunk.append(q)
        chunk_len += l
    flush_cs()

    # ---- 写入新文件（先清掉将被替换的旧 cs-bank 文件）----
    for f in order:
        if f.startswith("cs-bank-"):
            p = os.path.join(ASSETS, f + ".js")
            if os.path.exists(p):
                os.remove(p)
    for name, text in new_files.items():
        with open(os.path.join(ASSETS, name + ".js"), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)

    # ---- 删除旧 MORE 分片 ----
    removed = []
    for f in order:
        if f in new_files:
            continue
        p = os.path.join(ASSETS, f + ".js")
        if os.path.exists(p) and (f.startswith("qbank-") or f.startswith("tuitui-")):
            os.remove(p)
            removed.append(f)

    # ---- 校验：重新提取全部（新+保留）文件，按路径核对 id 计数 ----
    keep = [f for f in order if f not in new_files and os.path.exists(os.path.join(ASSETS, f + ".js"))]
    verify_order = sorted(new_files.keys()) + keep
    data2 = extract(verify_order)
    cs2, more2, essay2 = [], [], []
    for f in verify_order:
        cs2 += data2[f]["cs"]
        for arr in data2[f]["more"]:
            more2 += arr
        for arr in data2[f]["essay"]:
            essay2 += arr
    ok = True
    for path, items2 in (("cs", cs2), ("more", more2), ("essay", essay2)):
        c2 = collections.Counter(ids(items2))
        if c2 != base[path]:
            ok = False
            diff = (c2 - base[path]) + (base[path] - c2)
            print("MISMATCH in path", path, list(diff.items())[:10])
    if not ok:
        print("VERIFY FAILED")
        sys.exit(1)

    print("OK: %d new shard files, %d old files removed" % (len(new_files), len(removed)))
    print("raw totals: more=%d cs=%d essay=%d" % (len(more2), len(cs2), len(essay2)))
    for mod, items in by_mod.items():
        n = sum(1 for q in items)
        shards = [k for k, v in manifest.items() if v["module"] == mod]
        print("  %-9s %5d questions -> %d shards" % (mod, n, len(shards)))


if __name__ == "__main__":
    main()
