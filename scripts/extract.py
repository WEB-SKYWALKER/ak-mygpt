#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract script (local-only source)
- Mirrors gamedata/excel -> docs/latest/excel
- Mirrors gamedata/story -> docs/latest/stories (keeping subdirs)
- Builds docs/latest/index.json
- Copies latest -> docs/release/YYYY-MM-DD snapshot

You can extend "generate_characters()" if you want docs/latest/characters support.
"""
import argparse, json, os, shutil
from pathlib import Path
from datetime import datetime, date

def copy_tree(src: Path, dst: Path):
    if not src.exists():
        return 0
    count = 0
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        outp = dst / rel
        if p.is_dir():
            outp.mkdir(parents=True, exist_ok=True)
            continue
        outp.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, outp)
        count += 1
    return count

def generate_characters(source_excel: Path, out_latest: Path):
    """
    TODO: Implement character splitting here if needed.
    For now, this is a no-op scaffold that creates the folder.
    """
    characters_out = out_latest / "characters"
    characters_out.mkdir(parents=True, exist_ok=True)
    # Example: if you already have per-character jsons somewhere, you could copy them here.

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="Path to ./gamedata")
    ap.add_argument("--out", required=True, help="Path to ./docs")
    args = ap.parse_args()

    src = Path(args.source)
    out = Path(args.out)
    out_latest = out / "latest"
    out_latest.mkdir(parents=True, exist_ok=True)

    excel_src = src / "excel"
    stories_src = src / "story"

    excel_out = out_latest / "excel"
    stories_out = out_latest / "stories"

    # 1) mirror excel & story
    excel_out.mkdir(parents=True, exist_ok=True)
    stories_out.mkdir(parents=True, exist_ok=True)

    excel_count = copy_tree(excel_src, excel_out)
    story_count = copy_tree(stories_src, stories_out)

    # 2) (optional) generate characters
    generate_characters(excel_src, out_latest)

    # 3) build index.json
    def list_files(root: Path):
        files = []
        if not root.exists():
            return files
        for p in root.rglob("*.json"):
            files.append(str(p.relative_to(out_latest).as_posix()))
        files.sort()
        return files

    index = {
        "generatedAt": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "excel": list_files(excel_out),
        "stories": list_files(stories_out),
        "notes": {
            "excel_count": excel_count,
            "story_count": story_count
        }
    }
    (out_latest / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4) release snapshot
    release_dir = out / "release" / date.today().isoformat()
    release_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(out_latest, release_dir, dirs_exist_ok=True)

    print(f"Done. excel files: {excel_count}, story files: {story_count}")
    print(f"Wrote: {out_latest/'index.json'}")
    print(f"Release snapshot: {release_dir}")

if __name__ == "__main__":
    main()
