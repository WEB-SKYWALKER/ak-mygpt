#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract Arknights JP (YoStar) JSONs into lightweight snapshots for a roleplay GPT.

Reads (YoStar JP):
- gamedata/excel/: character_table.json, handbook_info_table.json, charword_table.json, (optional) story_review_*.json
- gamedata/story/: story text JSONs (multiple schemas across files)

Outputs under --out (default: ./docs):
- latest/index.json and release/YYYY-MM-DD/index.json
- characters/<slug>.json   (profile + voiceLines + storyQuotes)
- stories/<sid>.json       (title/chapters/scenes/speeches)
"""

import argparse, os, json, datetime, re, shutil, sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# ---------- utils ----------

def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s)
    return s

def read_json(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dir(p: Path):
    os.makedirs(p, exist_ok=True)

def try_excel_dir(src_root: Path):
    for d in [src_root / "gamedata" / "excel", src_root / "dyn" / "gamedata" / "excel"]:
        if d.exists():
            return d
    return None

def try_story_dirs(src_root: Path) -> List[Path]:
    dirs = []
    for d in [src_root / "gamedata" / "story", src_root / "dyn" / "gamedata" / "story"]:
        if d.exists():
            dirs.append(d)
    return dirs

# ---------- characters ----------

def extract_characters(src_root: Path, out_root: Path) -> Tuple[Dict[str,str], List[str]]:
    excel_dir = try_excel_dir(src_root)
    if not excel_dir:
        print("ERROR: excel dir not found", file=sys.stderr)
        return {}, ["excel dir not found"]

    tables = {}
    missing = []
    for name in ["character_table.json","handbook_info_table.json","charword_table.json"]:
        p = excel_dir / name
        if p.exists():
            tables[name] = read_json(p)
        else:
            missing.append(name)

    char_table = tables.get("character_table.json", {})
    handbook = tables.get("handbook_info_table.json", {})
    charword = tables.get("charword_table.json", {})

    if isinstance(handbook, dict) and "handbookDict" in handbook:
        hb = handbook["handbookDict"]
    else:
        hb = handbook if isinstance(handbook, dict) else {}

    characters_map = {}

    for char_id, ch in char_table.items():
        name = (ch.get("name") or "").strip()
        if not name:
            continue
        slug = slugify(name)

        # handbook（プロフィール）
        hb_entry = None
        if isinstance(hb, dict):
            hb_entry = hb.get(char_id) or hb.get(name)

        profile = {}
        if isinstance(hb_entry, dict):
            profile = {
                "appellation": hb_entry.get("appellation") or name,
                "biography": hb_entry.get("storyTextAudio") or hb_entry.get("storyText") or {},
                "gender": hb_entry.get("gender"),
                "faction": hb_entry.get("faction"),
                "race": hb_entry.get("race"),
                "place": hb_entry.get("place"),
                "birth": hb_entry.get("birth"),
            }

        # charword（ホーム/基地台詞）
        voiceLines = {}
        if isinstance(charword, dict):
            cw_entry = charword.get(char_id) or charword.get(name)
            if isinstance(cw_entry, dict):
                voiceLines = cw_entry

        out_obj = {
            "id": char_id,
            "name": name,
            "rarity": ch.get("rarity"),
            "profession": ch.get("profession"),
            "subProfessionId": ch.get("subProfessionId"),
            "profile": profile,
            "voiceLines": voiceLines,
            "speechStyle": {},
            "storyQuotes": []
        }
        ensure_dir(out_root / "characters")
        with open(out_root / "characters" / f"{slug}.json", "w", encoding="utf-8") as f:
            json.dump(out_obj, f, ensure_ascii=False, indent=2)
        characters_map[slug] = f"characters/{slug}.json"

    return characters_map, missing

# ---------- stories (robust parser for multiple schemas) ----------

def _yield_speeches_from(obj: Any):
    """
    Try to pull speeches as dicts: {"speaker": str, "text": str}
    Handles a few known/observed shapes:
      - {"speeches":[{"speaker":...,"text":...}]}
      - {"content":[{"speaker":...,"content":...}]}
      - {"dialogue":[{"actor":...,"text":...}]}
      - {"story":[{"talk":[{"char":...,"text":...}], ...}]}
      - arbitrary nested lists under keys: scenes, sections, parts, talks, lines, nodes
    """
    if isinstance(obj, dict):
        # direct patterns
        if "speeches" in obj and isinstance(obj["speeches"], list):
            for sp in obj["speeches"]:
                if isinstance(sp, dict):
                    speaker = sp.get("speaker") or sp.get("actor") or sp.get("name")
                    text    = sp.get("text")    or sp.get("content") or sp.get("line")
                    if speaker and text:
                        yield {"speaker": speaker, "text": text}
        if "content" in obj and isinstance(obj["content"], list):
            for sp in obj["content"]:
                if isinstance(sp, dict):
                    speaker = sp.get("speaker") or sp.get("actor") or sp.get("name")
                    text    = sp.get("text")    or sp.get("content") or sp.get("line")
                    if speaker and text:
                        yield {"speaker": speaker, "text": text}
        if "dialogue" in obj and isinstance(obj["dialogue"], list):
            for sp in obj["dialogue"]:
                if isinstance(sp, dict):
                    speaker = sp.get("speaker") or sp.get("actor") or sp.get("name") or sp.get("char")
                    text    = sp.get("text")    or sp.get("content") or sp.get("line")
                    if speaker and text:
                        yield {"speaker": speaker, "text": text}
        if "talk" in obj and isinstance(obj["talk"], list):
            for sp in obj["talk"]:
                if isinstance(sp, dict):
                    speaker = sp.get("char") or sp.get("speaker") or sp.get("actor") or sp.get("name")
                    text    = sp.get("text") or sp.get("content") or sp.get("line")
                    if speaker and text:
                        yield {"speaker": speaker, "text": text}

        # recurse into likely containers
        for k in ["story","stories","chapters","chapter","scenes","sections","parts","nodes","lines"]:
            v = obj.get(k)
            if isinstance(v, list):
                for it in v:
                    yield from _yield_speeches_from(it)
            elif isinstance(v, dict):
                yield from _yield_speeches_from(v)

    elif isinstance(obj, list):
        for it in obj:
            yield from _yield_speeches_from(it)

def parse_story_dir(story_root: Path, out_root: Path, index_hint: Dict[str,str], max_speeches_per_story=4000):
    """
    Walk every *.json under story_root and try to build stories/<sid>.json.
    sid is derived from filename (without extension).
    """
    ensure_dir(out_root / "stories")
    stories_map = dict(index_hint)  # start with index from excel if any
    total_files = 0
    built_files = 0
    for p in sorted(story_root.rglob("*.json")):
        total_files += 1
        sid = p.stem.lower()  # filename as id (e.g., 'act42side_1')
        try:
            data = read_json(p)
        except Exception:
            continue

        # title best-effort: try common fields; fallback to filename
        title = None
        for key in ["name","title","storyName","chapterName","episodeName"]:
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                title = val.strip(); break
        if not title:
            title = sid

        # pull speeches
        speeches = []
        for sp in _yield_speeches_from(data):
            speaker = str(sp.get("speaker") or "").strip()
            text    = str(sp.get("text") or "").strip()
            if not speaker or not text:
                continue
            speeches.append({"speaker": speaker, "text": text})
            if len(speeches) >= max_speeches_per_story:
                break

        # shape into 1 chapter / 1 scene (flat)
        out_obj = {
            "id": sid,
            "title": title,
            "chapters": [{
                "id": f"{sid}-ch1",
                "title": title,
                "scenes": [{
                    "id": f"{sid}-sc1",
                    "title": title,
                    "speeches": speeches
                }]
            }],
            "charactersInvolved": [],  # optional: could be inferred later
            "note": "Auto-parsed from gamedata/story (flat)."
        }

        with open(out_root / "stories" / f"{sid}.json", "w", encoding="utf-8") as f:
            json.dump(out_obj, f, ensure_ascii=False, indent=2)
        stories_map[sid] = f"stories/{sid}.json"
        built_files += 1

    print(f"[stories] scanned={total_files} built={built_files} from {story_root}")
    return stories_map

# ---------- excel stories index (optional) ----------

def extract_stories_index(src_root: Path, out_root: Path):
    excel_dir = try_excel_dir(src_root)
    if not excel_dir:
        return {}, ["excel dir not found"]

    candidates = ["story_review_table.json","story_review_meta_table.json","storyinfo.json"]
    found = None
    for c in candidates:
        p = excel_dir / c
        if p.exists():
            found = p; break

    stories_map = {}
    warnings = []

    if not found:
        warnings.append("story index not found")
        return stories_map, warnings

    try:
        data = read_json(found)
        if isinstance(data, dict) and "infos" in data and isinstance(data["infos"], dict):
            for sid, meta in data["infos"].items():
                title = meta.get("name") or meta.get("title") or sid
                sid_slug = str(sid).lower()
                stories_map[sid_slug] = f"stories/{sid_slug}.json"
        elif isinstance(data, dict) and "entry" in data and isinstance(data["entry"], list):
            for e in data["entry"]:
                sid = str(e.get("id") or e.get("key") or e.get("code") or "").lower()
                if not sid: continue
                title = e.get("name") or e.get("title") or sid
                stories_map[sid] = f"stories/{sid}.json"
        else:
            warnings.append(f"Unrecognized story index structure in {found.name}")
    except Exception as e:
        warnings.append(f"Failed to parse story index: {e}")

    # create minimal placeholder files so links resolve (optional)
    ensure_dir(out_root / "stories")
    for sid in stories_map.keys():
        fp = out_root / "stories" / f"{sid}.json"
        if not fp.exists():
            with open(fp, "w", encoding="utf-8") as f:
                json.dump({
                    "id": sid, "title": sid,
                    "chapters": [], "charactersInvolved": [],
                    "note": "Placeholder from story index; will be overwritten if text is found."
                }, f, ensure_ascii=False, indent=2)

    return stories_map, warnings

# ---------- collect short quotes to characters ----------

def collect_story_quotes(out_root: Path, characters_map: Dict[str,str], max_per_char: int = 300):
    stories_dir = out_root / "stories"
    if not stories_dir.exists():
        return 0

    # character files
    char_file = {slug: out_root / path for slug, path in characters_map.items()}

    def normalize_name(n: str) -> str:
        n = (n or "").strip()
        n = re.sub(r"[［\[\(（].*?[］\)\]]", "", n)
        return n

    collected = {slug: [] for slug in characters_map.keys()}

    for p in stories_dir.glob("*.json"):
        try:
            data = read_json(p)
        except Exception:
            continue
        for ch in data.get("chapters", []):
            for sc in ch.get("scenes", []):
                for sp in sc.get("speeches", []):
                    speaker = normalize_name(sp.get("speaker", ""))
                    text = (sp.get("text") or "").strip()
                    if not speaker or not text:
                        continue
                    sslug = slugify(speaker)
                    if sslug in collected and len(text) <= 120:
                        if len(collected[sslug]) < max_per_char:
                            collected[sslug].append(text)

    touched = 0
    for sslug, quotes in collected.items():
        if not quotes:
            continue
        fp = char_file.get(sslug)
        if not fp or not fp.exists():
            continue
        try:
            obj = read_json(fp)
            obj["storyQuotes"] = (obj.get("storyQuotes") or []) + quotes
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            touched += 1
        except Exception:
            pass

    return touched

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="./tmp_repo/ja_JP", help="Path to ja_JP root")
    ap.add_argument("--out", default="./docs", help="Output dir (writes latest/ and release/DATE/)")
    args = ap.parse_args()

    src_root = Path(args.source)
    out_base = Path(args.out)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    release_dir = out_base / "release" / today
    latest_dir  = out_base / "latest"
    ensure_dir(release_dir); ensure_dir(latest_dir)

    # characters
    characters_map, missing_tables = extract_characters(src_root, release_dir)

    # story index (optional) + story text (preferred)
    stories_map, story_warn = extract_stories_index(src_root, release_dir)
    for story_dir in try_story_dirs(src_root):
        stories_map = parse_story_dir(story_dir, release_dir, stories_map)

    # collect short quotes for each character
    touched = collect_story_quotes(release_dir, characters_map, max_per_char=300)

    # write index
    index_obj = {
        "version": "ak-v4",
        "generatedAt": datetime.datetime.now().astimezone().isoformat(),
        "characters": characters_map,
        "stories": stories_map,
        "notes": {
            "missingTables": missing_tables,
            "storyWarnings": story_warn,
            "storyQuotesAttached": touched
        }
    }
    for target in [release_dir, latest_dir]:
        with open(target / "index.json", "w", encoding="utf-8") as f:
            json.dump(index_obj, f, ensure_ascii=False, indent=2)
    # copy subdirs to /latest
    for sub in ["characters", "stories"]:
        src = release_dir / sub
        if src.exists():
            dst = latest_dir / sub
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    print("DONE.")
    print("Outputs:")
    print(" -", release_dir)
    print(" -", latest_dir)

if __name__ == "__main__":
    main()
