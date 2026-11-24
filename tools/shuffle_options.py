#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选项洗牌工具（种子可复现）
==========================
输入题库 JS（window.YC_MORE_QBANKS.push([...]) 格式），按种子打乱每题选项顺序：
  1. options 数组重排；
  2. answer 索引同步更新（始终指向原正确选项的新位置）；
  3. explanation 中的「故选X」引用同步重映射，保证解析仍指向正确选项。
同一种子 + 同一题库文件，结果完全可复现。只动顺序与索引，不生成、不改写任何观点内容。

用法：
  预览（不写文件）：python3 tools/shuffle_options.py --seed 20261125 --files "assets/qk-zhengzhi-*.js" --dry-run
  实际写入：      python3 tools/shuffle_options.py --seed 20261125 --files "assets/qk-zhengzhi-*.js"
  指定单个文件：  --files assets/qk-zhengzhi-02.js

说明：
  - 每题置换由 f"{seed}:{文件名}:{题目id}" 派生，题目顺序变化不影响单题结果。
  - 解析重映射只处理 PATTERNS 中登记的引用样式（当前全库仅「故选X」一种）；
    若解析用文字描述选项（如"选1千米"），本身不受顺序影响，无需处理。
  - 写入前自动备份为 <原文件>.bak-<seed>。
"""
import argparse
import json
import random
import re
import sys
from glob import glob

LETTERS = "ABCDEFGH"
# 解析中「指向正确选项」的引用样式；出现新样式时在此扩展
PATTERNS = [re.compile(r"故选([A-H])")]


def load_js(path):
    """返回 (push前缀, 题目数组, push后剩余文本)，保持原文件结构"""
    s = open(path, encoding="utf-8").read()
    i = s.index("push(") + len("push(")
    prefix = s[:i]
    arr, end = json.JSONDecoder().raw_decode(s[i:].lstrip())
    return prefix, arr, s[i:].lstrip()[end:]


def dump_js(path, prefix, arr, tail):
    body = json.dumps(arr, ensure_ascii=False, separators=(",", ":"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(prefix + body + tail)


def perm_for(seed, fname, qid, n):
    rng = random.Random(f"{seed}:{fname}:{qid}")
    idx = list(range(n))
    rng.shuffle(idx)
    return idx  # perm[新位置] = 旧位置


def remap_explanation(text, perm):
    old2new = {old: new for new, old in enumerate(perm)}

    def sub(m):
        old = LETTERS.index(m.group(1))
        new = old2new.get(old)
        if new is None:
            return m.group(0)
        return m.group(0).replace(m.group(1), LETTERS[new])

    for p in PATTERNS:
        text = p.sub(sub, text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True, type=str, help="随机种子，同种子结果可复现")
    ap.add_argument("--files", required=True, help="题库文件，支持通配符")
    ap.add_argument("--dry-run", action="store_true", help="只统计不写入")
    args = ap.parse_args()

    paths = sorted(glob(args.files))
    if not paths:
        print(f"未匹配到文件: {args.files}")
        sys.exit(1)

    total = shuffled = 0
    for path in paths:
        fname = path.split("/")[-1]
        prefix, arr, tail = load_js(path)
        changed = 0
        for q in arr:
            total += 1
            opts = q.get("options") or []
            ans = q.get("answer")
            if len(opts) < 2 or not isinstance(ans, int) or not (0 <= ans < len(opts)):
                continue
            perm = perm_for(args.seed, fname, q["id"], len(opts))
            new_opts = [opts[i] for i in perm]
            new_ans = perm.index(ans)
            new_exp = remap_explanation(q.get("explanation", ""), perm)
            if new_opts != opts or new_ans != ans or new_exp != q.get("explanation", ""):
                q["options"] = new_opts
                q["answer"] = new_ans
                q["explanation"] = new_exp
                changed += 1
        shuffled += changed
        dist = {}
        for q in arr:
            if isinstance(q.get("answer"), int):
                dist[q["answer"]] = dist.get(q["answer"], 0) + 1
        print(f"{fname}: 共{len(arr)}题，洗牌{changed}题，答案分布={dict(sorted(dist.items()))}")
        if not args.dry_run and changed:
            import shutil
            bak = f"{path}.bak-{args.seed}"
            if not __import__("os").path.exists(bak):
                shutil.copy2(path, bak)
            dump_js(path, prefix, arr, tail)
            print(f"  已写入，备份: {bak}")
    print(f"合计: 扫描{total}题，洗牌{shuffled}题" + ("（dry-run 未写入）" if args.dry_run else ""))


if __name__ == "__main__":
    main()
