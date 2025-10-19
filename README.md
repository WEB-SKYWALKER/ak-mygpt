# Arknights Data Site (.txt 対応)

 **外部リポの取得を行わず**、リポ内の `gamedata/` を唯一のソースにして
`docs/` 以下へ静的出力を作成し、GitHub Pages で公開します。

## 置き場所

```
gamedata/
├─ excel/   # 例: character_table.json, item_table.json など
└─ story/   # 章/話ごとの .txt （UTF-8推奨）
scripts/
└─ extract.py
```

## 生成物

```
docs/
├─ latest/
│  ├─ index.json
│  ├─ excel/                 # excel/*.json のコピー + index.json
│  └─ story/                 # story/*.txt のコピー + index.json
└─ release/YYYY-MM-DD/ ...   # 同じ内容のスナップショット
```

### `.txt` を JSON で配信したい場合
Actions の環境変数 `STORY_JSON_WRAPPER=true` にすると
`docs/latest/story_json/**.json` と `docs/release/.../story_json/**.json` も生成されます。

## ローカル実行

```bash
python scripts/extract.py
```

## GitHub Pages

- push（main）で自動ビルド → Pages へデプロイします。
