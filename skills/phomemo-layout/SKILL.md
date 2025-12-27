---
name: phomemo-layout
description: Phomemo M02 Pro向けのレイアウトJSONの生成・修正・検証・プレビュー/印刷を扱う。576px固定幅、長尺はY方向で確保、回転/分割送信などの制約を踏まえて設計する依頼、天気/ToDo/定規などの印刷テンプレを作る依頼、dry_runでプレビューしてから印刷する依頼で使う。
---

# Phomemo Layout Skill

## 目的
Phomemo M02 Pro向けのレイアウトJSONを、仕様とスキーマに沿って生成・検証し、プレビュー/印刷まで実行する。

## 参照
- `references/printer-spec.md`
- `references/layout_job.schema.json`
- `references/layout.sample.json`
- `references/workflow.md`

## 手順
1) `references/printer-spec.md` と `references/layout_job.schema.json` を読む。
2) `references/layout.sample.json` を参考に、JSONのみを出力する。
3) `scripts/validate_layout.py` で検証する。
4) `scripts/render_layout.py --dry-run` でプレビューする。
5) 印刷が必要なら `scripts/render_layout.py --print` を使う。

## 使い分けの目安
- 天気: 日付/天候/気温/降水確率の見やすさを優先し、余白と行間を広めにする。
- ToDo: 箇条書きの可読性を優先し、文字サイズと行間を固定する。
- 定規: 物理長の精度を優先し、Y方向に必要pxを確保する。

## 注意
- スクリプト実行時は `PYTHONPATH=src` を設定する（またはパッケージとしてインストールする）。
- 出力はJSONのみ。説明文やコードブロックは入れない。
- 576px固定幅。長尺はY方向で確保する。
- `output.send_to_printer` と `--print` の両方を満たさないと印刷されない。
- `dry_run` の既定はプレビューのみなので、印刷時は明示的に `--print` を使う。
- `canvas.font_path` は存在するパスのみを指定する。
