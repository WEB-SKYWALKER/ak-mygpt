# scripts/build_knowledge_bundles.py
import argparse, json, math, os, re, sys
from pathlib import Path

def read_text(path: Path) -> str:
    return path.read_text("utf-8", errors="ignore")

def load_json(path: Path):
    try:
        return json.loads(read_text(path))
    except Exception:
        return None

PRI_TEXT_KEYS = ["text", "content", "body", "value", "message"]

def extract_text_from_story_json(payload) -> str:
    """
    story_json/* の想定フォーマットが色々あるため、できるだけ寛容に本文を抽出。
    - 文字列ならそのまま
    - dict: text/content/body/value/message のどれか
    - list/dict の深い所に文字列が散在 → 文字列リーフを最大 50,000 文字まで収集
    """
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload

    if isinstance(payload, dict):
        for k in PRI_TEXT_KEYS:
            if k in payload and isinstance(payload[k], str) and payload[k].strip():
                return payload[k]
        # よくある別形式：{"data":[{"text":"..."}, ...]}
        if "data" in payload and isinstance(payload["data"], list):
            parts = []
            for row in payload["data"]:
                if isinstance(row, dict):
                    t = row.get("text") or row.get("content") or row.get("body") or ""
                    if isinstance(t, str):
                        parts.append(t)
            if parts:
                return "\n".join(parts)

    # フォールバック：全ての文字列リーフをかき集める
    def walk(v, out):
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, dict):
            for vv in v.values():
                walk(vv, out)
        elif isinstance(v, (list, tuple)):
            for vv in v:
                walk(vv, out)

    strings = []
    walk(payload, strings)
    text = "\n".join(s for s in strings if isinstance(s, str))
    # 大きすぎる場合は少しだけ切る
    return text[:50000]

def json_compact(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def chunk_text(text: str, max_chars: int):
    for i in range(0, len(text), max_chars):
        yield text[i:i+max_chars]

def make_record(_id: str, title: str, source: str, tags: list[str], text: str) -> dict:
    return {
        "id": _id,
        "title": title,
        "source": source,
        "tags": tags,
        "text": text
    }

def write_bundles(records, out_dir: Path, bundle_size_mb: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    # バイトサイズで分割（MyGPT の Knowledge は 20–25MB 程度が扱いやすい）
    limit = bundle_size_mb * 1024 * 1024

    idx = 1
    cur = []
    cur_size = 0

    def flush():
        nonlocal idx, cur, cur_size
        if not cur:
            return
        out_path = out_dir / f"bundle_{idx:03}.jsonl"
        with out_path.open("w", encoding="utf-8", newline="\n") as f:
            for line in cur:
                f.write(line + "\n")
        print(f"[write] {out_path}  ({len(cur)} recs, ~{cur_size/1024/1024:.2f} MB)")
        idx += 1
        cur = []
        cur_size = 0

    for r in records:
        line = json_compact(r)
        sz = len(line.encode("utf-8")) + 1
        if cur and cur_size + sz > limit:
            flush()
        cur.append(line)
        cur_size += sz

    flush()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story-root", required=True, help="docs/latest/story_json へのパス")
    ap.add_argument("--excel-root", required=True, help="docs/latest/excel へのパス")
    ap.add_argument("--out-dir", required=True, help="出力先ディレクトリ")
    ap.add_argument("--bundle-size-mb", type=int, default=25)
    ap.add_argument("--base-url", default="https://web-skywalker.github.io/ak-mygpt/latest")
    ap.add_argument("--max-story", type=int, default=0, help="story_json の最大件数(0=制限なし)")
    ap.add_argument("--max-excel", type=int, default=0, help="excel の最大件数(0=制限なし)")
    ap.add_argument("--excel-chunk", type=int, default=15000, help="excel の1レコード文字数の上限（分割）")
    args = ap.parse_args()

    story_root = Path(args.story_root)
    excel_root = Path(args.excel_root)
    out_dir = Path(args.out_dir)

    if not story_root.exists() or not excel_root.exists():
        print("ERROR: story-root / excel-root が見つかりません。", file=sys.stderr)
        sys.exit(1)

    base_story = f"{args.base-url}/story_json"
    base_excel = f"{args.base-url}/excel"

    records = []

    # 1) story_json
    story_files = sorted(story_root.rglob("*.json"))
    if args.max_story > 0:
        story_files = story_files[:args.max_story]

    for p in story_files:
        rel = p.relative_to(story_root).as_posix()
        payload = load_json(p)
        text = extract_text_from_story_json(payload)
        if not text.strip():
            continue

        rec = make_record(
            _id=f"story:{rel}",
            title=f"story_json/{rel}",
            source=f"{base_story}/{rel}",
            tags=["arknights", "story"],
            text=text
        )
        records.append(rec)

    # 2) excel（巨大になりがちなので分割）
    excel_files = sorted(excel_root.glob("*.json"))
    if args.max_excel > 0:
        excel_files = excel_files[:args.max_excel]

    for p in excel_files:
        rel = p.name
        payload = load_json(p)
        if payload is None:
            # 失敗時は生テキスト
            payload_text = read_text(p)
        else:
            payload_text = json_compact(payload)

        # 長大なファイルはチャンク分割
        part_idx = 1
        for chunk in chunk_text(payload_text, args.excel_chunk):
            suffix = "" if part_idx == 1 else f" (part {part_idx})"
            rec = make_record(
                _id=f"excel:{rel}#{part_idx}",
                title=f"excel/{rel}{suffix}",
                source=f"{base_excel}/{rel}",
                tags=["arknights", "excel"],
                text=chunk
            )
            records.append(rec)
            part_idx += 1

    # 3) 書き出し
    write_bundles(records, out_dir, args.bundle_size_mb)
    print(f"[done] total records: {len(records)}")

if __name__ == "__main__":
    main()
