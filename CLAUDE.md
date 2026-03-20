# CLAUDE.md — helix-sandbox

## プロジェクト概要

helix-sandbox は、Windows Sandbox (WSB) をプログラマティックに制御する MCP サーバーです。
AI がサンドボックス内でコード実行・ファイル操作・GUI 操作を安全に行えます。

## 技術スタック

- Python 3.12 + uv（パッケージ管理）
- FastMCP（MCP サーバー実装）
- wsb.exe CLI（Windows 11 24H2）
- Docker バックエンド（オプション）

## 共有記憶（Mem0）

Mem0 MCP サーバーが接続されています。
- 過去の決定や方針を確認したい時は `search_memory` で検索すること
- ユーザーが「覚えておいて」と言ったら `add_memory` で保存すること

## 開発ルール

- 日本語で応答すること
- コード・コミットメッセージ・README は英語
- UTF-8 エンコーディング必須
- テストは pytest で作成
- `uv run pytest` でテスト実行

## 競合情報

- E2B: クラウドVM前提。ローカル完結ではない
- Cua: フレームワーク。WSB特化ではない
- WindowsSandboxMcp: 1 Star の実験段階。helix-sandbox の方が圧倒的に成熟
→ WSB + Docker双方対応 + AI GUI操作 + MCP の組み合わせは唯一無二

## ゴール

1. FastMCP でMCPサーバーとして実装
2. GitHub に公開（英語 README）
3. helix-pilot に次ぐ2番目の公開ツール
