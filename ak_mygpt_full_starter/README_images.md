# 画像参照アドオンの使い方（抜粋）
1. `images/` に画像を置く（ファイル名先頭をスラッグにすると自動判別が楽：`kelsey_01.jpg`）。
2. マニフェスト生成：
   ```bash
   python3 scripts/scan_images.py --images ./images --out ./image_manifest.json
   ```
3. 必要なら `image_manifest.json` を手修正してタグの精度を上げる（例：`白衣/メガネ/長髪` など）。
