"""File upload into the browser — two modes, ported from two separate CLIs that used to run here.

`mode="dom"` — rootfs/usr/local/bin/chrome-upload's approach: CDP DOM.setFileInputFiles on a page's
<input type=file>, no OS dialog at all (see cdp_client.upload_dom).

`mode="native"` — rootfs/usr/local/bin/uiupload's approach: complete a native GTK/Qt "Open File"
dialog via REAL XTEST events (xdotool). Needed because synthetic events (XSendEvent) are silently
discarded by GTK. Faithful port of uiupload's exact fallback sequence: Ctrl+L + path + Enter, then
mnemonic (Alt+O / Alt+A), then a real click on the geometrically-derived "Open" button.

Both modes receive the file's bytes over HTTP and write them to an EPHEMERAL temp path inside this
container first — neither mode ever assumes a path shared with another container.
"""

from __future__ import annotations

import os
import subprocess
import time

import native_process

os.environ.setdefault("DISPLAY", ":1")

DEFAULT_DIALOG_RE = "Open File|Save File|Save As|Open Files|Select|Abrir|Salvar|Selecionar arquivo"


class UploadError(Exception):
    """Neither CDP DOM injection nor native-dialog completion could attach the file."""


def _run(*a: str) -> subprocess.CompletedProcess:
    return native_process.run_xdotool(*a)


def _find_dialog(title_regex: str) -> str | None:
    search = _run("search", "--name", title_regex)
    if search.returncode != 0 or not search.stdout.strip():
        return None
    candidates = []
    for wid in search.stdout.split():
        name = _run("getwindowname", wid)
        title = name.stdout.strip() if name.returncode == 0 else ""
        if "Chrome" in title or "Telegram" in title:
            continue
        candidates.append(wid)
    return candidates[-1] if candidates else None


def upload_native(path: str, title_regex: str = DEFAULT_DIALOG_RE) -> str:
    """Complete an already-open native file dialog with `path`. Raises UploadError on failure."""
    wid = None
    for _ in range(40):  # ~8s wait for the dialog to appear
        wid = _find_dialog(title_regex)
        if wid:
            break
        time.sleep(0.2)
    if not wid:
        raise UploadError(f"no file dialog found (regex: {title_regex})")

    _run("windowactivate", "--sync", wid)
    time.sleep(0.2)
    _run("key", "--clearmodifiers", "ctrl+l")  # GTK location bar
    time.sleep(0.2)
    _run("type", "--clearmodifiers", "--delay", "12", path)
    time.sleep(0.2)
    _run("key", "--clearmodifiers", "Return")
    time.sleep(0.5)
    if not _find_dialog(title_regex):
        return f"'{path}' opened (path + Enter)"

    # A) GTK Open-button mnemonic (no coordinates): "_Open" -> Alt+O; "_Abrir" -> Alt+A.
    for mnemonic in ("alt+o", "alt+a"):
        _run("key", "--clearmodifiers", mnemonic)
        time.sleep(0.5)
        if not _find_dialog(title_regex):
            return f"'{path}' opened (mnemonic {mnemonic})"

    # B) Real XTEST click on the Open button (bottom-right corner of the window).
    geom = _run("getwindowgeometry", "--shell", wid)
    if geom.returncode == 0:
        values = dict(line.split("=", 1) for line in geom.stdout.splitlines() if "=" in line)
        if "WIDTH" in values and "HEIGHT" in values and "X" in values and "Y" in values:
            ox = int(values["X"]) + int(values["WIDTH"]) - 52
            for dy in (30, 38, 22, 46):
                oy = int(values["Y"]) + int(values["HEIGHT"]) - dy
                _run("mousemove", str(ox), str(oy))
                time.sleep(0.12)
                _run("click", "1")
                time.sleep(0.4)
                if not _find_dialog(title_regex):
                    return f"'{path}' opened (real click on Open)"

    raise UploadError("dialog still open after path+Enter, mnemonic, and coordinate-click fallbacks")
