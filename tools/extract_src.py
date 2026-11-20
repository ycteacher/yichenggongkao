# -*- coding: utf-8 -*-
"""One-time extractor: pull inline <script>/<style> blocks out of index.html
into readable source files under src/, and write a template with markers.

The build script (build.py) reverses this exactly, so dist/index.html is
byte-for-byte identical to the original index.html.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "index.html")
INLINE_DIR = os.path.join(ROOT, "src", "inline")
TEMPLATE = os.path.join(ROOT, "src", "template.html")

os.makedirs(INLINE_DIR, exist_ok=True)

with open(HTML, encoding="utf-8") as fh:
    source = fh.read()

pat = re.compile(
    r'(<script\b(?![^>]*\bsrc=)[^>]*>.*?</script>|<style\b[^>]*>.*?</style>)',
    re.S | re.I,
)

HINTS = [
    ("cloud sync layer", "cloud-sync"),
    ("share & referral", "referral"),
    ("usage stats beacon v3", "stats-v3"),
    ("usage stats beacon v1", "stats-v1"),
    ("app-manifest", "app-manifest"),
    ("application/json", "app-manifest"),
    ("injectInfo", "inject-info"),
    ("publicPath", "public-path"),
    ("YC_CS_BANK", "bank-init"),
    ("artifactId", "artifact"),
    ("__ycUI2", "main-ui"),
    ("yc-topbar", "ui-polish"),
]

counter = {"script": 0, "style": 0}
manifest = []


def slug_of(raw):
    low = raw.lower()
    for needle, name in HINTS:
        if needle.lower() in low:
            return name
    return "part"


def repl(match):
    raw = match.group(1)
    is_script = raw.lower().lstrip().startswith("<script")
    kind = "script" if is_script else "style"
    idx = counter[kind]
    counter[kind] += 1
    slug = slug_of(raw)
    ext = "jsfrag" if is_script else "cssfrag"
    fname = "%02d-%s.%s" % (idx, slug, ext)
    with open(os.path.join(INLINE_DIR, fname), "w", encoding="utf-8", newline="") as fh:
        fh.write(raw)
    manifest.append({"index": idx, "kind": kind, "file": fname, "bytes": len(raw.encode("utf-8"))})
    marker = "@@YC_%s_%02d@@" % (kind.upper(), idx)
    return marker


template = pat.sub(repl, source)

with open(TEMPLATE, "w", encoding="utf-8", newline="") as fh:
    fh.write(template)

print("extracted blocks:", len(manifest))
for item in manifest:
    print("  %s %-2d %-28s %6d B" % (item["kind"], item["index"], item["file"], item["bytes"]))
print("template ->", TEMPLATE)
