#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, re, argparse
from pathlib import Path

TOKENS_TO_TAGS = {
    "whitecoat": "白衣", "labcoat": "白衣", "glasses": "メガネ",
    "suit": "スーツ", "robe": "ローブ", "longhair": "長髪", "shorthair": "短髪",
    "silverhair": "銀髪", "whitehair": "白髪", "blonde": "金髪", "blackhair": "黒髪",
    "formal": "礼装"
}

def guess_slug_from_name(fname: str) -> str:
    base = Path(fname).stem.lower()
    parts = re.split(r"[_\-\.]+", base)
    return parts[0] if parts else base

def tags_from_tokens(fname: str):
    base = Path(fname).stem.lower()
    return sorted({tag for tk, tag in TOKENS_TO_TAGS.items() if tk in base})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default="./images")
    ap.add_argument("--out", default="./image_manifest.json")
    args = ap.parse_args()
    root = Path(args.images)
    if not root.exists():
        print("Images folder not found:", root); return
    manifest = {}
    for p in root.rglob("*"):
        if not p.is_file(): continue
        if p.suffix.lower() not in [".jpg",".jpeg",".png",".webp",".gif"]: continue
        slug = guess_slug_from_name(p.name)
        tags = tags_from_tokens(p.name)
        rel = str(p.as_posix())
        entry = manifest.setdefault(slug, {"images": [], "tags": []})
        entry["images"].append(rel)
        for t in tags:
            if t not in entry["tags"]:
                entry["tags"].append(t)
    Path(args.out).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", args.out, "with", len(manifest), "entries.")

if __name__ == "__main__":
    main()
