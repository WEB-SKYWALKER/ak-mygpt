# Arknights Roleplay MyGPT - Full Upstream Starter

YoStarリポから毎回自動取得してスナップショットを生成し、GitHub Pagesに公開するスターターです。

## セットアップ
1. このスターターの中身を空のリポジトリへアップロード
2. Actions → “Build & Publish Snapshots (YoStar upstream)” → Run workflow
3. Settings → Pages → Deployed を確認（URL例: https://<あなた>.github.io/<repo>/latest/index.json）
4. マイGPTのシステム文に `system_prompt.txt` + `system_prompt_images.txt` を貼り、参照先に上記URL（＋ `image_manifest.json`）を指定

## 画像タグ（任意）
- `images/` に画像を置き、`scripts/scan_images.py --images ./images --out ./image_manifest.json` で作成
- 公開は `image_manifest.json` のみを推奨（画像は再配布しない）
