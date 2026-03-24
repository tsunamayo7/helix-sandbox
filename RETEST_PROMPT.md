# helix-sandbox 再テストプロンプト

helix-sandbox の Docker イメージを再ビルドしたので、screenshot 機能の改善を中心に再テストしてください。

## 事前準備
1. 既存のコンテナがあれば削除: `docker rm -f $(docker ps -aq --filter name=helix-sandbox) 2>/dev/null`
2. helix-sandbox の Docker イメージが最新か確認: `docker images helix-sandbox`

## テスト項目

### 1. サンドボックス作成・基本動作
- create_sandbox でサンドボックスを作成（timeout_minutes=10）
- execute_command で `python3 --version` と `uname -a` を実行

### 2. screenshot 改善確認（最重要）
- create_sandbox 直後に screenshot を実行
- 返された PNG のバイト数を確認（以前は250bytesの黒画像だった）
- 2KB以上あれば改善成功
- 可能であれば画像の内容を確認（xfce4デスクトップとターミナルが見えるはず）

### 3. get_diff 改善確認
- write_file で /workspace/hello.py に `print("hello")` を書き込み
- get_diff を実行し、hello.py の変更差分が出ることを確認（以前は "No diff available" だった）

### 4. ファイル操作
- write_file / read_file / list_directory が正常動作するか確認
- パストラバーサル検査: read_file("/workspace/../etc/passwd") がブロックされるか

### 5. リソース統計
- container_stats で CPU/メモリ使用量を取得

### 6. クリーンアップ
- destroy_sandbox で破棄、sandbox_status が none になることを確認

## 変更点まとめ（確認ポイント）
- Dockerfile: Ubuntu 22.04 → 24.04 に変更、x11-utils 追加
- entrypoint.sh: Xvfb起動をxdpyinfoで確認待ち、xfce4の可視ウィンドウ数確認、ターミナル自動起動
- screenshot: 4つのキャプチャ方式を試行（xdotool+import, scrot, xwd+convert, plain import）、8回リトライ、2KB閾値
- get_diff: git init+commitで初期スナップショット、git diff --cachedで差分取得

結果を C:\Development\めも_codex_test_prompts.txt に追記してください。
