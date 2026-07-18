# 戦コレ6 期待値検索ツール Render公開用

このフォルダの中身をGitHubリポジトリのルートへ置いてRenderに接続します。

## Render設定

- Service name: senkore6-ev-tool
- Environment: Python
- Plan: Pro
- Build Command: 空欄
- Start Command: `python senkore6_tool_server.py`
- Environment Variable: `SENKORE6_HOST=0.0.0.0`

`PORT` はRenderが自動設定します。

## 確認URL

- `/healthz` が `ok` を返すこと
- `/` のレスポンスヘッダー `X-App-Version` が `2026-07-19-senkore6-v16-rescue-aim` であること
