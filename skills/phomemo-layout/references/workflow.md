# Phomemo レイアウト作成の標準フロー

## 1) 仕様とスキーマを読む
- `printer-spec.md`
- `layout_job.schema.json`

## 2) JSONを作る
- 出力はJSONのみ
- `canvas` / `layers` / `output` を必ず含める
- `canvas.font_path` は存在するパスのみ

## 3) 検証する
- `PYTHONPATH=src scripts/validate_layout.py <path/to/layout.json>`
- エラーが出たら原因に対応してJSONを修正する

## 4) プレビューする
- `PYTHONPATH=src scripts/render_layout.py <path/to/layout.json> --dry-run`
- `preview_path` を確認する

## 5) 印刷する
- `PYTHONPATH=src scripts/render_layout.py <path/to/layout.json> --print`
- `printed=true` であることを確認する

## 6) 典型的な印刷失敗の原因
- `--dry-run` のまま
- `output.send_to_printer=false`
- `PHOMEMO_PRINTER_ADDRESS` 未設定
