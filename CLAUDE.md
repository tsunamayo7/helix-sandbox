# CLAUDE.md — helix-sandbox

## プロジェクト概要

helix-sandbox は、Docker と Windows Sandbox の両方に対応したセキュアなサンドボックス MCP サーバーです。
AI エージェントがサンドボックス内でコード実行・ファイル操作・GUI 操作を安全に行えます。

## 技術スタック

- Python 3.12 + uv
- FastMCP（MCP サーバー）
- Docker SDK（Docker バックエンド）
- wsb.exe CLI（Windows Sandbox バックエンド）

## 開発ルール

- 日本語で応答すること
- コード・コミットメッセージ・README は英語
- テスト: `uv run python -m pytest tests/ -v`
- リント: `uv run ruff check src/ server.py tests/`
- 構文チェック: `uv run python -m py_compile server.py`

## 競合情報

- E2B: クラウドVM前提、ローカル完結ではない
- Cua: フレームワーク、WSB特化ではない
- WindowsSandboxMcp: 実験段階（1 Star）
- → WSB + Docker双方対応 + AI GUI操作 + MCP の組み合わせは唯一無二

## 状態

- [x] PyQt6 依存除去（コールバックベースに移行）
- [x] FastMCP server.py 実装（10 MCPツール）
- [x] Dockerfile 作成
- [x] pytest テスト（20テスト）
- [x] GitHub Actions CI
- [x] 英語 README
- [ ] GitHub 公開
