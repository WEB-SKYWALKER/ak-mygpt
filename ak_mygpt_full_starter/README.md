# Arknights Roleplay MyGPT - FULL Starter (Snapshots + Images)

## これでできること
- YoStar JPテキストから **キャラ別JSON** を生成（プロフィール/ホーム台詞/（任意）storyQuotes）
- （あれば）ストーリー索引の生成
- 画像フォルダをスキャンして **image_manifest.json** を生成 → 外見タグをRPの描写に活用
- GitHub Actions で **毎日ビルド & Pages公開**
- マイGPTは **キャッシュ6時間**、`/refresh` で即時更新

## 最短セットアップ
1. GitHubで新規リポジトリ（例: `ak-mygpt-full`）を作成し、**このフォルダの中身をアップロード**。
2. `sample_data/ja_JP/` に YoStarの `gamedata/excel/*.json` を配置。
3. `images/` に手元のキャラ画像を入れる（`kelsey_01.jpg` など）。
4. 画像マニフェスト作成：
   ```bash
   python3 scripts/scan_images.py --images ./images --out ./image_manifest.json
   ```
5. スナップショット生成：
   ```bash
   python3 scripts/extract.py --source ./sample_data/ja_JP --out ./docs
   ```
6. GitHub Pages を有効化（Settings > Pages > Source: GitHub Actions）。
7. マイGPTのシステム文には `system_prompt.txt` + `system_prompt_images.txt` を貼り付け、
   参照先には `https://<あなたのユーザー名>.github.io/<リポジトリ>/latest/index.json` と `image_manifest.json` を指定。

## 注意
- 外見の記述は **tags（テキスト）** を根拠とし、画像自体は配布・表示しない方針。
- 収録状況によりストーリー本文が無い場合は `storyQuotes` は空のままでもOK。
