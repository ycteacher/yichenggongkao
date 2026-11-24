# -*- coding: utf-8 -*-
"""只重建 qbank-index.json / qbank-idmap.json（不动 index.html）。
从 tools/build.py 提取的 build_bank_index 逻辑，BANK_VER 手工指定。"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
INDEX_OUT = os.path.join(ASSETS, "qbank-index.json")
IDMAP_OUT = os.path.join(ASSETS, "qbank-idmap.json")
BANK_VER = sys.argv[1] if len(sys.argv) > 1 else "tt81"


def _extract_json_arrays(text):
    payloads = []
    dec = json.JSONDecoder()
    for m in re.finditer(r"\.push\(", text):
        i = m.end()
        while i < len(text) and text[i] in " \t\r\n":
            i += 1
        try:
            val, _ = dec.raw_decode(text, i)
        except ValueError:
            continue
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

    for q in cs_items:
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
