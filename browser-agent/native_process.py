"""Captured execution for the browser image's two fixed native tools.

The browser agent never accepts an executable from a request.  Keep that boundary explicit here:
only the image's absolute xdotool and ImageMagick paths can be spawned, while their validated
operation arguments remain ordinary argv elements (never a shell command).
"""

from __future__ import annotations

import os
import subprocess
import tempfile

_XDOTOOL = "/usr/bin/xdotool"
_IMAGEMAGICK_IMPORT = "/usr/bin/import"
_EXECUTABLES = frozenset({_XDOTOOL, _IMAGEMAGICK_IMPORT})


def _run(executable: str, arguments: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    if executable not in _EXECUTABLES:
        raise ValueError(f"unsupported browser-agent executable: {executable!r}")

    argv = (executable, *arguments)
    with (
        tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stdout,
        tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stderr,
    ):
        file_actions = (
            (os.POSIX_SPAWN_DUP2, stdout.fileno(), 1),
            (os.POSIX_SPAWN_DUP2, stderr.fileno(), 2),
        )
        pid = os.posix_spawn(executable, argv, os.environ, file_actions=file_actions)
        while True:
            try:
                _pid, wait_status = os.waitpid(pid, 0)
                break
            except InterruptedError:
                continue
        stdout.seek(0)
        stderr.seek(0)
        return subprocess.CompletedProcess(
            args=list(argv),
            returncode=os.waitstatus_to_exitcode(wait_status),
            stdout=stdout.read(),
            stderr=stderr.read(),
        )


def run_xdotool(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the image's fixed xdotool binary and capture its text output."""
    return _run(_XDOTOOL, arguments)


def capture_root_window(output_path: str) -> subprocess.CompletedProcess[str]:
    """Capture the X11 root window to ``output_path`` with the fixed ImageMagick binary."""
    return _run(_IMAGEMAGICK_IMPORT, ("-window", "root", output_path))
