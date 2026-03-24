"""helix-sandbox — Subprocess Utilities

Utility for running subprocesses with hidden console windows on Windows.
"""

import subprocess
import sys
import os
import re
from typing import Any


def _is_claude_command(cmd: Any) -> bool:
    """コマンドが Claude CLI 呼び出しかどうかを判定する。"""
    if isinstance(cmd, (list, tuple)) and cmd:
        exe = os.path.basename(str(cmd[0]).strip('"')).lower()
        return exe in {"claude", "claude.exe", "claude.cmd"}
    if isinstance(cmd, str):
        return re.search(r'(^|[\s"\\/])claude(?:\.exe|\.cmd)?(?=$|[\s"])', cmd, re.IGNORECASE) is not None
    return False


def _normalize_exe_path(path: str) -> str:
    """環境変数から来る exe パス文字列を正規化する。"""
    if not path:
        return ""
    return os.path.expandvars(os.path.expanduser(path.strip().strip('"').strip("'")))


def _to_short_path(path: str) -> str | None:
    """Windows の 8.3 short path を取得。取得不能時は None。"""
    if sys.platform != "win32" or not path:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        buffer_size = 1024
        output = ctypes.create_unicode_buffer(buffer_size)
        get_short = ctypes.windll.kernel32.GetShortPathNameW
        get_short.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        get_short.restype = wintypes.DWORD
        result = get_short(path, output, buffer_size)
        if result == 0:
            return None
        short_path = output.value
        return short_path if short_path and os.path.isfile(short_path) else None
    except Exception:
        return None


def _inject_claude_windows_env(cmd: Any, kwargs: dict) -> dict:
    """
    Windows の Claude CLI 実行時に Git Bash 関連の環境変数を補完する。
    """
    if sys.platform != "win32" or not _is_claude_command(cmd):
        return kwargs

    try:
        from .platform_utils import find_git_bash_path

        git_bash = find_git_bash_path()
        if not git_bash:
            return kwargs

        env = kwargs.get("env")
        env = dict(env) if env is not None else os.environ.copy()

        existing_raw = env.get("CLAUDE_CODE_GIT_BASH_PATH", "")
        existing = _normalize_exe_path(existing_raw)
        if existing and os.path.isfile(existing):
            selected = existing
        else:
            selected = git_bash

        # CLI 側実装差異を避けるため、利用可能なら短い 8.3 パスを優先
        short_selected = _to_short_path(selected)
        env["CLAUDE_CODE_GIT_BASH_PATH"] = short_selected or selected

        # PATH に Git Bash 関連ディレクトリを補完（未登録時のみ）
        path_list = env.get("PATH", "").split(os.pathsep) if env.get("PATH") else []
        normalized = {os.path.normcase(os.path.normpath(p)) for p in path_list if p}

        bash_dir = os.path.dirname(git_bash)
        git_root = os.path.dirname(bash_dir) if os.path.basename(bash_dir).lower() == "bin" else ""
        extra_dirs = [bash_dir]
        if git_root:
            extra_dirs.extend([
                git_root,
                os.path.join(git_root, "usr", "bin"),
            ])

        prepend = []
        for d in extra_dirs:
            if not d:
                continue
            nd = os.path.normcase(os.path.normpath(d))
            if nd not in normalized:
                prepend.append(d)
                normalized.add(nd)

        if prepend:
            env["PATH"] = os.pathsep.join(prepend + path_list)

        kwargs["env"] = env
    except Exception:
        # 環境補完失敗時は既存挙動を維持
        return kwargs

    return kwargs


def run_hidden(cmd, **kwargs) -> subprocess.CompletedProcess:
    """Windows上でサブプロセスのコンソールウィンドウを非表示にして実行

    subprocess.run() のドロップイン置換。
    Windows以外のプラットフォームでは通常の subprocess.run() と同じ動作。

    Args:
        cmd: 実行コマンド (list or str)
        **kwargs: subprocess.run() に渡す追加引数

    Returns:
        subprocess.CompletedProcess
    """
    kwargs = _inject_claude_windows_env(cmd, kwargs)
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        kwargs.setdefault("startupinfo", si)
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    return subprocess.run(cmd, **kwargs)


def popen_hidden(cmd, **kwargs) -> subprocess.Popen:
    """Windows上でサブプロセスのコンソールウィンドウを非表示にしてPopen実行

    subprocess.Popen() のドロップイン置換。

    Args:
        cmd: 実行コマンド (list or str)
        **kwargs: subprocess.Popen() に渡す追加引数

    Returns:
        subprocess.Popen
    """
    kwargs = _inject_claude_windows_env(cmd, kwargs)
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        kwargs.setdefault("startupinfo", si)
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    return subprocess.Popen(cmd, **kwargs)
