"""
SandboxPilotBridge --- Pilot 操作を sandbox 内に中継

Pilot の screenshot / click / type / hotkey 等の操作を、
ホストデスクトップではなく sandbox 内のアプリに向ける。

アーキテクチャ:
  Pilot -> SandboxPilotBridge -> SandboxBackend -> sandbox 内の GUI

  screenshot: sandbox backend の screenshot() を呼ぶ
  click/type/hotkey: sandbox backend の exec_in_sandbox() 経由で
                     xdotool (Linux/Docker) または コマンドファイル (WSB) を実行
  describe/verify: screenshot -> Ollama Vision (ホスト側) で解析
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SandboxPilotBridge:
    """sandbox 経由で Pilot 操作を実行"""

    def __init__(self, sandbox_backend):
        """
        Args:
            sandbox_backend: SandboxBackend インスタンス
                             (WindowsSandboxBackend or DockerBackend)
        """
        self._backend = sandbox_backend

    @property
    def is_available(self) -> bool:
        """sandbox が起動中かつ操作可能か"""
        if self._backend is None:
            return False
        try:
            from ..sandbox.sandbox_config import SandboxStatus
            return self._backend.get_status() == SandboxStatus.RUNNING
        except Exception:
            return False

    @property
    def backend_type(self) -> str:
        """バックエンド種別"""
        if self._backend is None:
            return "none"
        return self._backend.backend_type()

    # ─── スクリーンショット ───

    def screenshot(self) -> Optional[bytes]:
        """sandbox 内のスクリーンショットを取得 (PNG bytes)"""
        if self._is_docker():
            return self._backend.screenshot()
        elif self._is_wsb():
            return self._wsb_screenshot()
        return None

    # ─── GUI 操作 ───

    def click(self, x: int, y: int) -> dict:
        """sandbox 内の座標をクリック"""
        if self._is_docker():
            cmd = f"DISPLAY=:99 xdotool mousemove {x} {y} click 1"
            return self._exec(cmd)
        elif self._is_wsb():
            return self._wsb_send_command({"action": "click", "x": x, "y": y})
        return {"ok": False, "error": "No supported backend"}

    def type_text(self, text: str) -> dict:
        """sandbox 内にテキスト入力"""
        if self._is_docker():
            escaped = text.replace("'", "'\\''")
            cmd = f"DISPLAY=:99 xdotool type --clearmodifiers '{escaped}'"
            return self._exec(cmd)
        elif self._is_wsb():
            return self._wsb_send_command({"action": "type", "text": text})
        return {"ok": False, "error": "No supported backend"}

    def hotkey(self, keys: str) -> dict:
        """sandbox 内にホットキーを送信"""
        if self._is_docker():
            cmd = f"DISPLAY=:99 xdotool key {keys}"
            return self._exec(cmd)
        elif self._is_wsb():
            return self._wsb_send_command({"action": "hotkey", "keys": keys})
        return {"ok": False, "error": "No supported backend"}

    def scroll(self, amount: int) -> dict:
        """sandbox 内でスクロール"""
        if self._is_docker():
            direction = "5" if amount < 0 else "4"  # 5=down, 4=up
            count = abs(amount)
            cmd = f"DISPLAY=:99 xdotool click --repeat {count} {direction}"
            return self._exec(cmd)
        elif self._is_wsb():
            return self._wsb_send_command({"action": "scroll", "amount": amount})
        return {"ok": False, "error": "No supported backend"}

    # ─── 内部メソッド ───

    def _exec(self, command: str) -> dict:
        """sandbox 内でコマンド実行 (Docker exec)"""
        try:
            result = self._backend.exec_in_sandbox(command)
            return {"ok": result is not None, "result": result or ""}
        except Exception as e:
            logger.error(f"[SandboxPilotBridge] exec failed: {e}")
            return {"ok": False, "error": str(e)}

    def _is_docker(self) -> bool:
        return self._backend is not None and self._backend.backend_type() == "docker"

    def _is_wsb(self) -> bool:
        return self._backend is not None and self._backend.backend_type() == "windows_sandbox"

    # ─── Windows Sandbox 固有 (コマンドファイル方式) ───

    def _wsb_get_cmd_dir(self) -> Path:
        """WSB のコマンドディレクトリパスを取得"""
        workspace = self._backend.get_workspace_path()
        cmd_dir = Path(workspace) / ".helix-pilot-cmd"
        cmd_dir.mkdir(parents=True, exist_ok=True)
        return cmd_dir

    def _wsb_send_command(self, cmd: dict, timeout: float = 5.0) -> dict:
        """WSB のコマンドファイルに書き込み -> 結果を待つ"""
        try:
            cmd_dir = self._wsb_get_cmd_dir()
            cmd_file = cmd_dir / "command.json"
            result_file = cmd_dir / "result.json"

            # 前の結果をクリア
            result_file.unlink(missing_ok=True)

            # コマンド書き込み
            cmd_file.write_text(json.dumps(cmd), encoding="utf-8")

            # 結果待ち
            start = time.time()
            while time.time() - start < timeout:
                if result_file.exists():
                    try:
                        result = json.loads(result_file.read_text(encoding="utf-8"))
                        result_file.unlink(missing_ok=True)
                        return result
                    except json.JSONDecodeError:
                        pass  # まだ書き込み中の可能性
                time.sleep(0.1)

            return {"ok": False, "error": "WSB command timeout"}

        except Exception as e:
            logger.error(f"[SandboxPilotBridge] WSB command failed: {e}")
            return {"ok": False, "error": str(e)}

    def _wsb_screenshot(self) -> Optional[bytes]:
        """WSB 内のスクリーンショットを取得"""
        result = self._wsb_send_command({"action": "screenshot"}, timeout=10)
        if result.get("ok"):
            cmd_dir = self._wsb_get_cmd_dir()
            shot_path = cmd_dir / "screenshot.png"
            if shot_path.exists():
                data = shot_path.read_bytes()
                shot_path.unlink(missing_ok=True)
                return data
        return None
