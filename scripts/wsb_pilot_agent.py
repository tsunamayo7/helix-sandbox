"""
WSB Pilot Agent --- Windows Sandbox 内で動作する操作エージェント

MappedFolder (C:\\workspace\\.helix-pilot-cmd\\) を監視し、
コマンドファイルが書き込まれたら GUI 操作を実行して結果を返す。

コマンドファイル形式 (JSON):
  command.json: {"action": "click", "x": 100, "y": 200}
  result.json:  {"ok": true, "result": "clicked"}

対応アクション:
  click     - 座標クリック (SendInput)
  type      - テキスト入力 (SendKeys)
  hotkey    - ホットキー (SendKeys)
  scroll    - マウススクロール (mouse_event)
  screenshot - スクリーンキャプチャ (GDI+)

セキュリティ:
  - sandbox 内でのみ動作する前提
  - コマンドファイル以外からの入力は受け付けない
"""

import json
import time
import ctypes
import subprocess
import sys
from pathlib import Path

COMMAND_DIR = Path(r"C:\workspace\.helix-pilot-cmd")
COMMAND_FILE = COMMAND_DIR / "command.json"
RESULT_FILE = COMMAND_DIR / "result.json"
SCREENSHOT_FILE = COMMAND_DIR / "screenshot.png"


def click(x: int, y: int):
    """SendInput で座標クリック"""
    ctypes.windll.user32.SetCursorPos(x, y)
    time.sleep(0.05)
    # mouse_event: LEFTDOWN=0x0002, LEFTUP=0x0004
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.02)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)


def type_text(text: str):
    """PowerShell SendKeys でテキスト入力"""
    # SendKeys の特殊文字をエスケープ
    escaped = text.replace("{", "{{").replace("}", "}}") \
                  .replace("+", "{+}").replace("^", "{^}") \
                  .replace("%", "{%}").replace("~", "{~}")
    ps = (
        'Add-Type -AssemblyName System.Windows.Forms; '
        f'[System.Windows.Forms.SendKeys]::SendWait("{escaped}")'
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True, timeout=10,
    )


def hotkey(keys: str):
    """PowerShell SendKeys でホットキー送信

    keys 形式: "ctrl+shift+1" -> SendKeys: "^+1"
    """
    mapping = {"ctrl": "^", "shift": "+", "alt": "%"}
    parts = keys.lower().split("+")
    sendkeys_str = ""
    for part in parts:
        part = part.strip()
        if part in mapping:
            sendkeys_str += mapping[part]
        else:
            sendkeys_str += part
    ps = (
        'Add-Type -AssemblyName System.Windows.Forms; '
        f'[System.Windows.Forms.SendKeys]::SendWait("{sendkeys_str}")'
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True, timeout=10,
    )


def scroll(amount: int):
    """mouse_event でスクロール"""
    # MOUSEEVENTF_WHEEL = 0x0800, amount は 120 の倍数
    ctypes.windll.user32.mouse_event(0x0800, 0, 0, amount * 120, 0)


def screenshot() -> str:
    """PowerShell GDI+ でスクリーンキャプチャ"""
    out_path = str(SCREENSHOT_FILE)
    ps = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$gfx.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bmp.Save('{out_path}')
$gfx.Dispose()
$bmp.Dispose()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True, timeout=15,
    )
    return out_path


def process_command(cmd: dict) -> dict:
    """コマンドを処理して結果を返す"""
    action = cmd.get("action", "")

    if action == "click":
        click(int(cmd["x"]), int(cmd["y"]))
        return {"ok": True, "result": f"clicked ({cmd['x']}, {cmd['y']})"}

    elif action == "type":
        type_text(cmd.get("text", ""))
        return {"ok": True, "result": "typed"}

    elif action == "hotkey":
        hotkey(cmd.get("keys", ""))
        return {"ok": True, "result": f"hotkey: {cmd.get('keys', '')}"}

    elif action == "scroll":
        scroll(int(cmd.get("amount", 0)))
        return {"ok": True, "result": f"scrolled {cmd.get('amount', 0)}"}

    elif action == "screenshot":
        path = screenshot()
        return {"ok": True, "path": path}

    elif action == "ping":
        return {"ok": True, "result": "pong"}

    else:
        return {"ok": False, "error": f"Unknown action: {action}"}


def main():
    """コマンドファイル監視ループ"""
    COMMAND_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[WSB Pilot Agent] Watching {COMMAND_DIR}")
    print(f"[WSB Pilot Agent] Python {sys.version}")

    while True:
        if COMMAND_FILE.exists():
            try:
                raw = COMMAND_FILE.read_text(encoding="utf-8")
                cmd = json.loads(raw)
                result = process_command(cmd)
            except json.JSONDecodeError as e:
                result = {"ok": False, "error": f"Invalid JSON: {e}"}
            except Exception as e:
                result = {"ok": False, "error": str(e)}

            try:
                RESULT_FILE.write_text(
                    json.dumps(result, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception:
                pass

            try:
                COMMAND_FILE.unlink(missing_ok=True)
            except Exception:
                pass

        time.sleep(0.1)  # 100ms ポーリング


if __name__ == "__main__":
    main()
