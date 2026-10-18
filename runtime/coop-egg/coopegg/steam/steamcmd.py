import fcntl
import os
import pty
import re
import select
import struct
import subprocess
import sys
import termios
from dataclasses import dataclass

from .. import settings
from ..output import scrub, streams

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
PROGRESS = re.compile(r"progress:\s*([\d.]+)|^\[\s*(\d+)%\]")
LINE_END = re.compile(r"(?<=[\r\n])")


@dataclass
class Result:
    code: int
    text: str


class _Tidy:

    def __init__(self):
        self.last_bucket = {}
        self.last_line = None
        self.partial = ""

    def lines(self, text, final=False):
        parts = LINE_END.split(self.partial + ANSI.sub("", text))
        self.partial = "" if parts[-1].endswith(("\r", "\n")) else parts.pop()
        if final and self.partial:
            parts.append(self.partial)
            self.partial = ""
        for part in parts:
            line = part.strip()
            if not line or line == self.last_line:
                continue
            self.last_line = line
            match = PROGRESS.search(line)
            if match:
                percent = int(float(match.group(1) or match.group(2)))
                key = re.sub(r"[\d.]+", "#", line.split("progress")[0].split("(")[0])
                if self.last_bucket.get(key) == percent // 10:
                    continue
                self.last_bucket[key] = percent // 10
            yield line + "\n"


def available():
    return settings.STEAMCMD_SH.exists()


def run(*commands):
    login = ["+login", settings.STEAM_ACCOUNT]
    if settings.STEAM_PASSWORD:
        login.append(settings.STEAM_PASSWORD)
    argv = [str(settings.STEAMCMD_SH), "+force_install_dir", str(settings.STEAM_CONTENT), *login, *commands, "+quit"]

    master, slave = pty.openpty()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 250, 0, 0))
    process = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave,
                               close_fds=True, start_new_session=True)
    os.close(slave)

    tidy = _Tidy()
    shown = []

    def show(lines):
        for line in lines:
            sys.stdout.write(line)
            shown.append(line)

    watching = [master]
    typed = sys.stdin.fileno() if sys.stdin and not sys.stdin.closed else None
    if typed is not None:
        watching.append(typed)

    while True:
        ready, _, _ = select.select(watching, [], [], 0.3)
        if not ready:
            show(tidy.lines("", final=True))
            continue
        if master in ready:
            try:
                data = os.read(master, 65536)
            except OSError:
                break
            if not data:
                break
            show(tidy.lines(data.decode("utf-8", "replace")))
        if typed in ready:
            data = os.read(typed, 1024)
            if data:
                os.write(master, data)
            else:
                watching.remove(typed)
                typed = None

    show(tidy.lines("", final=True))
    os.close(master)
    code = process.wait()
    scrub.scrub(steam_only=True)
    return Result(code, "".join(shown))
