# -*- coding: utf-8 -*-
"""Build index.html from src/template.html + src/inline/* fragments.

Usage:  python tools/build.py
Output: index.html (at repo root), assets/qbank-index.json, assets/qbank-idmap.json

Writes only if the result differs, and prints a short diff summary.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "src", "template.html")
INLINE_DIR = os.path.join(ROOT, "src", "inline")
OUT = os.path.join(ROOT, "index.html")
ASSETS = os.path.join(ROOT, "assets")
INDEX_OUT = os.path.join(ASSETS, "qbank-index.json")
IDMAP_OUT = os.path.join(ASSETS, "qbank-idmap.json")

BANK_VER = "tt56"

with open(TEMPLATE, encoding="utf-8") as fh:
    template = fh.read()

fragments = {}
for name in os.listdir(INLINE_DIR):
    if name.endswith((".jsfrag", ".cssfrag")):
        with open(os.path.join(INLINE_DIR, name), encoding="utf-8") as fh:
            fragments[name] = fh.read()

marker_pat = re.compile(r"@@YC_(SCRIPT|STYLE)_(\d\d)@@")
missing = []


EXT = {"script": ".jsfrag", "style": ".cssfrag"}


def repl(match):
    kind = match.group(1).lower()
    idx = match.group(2)
    ext = EXT[kind]
    cands = [n for n in fragments if n.startswith(idx + "-") and n.endswith(ext)]
    if not cands:
        missing.append(match.group(0))
        return match.group(0)
    return fragments[cands[0]]


result = marker_pat.sub(repl, template)

if missing:
    print("ERROR: missing fragments:", missing)
    sys.exit(1)

old = ""
if os.path.exists(OUT):
    with open(OUT, encoding="utf-8") as fh:
        old = fh.read()

if result == old:
    print("OK: index.html unchanged (in sync with src).")
else:
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(result)
    print("OK: index.html rebuilt from src. %d -> %d chars." % (len(old), len(result)))


# ---------------------------------------------------------------------------
# 题库索引生成：assets/qbank-index.json（轻量，首屏加载）
#               assets/qbank-idmap.json（id -> 分片，错题/收藏/整卷按需加载）
#
# 分片约定（由 tools/regroup_banks.py 生成）：
#   qk-<module>-NN.js   -> window.YC_MORE_QBANKS.push([...])，单模块
#   cs-bank-N.js        -> 逐题 (window.YC_CS_BANK=...).push({...})，常识
#   shenlun-bank-1.js / zongying-bank-1.js -> YC_ESSAY_BANKS.push([...])
# 所有 JSON 载荷均为严格 JSON，可直接解析。
# ---------------------------------------------------------------------------

def _extract_json_arrays(text):
    """从分片文本中取出所有严格 JSON 数组/对象载荷（raw_decode，免括号配对）。"""
    payloads = []
    dec = json.JSONDecoder()
    for m in re.finditer(r"\.push\(", text):
        i = m.end()
        while i < len(text) and text[i] in " \t\r\n":
            i += 1
        try:
            val, _ = dec.raw_decode(text, i)
        except ValueError:
            continue  # 非载荷位置（如字符串中的 .push( 示例代码）
        payloads.append(val)
    return payloads


def _as_items(p):
    if isinstance(p, dict):
        return [p]
    if isinstance(p, list):
        return p
    return []


def build_bank_index():
    shard_names = sorted(
        f[:-3] for f in os.listdir(ASSETS)
        if f.endswith(".js") and (f.startswith("qk-") or f.startswith("cs-bank-")
                                  or f in ("shenlun-bank-1.js", "zongying-bank-1.js"))
    )
    files_meta = {}
    cs_items, more_items, essay_items = [], [], []
    for name in shard_names:
        text = open(os.path.join(ASSETS, name + ".js"), encoding="utf-8").read()
        payloads = _extract_json_arrays(text)
        items = []
        if name.startswith("cs-bank-"):
            for p in payloads:
                items.extend(_as_items(p))
            cs_items.extend(items)
            module = "changshi"
        elif name.startswith("qk-"):
            for p in payloads:
                items.extend(_as_items(p))
            more_items.extend(items)
            module = name.split("-")[1]
        else:
            for p in payloads:
                items.extend(_as_items(p))
            essay_items.extend(items)
            module = "shenlun" if name.startswith("shenlun-") else "zongying"
        files_meta[name] = {"module": module, "count": len(items), "bytes": len(text.encode("utf-8"))}

    # 模拟运行时合并（与 index-b34.js mergeAll 一致），得到各模块合并后题数
    nc, sp = {}, {}
    merged_per_mod = {}

    def add_more(q):
        if q and q.get("id") and q["id"] not in nc:
            dd = q.get("module") in ("yanyu", "panduan") and not q.get("fig") and not q.get("optFig")
            pk = "__id__" + q["id"]
            if dd and q.get("prompt") and len(str(q["prompt"])) >= 8:
                pk = (q.get("module") or "") + "|" + re.sub(r"\s+", "", str(q["prompt"]))[:200]
            if pk in sp:
                return
            sp[pk] = 1
            nc[q["id"]] = q
            merged_per_mod[q["module"]] = merged_per_mod.get(q["module"], 0) + 1

    for q in cs_items:  # cs 路径校验（与 ycMergeCs 一致）
        if (q and q.get("id") and q["id"] not in nc and q.get("prompt")
                and isinstance(q.get("options"), list) and len(q["options"]) == 4
                and isinstance(q.get("answer"), (int, float)) and not isinstance(q.get("answer"), bool)
                and 0 <= q["answer"] <= 3):
            nc[q["id"]] = q
            mk = q.get("module") or "changshi"
            merged_per_mod[mk] = merged_per_mod.get(mk, 0) + 1
    for q in more_items:
        add_more(q)

    modules = {}
    for name, meta in files_meta.items():
        modules.setdefault(meta["module"], {"count": 0, "files": []})
        modules[meta["module"]]["files"].append(name)
    for mod, info in modules.items():
        if mod in ("shenlun", "zongying"):
            info["count"] = files_meta[info["files"][0]]["count"]
        else:
            info["count"] = merged_per_mod.get(mod, 0)

    idmap = {}
    for name in shard_names:
        text = open(os.path.join(ASSETS, name + ".js"), encoding="utf-8").read()
        for p in _extract_json_arrays(text):
            for q in _as_items(p):
                qid = q.get("id") if isinstance(q, dict) else None
                if qid and qid not in idmap:
                    idmap[qid] = name

    index = {
        "v": BANK_VER,
        "total": len(cs_items) + len(more_items) + len(essay_items),
        "mergedTotal": sum(merged_per_mod.values()),
        "modules": modules,
        "files": files_meta,
    }
    with open(INDEX_OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(index, ensure_ascii=False, separators=(",", ":")))
    with open(IDMAP_OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(idmap, ensure_ascii=False, separators=(",", ":")))
    print("OK: qbank-index.json %d bytes (%d shards, mergedTotal=%d), qbank-idmap.json %d bytes"
          % (os.path.getsize(INDEX_OUT), len(shard_names), index["mergedTotal"], os.path.getsize(IDMAP_OUT)))


build_bank_index()
