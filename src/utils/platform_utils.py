"""
platform_utils.py — クロスプラットフォーム共通ヘルパー

Windows / macOS / Linux でそれぞれ異なる実装が必要な処理を一元管理する。
将来のプラットフォーム追加時は elif ブランチを追加するだけでよい。
"""

import os
import sys
import shutil
import logging

logger = logging.getLogger(__name__)


def show_error_dialog(message: str, title: str = "Helix AI Studio - Error") -> None:
    """クロスプラットフォームのエラーダイアログを表示する。

    Args:
        message: 表示するエラーメッセージ
        title:   ダイアログのタイトル
    """
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
        except Exception as e:
            logger.debug(f"Windows error dialog unavailable: {e}")
    elif sys.platform == 'darwin':
        try:
            import subprocess
            # osascript の引数内でダブルクォートをエスケープ
            safe_msg = message.replace('"', '\\"')
            safe_title = title.replace('"', '\\"')
            subprocess.run(
                [
                    'osascript', '-e',
                    f'display dialog "{safe_msg}" with title "{safe_title}" '
                    f'buttons {{"OK"}} with icon stop',
                ],
                timeout=10,
            )
        except Exception as e:
            logger.debug(f"macOS error dialog unavailable: {e}")
    else:
        # Linux / その他: stderr にフォールバック
        print(f"[{title}] {message}", file=sys.stderr)


def find_npm_global_command(cmd_name: str) -> list:
    """プラットフォーム別の npm グローバルコマンドのパス候補を返す。

    shutil.which() で見つからなかった場合のフォールバック検索に使用する。
    存在確認は呼び出し側で行うこと（os.path.exists を使用）。

    Args:
        cmd_name: 検索するコマンド名（例: 'claude', 'codex'）

    Returns:
        list[str]: パス候補のリスト（存在しないパスを含む場合がある）
    """
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA', '')
        localappdata = os.environ.get('LOCALAPPDATA', '')
        userprofile = os.environ.get('USERPROFILE', '')
        return [
            os.path.join(appdata, 'npm', f'{cmd_name}.cmd'),
            os.path.join(appdata, 'npm', cmd_name),
            os.path.join(localappdata, 'npm', f'{cmd_name}.cmd'),
            os.path.join(localappdata, 'npm', cmd_name),
            os.path.join(userprofile, 'AppData', 'Roaming', 'npm', f'{cmd_name}.cmd'),
            os.path.join(userprofile, 'AppData', 'Roaming', 'npm', cmd_name),
        ]
    elif sys.platform == 'darwin':
        home = os.path.expanduser('~')
        return [
            os.path.join(home, '.npm-global', 'bin', cmd_name),
            f'/usr/local/bin/{cmd_name}',       # Intel Mac (Homebrew)
            f'/opt/homebrew/bin/{cmd_name}',    # Apple Silicon (Homebrew)
            f'/usr/bin/{cmd_name}',
        ]
    else:
        # Linux / その他
        home = os.path.expanduser('~')
        return [
            os.path.join(home, '.npm-global', 'bin', cmd_name),
            f'/usr/local/bin/{cmd_name}',
            f'/usr/bin/{cmd_name}',
        ]


def find_git_bash_path() -> str | None:
    """
    Windows 上の Git Bash 実行ファイルを探索して返す。

    Returns:
        str | None: 見つかった bash.exe の絶対パス。見つからない場合は None。
    """
    if sys.platform != 'win32':
        return None

    # ユーザー指定が有効なら最優先
    env_path = (os.environ.get("CLAUDE_CODE_GIT_BASH_PATH") or "").strip().strip('"')
    if env_path and os.path.isfile(env_path):
        return env_path

    candidates = []
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    userprofile = os.environ.get("USERPROFILE", "")

    for base in (program_files, program_files_x86):
        if base:
            candidates.extend([
                os.path.join(base, "Git", "bin", "bash.exe"),
                os.path.join(base, "Git", "usr", "bin", "bash.exe"),
            ])

    if localappdata:
        candidates.extend([
            os.path.join(localappdata, "Programs", "Git", "bin", "bash.exe"),
            os.path.join(localappdata, "Programs", "Git", "usr", "bin", "bash.exe"),
        ])

    if userprofile:
        candidates.append(
            os.path.join(userprofile, "scoop", "apps", "git", "current", "bin", "bash.exe")
        )

    bash_in_path = shutil.which("bash")
    if bash_in_path:
        lower_path = bash_in_path.lower().replace("/", "\\")
        if lower_path.endswith("\\bash.exe") and "\\git\\" in lower_path:
            candidates.append(bash_in_path)

    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None
