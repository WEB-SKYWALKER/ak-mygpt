#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, os, json, datetime, re, shutil, sys
from pathlib import Path

def slugify(s: str) -> str:
    s = s.strip().lower()
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

def extract_characters(src_root: Path, out_root: Path):
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

def extract_stories(src_root: Path, out_root: Path):
    excel_dir = try_excel_dir(src_root)
    if not excel_dir:
        return {}, ["excel dir not found"]

    candidates = ["story_review_table.json","story_review_meta_table.json","storyinfo.json"]
    found = None
    for c in candidates:
        p = excel_dir / c
        if p.exists():
            found = p; break

    stories_map = {}; warnings = []
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
                ensure_dir(out_root / "stories")
                with open(out_root / "stories" / f"{sid_slug}.json", "w", encoding="utf-8") as f:
                    json.dump({
                        "id": sid_slug, "title": title, "chapters": [], "charactersInvolved": [],
                        "note": "Minimal index entry. Full story depends on available sources."
                    }, f, ensure_ascii=False, indent=2)
        elif isinstance(data, dict) and "entry" in data and isinstance(data["entry"], list):
            for e in data["entry"]:
                sid = str(e.get("id") or e.get("key") or e.get("code") or "").lower()
                if not sid: continue
                title = e.get("name") or e.get("title") or sid
                stories_map[sid] = f"stories/{sid}.json"
                ensure_dir(out_root / "stories")
                with open(out_root / "stories" / f"{sid}.json", "w", encoding="utf-8") as f:
                    json.dump({
                        "id": sid, "title": title, "chapters": [], "charactersInvolved": [],
                        "note": "Minimal index entry. Full story depends on available sources."
                    }, f, ensure_ascii=False, indent=2)
        else:
            warnings.append(f"Unrecognized story index structure in {found.name}")
    except Exception as e:
        warnings.append(f"Failed to parse story index: {e}")

    return stories_map, warnings

def collect_story_quotes(out_root: Path, characters_map: dict, max_per_char: int = 300):
    stories_dir = out_root / "stories"
    if not stories_dir.exists():
        return 0
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
                    if not speaker or not text: continue
                    slug = slugify(speaker)
                    if slug in collected and len(text) <= 120 and len(collected[slug]) < max_per_char:
                        collected[slug].append(text)
    touched = 0
    for slug, quotes in collected.items():
        if not quotes: continue
        fp = char_file.get(slug)
        if not fp or not fp.exists(): continue
        obj = read_json(fp)
        obj["storyQuotes"] = (obj.get("storyQuotes") or []) + quotes
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        touched += 1
    return touched

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="./tmp_repo/ja_JP")
    ap.add_argument("--out", default="./docs")
    args = ap.parse_args()
    src_root = Path(args.source); out_base = Path(args.out)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    release_dir = out_base / "release" / today
    latest_dir = out_base / "latest"
    ensure_dir(release_dir); ensure_dir(latest_dir)
    characters_map, missing_tables = extract_characters(src_root, release_dir)
    stories_map, story_warn = extract_stories(src_root, release_dir)
    touched = collect_story_quotes(release_dir, characters_map, max_per_char=300)
    index_obj = {
        "version": "ak-v3",
        "generatedAt": datetime.datetime.now().astimezone().isoformat(),
        "characters": characters_map,
        "stories": stories_map,
        "notes": {"missingTables": missing_tables, "storyWarnings": story_warn, "storyQuotesAttached": touched}
    }
    for target in [release_dir, latest_dir]:
        with open(target / "index.json", "w", encoding="utf-8") as f:
            json.dump(index_obj, f, ensure_ascii=False, indent=2)
    for sub in ["characters", "stories"]:
        src = release_dir / sub
        if src.exists():
            dst = latest_dir / sub
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
    print("DONE")

if __name__ == "__main__":
    main()
