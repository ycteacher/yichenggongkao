# -*- coding: utf-8 -*-
"""Build index.html from src/template.html + src/inline/* fragments.

Usage:  python tools/build.py
Output: index.html (at repo root)

Writes only if the result differs, and prints a short diff summary.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "src", "template.html")
INLINE_DIR = os.path.join(ROOT, "src", "inline")
OUT = os.path.join(ROOT, "index.html")

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
