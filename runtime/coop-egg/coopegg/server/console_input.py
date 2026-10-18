import os
import sys
import threading

from .. import settings


class ConsoleInput:
    def __init__(self):
        settings.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.path = settings.STATE_DIR / "console-in"
        if self.path.exists():
            self.path.unlink()
        os.mkfifo(self.path)
        self.fd = os.open(self.path, os.O_RDWR)
        threading.Thread(target=self._copy_panel_input, daemon=True).start()

    def _copy_panel_input(self):
        try:
            for line in sys.stdin:
                self.send(line)
        except (OSError, ValueError):
            pass

    def send(self, text):
        os.write(self.fd, text.encode("utf-8"))

    def stdin_for_engine(self):
        return self.fd
