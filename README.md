# Arknights Data Site — Starter Kit

このスターターは、**外部リポを取得せず**、あなたのリポ内の `gamedata/` を唯一のソースとして
`docs/` に静的JSONを生成し、GitHub Pages で公開するための最小構成です。

## ディレクトリ構成
```
.
├─ gamedata/
│  ├─ excel/   # 例: character_table.json, item_table.json などを置く
│  └─ story/   # シナリオjsonを階層のまま置く (任意)
├─ scripts/
│  └─ extract.py
├─ docs/       # 生成物 (CIが上書き)
└─ .github/workflows/build.yml
```

## 使い方

1. **このリポに `gamedata/` を追加**  
   - `gamedata/excel/*.json`
   - `gamedata/story/**.json`（任意。置いた分だけ `docs/latest/stories/` にミラーされます）

2. **ローカルで生成を試す（任意）**
   ```bash
   python3 scripts/extract.py --source ./gamedata --out ./docs
   ```

3. **GitHub Actions で自動生成 & Pages へデプロイ**  
   `gamedata/**` や `scripts/**` を push すると CI が動作し、`docs/` を公開します。

### 出力物
- `docs/latest/excel/` : `gamedata/excel/*.json` をミラー
- `docs/latest/stories/` : `gamedata/story/**` をディレクトリ構造ごとミラー
- `docs/latest/index.json` : 目次（excel と stories の一覧）
- `docs/release/YYYY-MM-DD/**` : `latest/**` のスナップショット

> **Note**  
> 既存サイトが `docs/latest/characters/` を前提にしている場合は、`scripts/extract.py` の
> 「TODO: ここから characters を生成」のブロックにロジックを追加してください。
> （例：`character_table.json` からオペレーターごとのjsonを分割して出力する、など）

## Git LFS（任意）
シナリオjson等が巨大な場合は LFS を推奨します。
`.gitattributes` はこのスターターに同梱されています。

## ライセンス
MIT
