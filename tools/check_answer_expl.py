#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
答案-解析对齐校验工具
======================
扫描题库 JS，找出以下问题的题目并输出 id 清单：
  A. answer 索引越界（不在 0..len(options)-1）
  B. 解析「故选X」与 answer 指向的选项字母不一致（核心对齐检查）
  C. options 数量 != 4（异常结构）
  D. options 内存在重复选项
  E. 同文件内整题重复（prompt+options 完全相同）

用法：
  python3 tools/check_answer_expl.py --files "assets/qk-*.js"
  python3 tools/check_answer_expl.py --files "assets/qk-zhengzhi-*.js" --json out.json
输出：控制台按文件汇总 + 问题清单；--json 可另存完整结果。
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from glob import glob

LETTERS = "ABCDEFGH"
PAT = re.compile(r"故选([A-H])")


def load_js(path):
    s = open(path, encoding="utf-8").read()
    i = s.index("push(") + len("push(")
    arr, _ = json.JSONDecoder().raw_decode(s[i:].lstrip())
    return arr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", required=True)
    ap.add_argument("--json", dest="json_out", help="结果另存 JSON 文件路径")
    args = ap.parse_args()

    paths = sorted(glob(args.files))
    if not paths:
        print(f"未匹配到文件: {args.files}")
        sys.exit(1)

    problems = defaultdict(list)  # kind -> [{file, id, detail}]
    total = 0
    for path in paths:
        fname = path.split("/")[-1]
        arr = load_js(path)
        seen = {}
        for q in arr:
            total += 1
            qid = q.get("id", "?")
            opts = q.get("options") or []
            ans = q.get("answer")
            exp = q.get("explanation", "") or ""

            if not isinstance(ans, int) or not (0 <= ans < len(opts)):
                problems["A_answer越界"].append({"file": fname, "id": qid, "detail": f"answer={ans}, options数={len(opts)}"})
                continue
            if len(opts) != 4:
                problems["C_选项数异常"].append({"file": fname, "id": qid, "detail": f"options数={len(opts)}"})
            if len(set(opts)) != len(opts):
                dup = [o for o in opts if opts.count(o) > 1][0]
                problems["D_选项重复"].append({"file": fname, "id": qid, "detail": f"重复选项: {dup[:30]}"})

            # B: 解析「故选X」与 answer 对齐（取解析中最后一个引用为准）
            refs = PAT.findall(exp)
            if refs:
                expl_letter = LETTERS.index(refs[-1])
                if expl_letter != ans:
                    problems["B_解析与答案不符"].append({
                        "file": fname, "id": qid,
                        "detail": f"解析故选{refs[-1]}(idx={expl_letter}) vs answer idx={ans}({LETTERS[ans]})",
                    })
            # E: 整题重复
            key = (q.get("prompt", ""), tuple(opts))
            if key in seen:
                problems["E_整题重复"].append({"file": fname, "id": qid, "detail": f"与 {seen[key]} 重复"})
            else:
                seen[key] = qid

    print(f"扫描 {len(paths)} 个文件，共 {total} 题\n")
    kinds = sorted(problems.keys())
    if not kinds:
        print("✅ 未发现答案-解析不对齐或其他结构问题")
    for k in kinds:
        items = problems[k]
        print(f"【{k}】{len(items)} 条")
        for it in items[:50]:
            print(f"  {it['file']}  {it['id']}  {it['detail']}")
        if len(items) > 50:
            print(f"  ...（其余 {len(items) - 50} 条见 JSON 输出）")
        print()

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in problems.items()}, f, ensure_ascii=False, indent=2)
        print(f"完整清单已写入 {args.json_out}")


if __name__ == "__main__":
    main()
