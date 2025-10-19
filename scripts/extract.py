#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Arknights Data Site — extractor
- 入力:
    EXCEL_SRC: gamedata/excel         … *.json 群（階層保持）
    STORY_SRC: gamedata/story         … *.txt  群（階層保持）
    OUT_DIR  : docs                   … 生成先（docs/）
    STORY_JSON_WRAPPER: "true"/"false"
        true の場合、.txt を JSON でも複製して配信

- 出力構成:
  docs/
    ├─ latest/
    │   ├─ index.json
    │   ├─ excel/        (EXCEL_SRC のコピー)
    │   ├─ story/        (STORY_SRC の .txt コピー)
    │   └─ story_json/   (任意) .txt を {"path","name","text"} で JSON 変換
    └─ release/YYYY-MM-DD/  ← latest のスナップショット
"""

from __future__ import annotations
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

# ===== 設定（環境変数） =====
EXCEL_DIR = Path(os.environ.get("EXCEL_SRC", "gamedata/excel"))
STORY_DIR = Path(os.environ.get("STORY_SRC", "gamedata/story"))
OUT_DIR   = Path(os.environ.get("OUT_DIR", "docs"))
WRAP_TXT  = os.environ.get("STORY_JSON_WRAPPER", "false").lower() == "true"

LATEST_DIR  = OUT_DIR / "latest"
RELEASE_DIR = OUT_DIR / "release" / datetime.utcnow().strftime("%Y-%m-%d")


def _clean_dir(p: Path):
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


def _copy_tree(src: Path, dst: Path, patterns: tuple[str, ...]):
    """
    src 以下のファイルのうち patterns にマッチするものだけを
    ディレクトリ階層を保ったまま dst にコピー
    """
    count = 0
    if not src.exists():
        return 0

    for path in src.rglob("*"):
        if path.is_file() and any(path.name.endswith(ext) for ext in patterns):
            rel = path.relative_to(src)
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, out)
            count += 1
    return count


def _wrap_story_txt_to_json(story_root: Path, json_root: Path):
    """
    story_root 以下の .txt を JSON にして json_root 以下に保存
    JSON 形式: {"path": "<相対パス>", "name": "<ファイル名>", "text": "<内容>"}
    """
    n = 0
    for txt in story_root.rglob("*.txt"):
        rel = txt.relative_to(story_root)
        out = (json_root / rel).with_suffix(".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        text = txt.read_text(encoding="utf-8", errors="replace")
        payload = {
            "path": str(rel).replace("\\", "/"),
            "name": txt.stem,
            "text": text
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        n += 1
    return n


def _build_index(latest_dir: Path, excel_root: Path, story_root: Path, wrapped: bool):
    index = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "excel_count": 0,
        "story_txt_count": 0,
        "story_json_count": 0,
        "paths": {
            "excel": "excel/",
            "story": "story/",
            "story_json": "story_json/" if wrapped else None
        },
        "lists": {
            "excel": [],
            "story": [],
            "story_json": []
        }
    }

    # excel
    for f in excel_root.rglob("*.json"):
        index["lists"]["excel"].append(str(f.relative_to(excel_root)).replace("\\", "/"))
    index["excel_count"] = len(index["lists"]["excel"])

    # story txt
    for f in story_root.rglob("*.txt"):
        index["lists"]["story"].append(str(f.relative_to(story_root)).replace("\\", "/"))
    index["story_txt_count"] = len(index["lists"]["story"])

    # story json (optional)
    if wrapped:
        sj = latest_dir / "story_json"
        for f in sj.rglob("*.json"):
            index["lists"]["story_json"].append(str(f.relative_to(sj)).replace("\\", "/"))
        index["story_json_count"] = len(index["lists"]["story_json"])

    (latest_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main():
    print("== Build start ==")
    print(f"EXCEL_SRC={EXCEL_DIR}")
    print(f"STORY_SRC={STORY_DIR}")
    print(f"OUT_DIR={OUT_DIR}")
    print(f"STORY_JSON_WRAPPER={WRAP_TXT}")

    # latest を作り直し
    _clean_dir(LATEST_DIR)

    # 1) excel json をコピー
    excel_out = LATEST_DIR / "excel"
    excel_out.mkdir(parents=True, exist_ok=True)
    excel_cnt = _copy_tree(EXCEL_DIR, excel_out, patterns=(".json",))
    print(f"Copied excel json: {excel_cnt}")

    # 2) story txt をコピー
    story_out = LATEST_DIR / "story"
    story_out.mkdir(parents=True, exist_ok=True)
    story_cnt = _copy_tree(STORY_DIR, story_out, patterns=(".txt",))
    print(f"Copied story txt: {story_cnt}")

    # 3) (任意) txt → json 変換
    story_json_cnt = 0
    if WRAP_TXT:
        story_json_out = LATEST_DIR / "story_json"
        story_json_out.mkdir(parents=True, exist_ok=True)
        story_json_cnt = _wrap_story_txt_to_json(story_out, story_json_out)
        print(f"Wrapped story txt → json: {story_json_cnt}")

    # 4) index.json
    _build_index(LATEST_DIR, excel_out, story_out, wrapped=WRAP_TXT)
    print("Wrote index.json")

    # 5) release スナップショット
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    shutil.copytree(LATEST_DIR, RELEASE_DIR)
    print(f"Snapshot created: {RELEASE_DIR}")

    print("== Build done ==")


if __name__ == "__main__":
    main()
