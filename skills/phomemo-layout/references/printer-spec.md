# Phomemo M02 Pro 印刷仕様（レイアウト設計用）

## 物理/画像制約
- **幅は常に 576px 固定**（M02 Proの印字幅に合わせる）
- 背景は白（#FFFFFF）、文字は黒を基本
- 出力は最終的に**しきい値で2値化**される（`output.threshold`）

## 実寸換算（重要）
- M02 Pro（300dpi想定）では、おおよそ **300px = 1 inch**
- cm → px の目安:
  - `px = cm / 2.54 * 300`
  - 例: **5cm ≒ 591px**
- 固定幅 576px は `576 / 300 * 2.54 ≒ 4.88cm`
  - **横方向（X方向）だけで5cmを表現するのは不可**
  - 5cm以上が必要な表現（定規など）は **紙送り方向（Y方向）** で長さを確保する

## 長尺データ送信の注意
- Bluetooth送信で途中停止する場合があるため、画像を縦方向に分割して送る
- `output.slice_height`（例: 1400）で画像をスライス
- `output.chunk_rows`（例: 200、1〜256）で送信ブロックを小さくする

## JSONレイアウトの基本
- `canvas` / `layers` / `output` を必ず含める
- `layers[].type` は `text` または `image`
- `text` レイヤーは `text` または `text_file` のどちらかを持つ
- `image` レイヤーは `path` を持つ（ローカルファイル）

## フォント
- `canvas.font_path` は **存在するフォントパスのみ**を指定（存在しないパスを創作しない）
- 候補例（環境により存在するものを使う）:
  - `/usr/local/share/fonts/HackGen_NF/HackGenConsoleNFJ-Regular.ttf`
  - `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`
  - 絵文字は `/usr/local/share/fonts/NotoEmoji-Regular.ttf` などを `fallback_fonts` へ

## レイアウト品質のヒント
- 余白: `canvas.margin` を 20〜40 程度
- テキスト幅: おおむね `576 - margin*2`
- 文字が潰れる場合は `font_size` を上げるか細いウェイトのフォントに切替

## 方向（縦横）について
- 実機側の見え方によっては「縦横が逆」に感じることがある
- `output.rotate` で回転を制御できる:
  - `auto`: 横長（width > height）のとき90度回転（既定）
  - `none`: 回転しない
  - `cw90` / `ccw90`: 強制回転
- **長尺の定規などは回転に頼らず、最初からY方向に必要pxを確保する**
