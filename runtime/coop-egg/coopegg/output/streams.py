import sys
import threading
import time

from .. import settings
from .redact import Redactor

_state = {"redactor": None, "file": None}


def redactor():
    if _state["redactor"] is None:
        _state["redactor"] = Redactor(
            settings.STEAM_ACCOUNT, settings.STEAM_PASSWORD, settings.HIDDEN_ADDRESSES
        )
    return _state["redactor"]


class SafeStream:

    def __init__(self, real):
        self.real = real
        self.pending = ""
        self.lock = threading.Lock()

    def write(self, text):
        with self.lock:
            self.pending += text
            cut = max(self.pending.rfind("\n"), self.pending.rfind("\r"))
            if cut >= 0:
                self._emit(self.pending[:cut + 1])
                self.pending = self.pending[cut + 1:]
        return len(text)

    def flush_pending(self):
        with self.lock:
            if self.pending:
                self._emit(self.pending)
                self.pending = ""
        self.real.flush()

    def flush(self):
        self.real.flush()

    def _emit(self, text):
        text = redactor().text(text)
        self.real.write(text)
        self.real.flush()
        if _state["file"]:
            _state["file"].write(text)
            _state["file"].flush()

    def isatty(self):
        return False


def start_startup_log():
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    for old in sorted(settings.LOGS_DIR.glob("startup-*.log"))[:-14]:
        old.unlink()
    path = settings.LOGS_DIR / time.strftime("startup-%Y%m%d-%H%M%S.log", time.gmtime())
    _state["file"] = open(path, "a", encoding="utf-8", errors="replace")
    sys.stdout = SafeStream(sys.__stdout__)
    sys.stderr = SafeStream(sys.__stderr__)
    return path


def show_pending_prompt():
    if isinstance(sys.stdout, SafeStream):
        sys.stdout.flush_pending()


def note(text):
    if _state["file"]:
        _state["file"].write(redactor().text(text) + "\n")
        _state["file"].flush()


def fail(message):
    print(f"[egg] ERROR: {message}")
    sys.exit(0)


def step(text):
    print(f"[egg] {text}", flush=True)
