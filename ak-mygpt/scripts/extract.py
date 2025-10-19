#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
ローカル（同リポ内）の gamedata/excel と gamedata/story を唯一のソースとして、
GitHub Pages で配信する静的成果物 docs/ を生成します。

- Excel系: そのままコピー（差分不要なら丸ごと）。併せて index.json を作成
- Story系: .txt をそのままコピーし、一覧用の story/index.json を作成
           環境変数 STORY_JSON_WRAPPER=true のとき、各 .txt の JSON ラッパーも生成
- リリーススナップショット: docs/release/YYYY-MM-DD/ にも同内容を出力
- ルートの docs/latest/index.json に全体メタ情報を出力
"""

import os, json, shutil, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_EXCEL = ROOT / "gamedata" / "excel"
SRC_STORY = ROOT / "gamedata" / "story"
DOCS = ROOT / "docs"
LATEST = DOCS / "latest"
RELEASE_ROOT = DOCS / "release" / datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")

def _copy_tree(src: Path, dst: Path, patterns: tuple[str, ...] = ("*",)):
    if not src.exists():
        return []
    copied = []
    for pat in patterns:
        for p in src.rglob(pat):
            if p.is_dir():
                continue
            rel = p.relative_to(src)
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            try:
                import shutil as _sh
                _sh.copy2(p, out)
            except Exception:
                continue
            st = out.stat()
            copied.append((rel.as_posix(), st.st_size, int(st.st_mtime)))
    return copied

def _write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def build_excel():
    latest_excel = LATEST / "excel"
    release_excel = RELEASE_ROOT / "excel"
    copied = _copy_tree(SRC_EXCEL, latest_excel, patterns=("*.json",))
    _copy_tree(SRC_EXCEL, release_excel, patterns=("*.json",))

    index = {"generated": int(time.time()),
             "files": [{"path": p, "bytes": b, "mtime": m} for p, b, m in sorted(copied)]}
    _write_json(latest_excel / "index.json", index)
    _write_json(release_excel / "index.json", index)
    return {"excel_files": len(copied)}

def build_story():
    latest_story = LATEST / "story"
    release_story = RELEASE_ROOT / "story"
    copied = _copy_tree(SRC_STORY, latest_story, patterns=("*.txt",))
    _copy_tree(SRC_STORY, release_story, patterns=("*.txt",))

    sindex = {"generated": int(time.time()),
              "files": [{"path": p, "bytes": b, "mtime": m} for p, b, m in sorted(copied)]}
    _write_json(latest_story / "index.json", sindex)
    _write_json(release_story / "index.json", sindex)

    # Optional: also create wrapped JSON for .txt
    if os.getenv("STORY_JSON_WRAPPER", "false").lower() in ("1", "true", "yes"):
        latest_wrap = LATEST / "story_json"
        release_wrap = RELEASE_ROOT / "story_json"
        count = 0
        for (rel, _, _m) in copied:
            src_txt = latest_story / rel
            text = src_txt.read_text(encoding="utf-8", errors="ignore")
            payload = {"path": rel, "lang": "ja", "text": text}
            for base in (latest_wrap, release_wrap):
                out = base / Path(rel).with_suffix(".json")
                _write_json(out, payload)
            count += 1
    else:
        count = 0
    return {"story_txt_files": len(copied), "story_json_wrapped": count}

def write_root_index(stats_excel, stats_story):
    meta = {"generated": int(time.time()),
            "release": RELEASE_ROOT.name,
            "sources": {"excel_dir": str(SRC_EXCEL), "story_dir": str(SRC_STORY)},
            "stats": {**stats_excel, **stats_story}}
    _write_json(LATEST / "index.json", meta)
    _write_json(RELEASE_ROOT / "index.json", meta)

def main():
    # reset output dirs
    if LATEST.exists():
        import shutil; shutil.rmtree(LATEST)
    if RELEASE_ROOT.exists():
        import shutil; shutil.rmtree(RELEASE_ROOT)
    LATEST.mkdir(parents=True, exist_ok=True)
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)

    stats_excel = build_excel()
    stats_story = build_story()
    write_root_index(stats_excel, stats_story)
    (DOCS / "README.txt").write_text("Generated static files. See ./latest/ and ./release/\\n", encoding="utf-8")
    print("DONE")

if __name__ == "__main__":
    main()
