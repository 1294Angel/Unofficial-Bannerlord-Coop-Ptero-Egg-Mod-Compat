import os
import signal
import subprocess
import tempfile
import threading
import time

from .. import settings
from ..output import scrub
from ..output.console_filter import QuietConsole
from ..output.hints import Hints
from ..output.redact import Redactor
from ..output.streams import note, step
from . import wine
from .console_input import ConsoleInput

STOP_GRACE = 60
RAW_LIMIT = 20 * 1024 * 1024
LOG_LIMIT = 50 * 1024 * 1024


def _command(modded):
    if not modded:
        return ["wine", str(settings.LAUNCHER.relative_to(settings.ROOT))], settings.ROOT
    modules = [line.strip() for line in settings.MODULE_LIST.read_text().splitlines() if line.strip()]
    token = "_MODULES_*" + "*".join(modules) + "*_MODULES_"
    command = ["wine", str(settings.ENGINE_DIR / "dotnet" / "dotnet.exe"), "TaleWorlds.Starter.DotNetCore.dll",
               token, "/dedicatedcustomserver", settings.SERVER_PORT, "EU", "0"]
    return command, settings.SHARED_BIN


class EngineOutput(threading.Thread):

    def __init__(self, raw_path, log_path):
        super().__init__(daemon=True)
        self.raw_path, self.log_path = raw_path, log_path
        self.redactor = Redactor(settings.STEAM_ACCOUNT, settings.STEAM_PASSWORD, settings.HIDDEN_ADDRESSES)
        self.console = QuietConsole(settings.SERVER_PORT, f"logs/{os.path.basename(log_path)}")
        self.hints = Hints(lambda text: print(text, flush=True))
        self.stopping = False
        self.partial = ""
        self.position = 0

    def run(self):
        with open(self.log_path, "a", encoding="utf-8", errors="replace") as log:
            while True:
                finished = self.stopping
                data = self._read_new()
                if data:
                    self._write_lines(data, log)
                elif finished:
                    self._write_lines("\n", log)
                    return
                else:
                    time.sleep(0.2)

    def _read_new(self):
        try:
            size = os.path.getsize(self.raw_path)
            if size < self.position:
                self.position = 0
            with open(self.raw_path, "rb") as raw:
                raw.seek(self.position)
                chunk = raw.read(1 << 20)
            self.position += len(chunk)
            if size > RAW_LIMIT and self.position >= size:
                os.truncate(self.raw_path, 0)
                self.position = 0
            return chunk.decode("utf-8", "replace")
        except OSError:
            return ""

    def _write_lines(self, text, log):
        text = self.partial + text
        *lines, self.partial = text.split("\n")
        for line in lines:
            clean = self.redactor.text(line.rstrip("\r"))
            log.write(clean + "\n")
            self.hints.check(clean)
            for shown in self.console.feed(clean):
                print(shown, flush=True)
        log.flush()
        if os.path.getsize(self.log_path) > LOG_LIMIT:
            log.truncate(0)


def _listening(port):
    try:
        with open("/proc/net/udp") as table:
            return f":{int(port):04X} " in table.read().upper()
    except (OSError, ValueError):
        return False


def _heartbeat(port, raw_path, stop):
    started = time.time()
    warned = False
    while not stop.wait(15 if time.time() - started < 180 else 120):
        age = int(time.time() - started)
        up = _listening(port)
        size = os.path.getsize(raw_path) if os.path.exists(raw_path) else 0
        note(f"[watch] T+{age}s udp_{port}_listening={'yes' if up else 'no'} engine_output={size}B")
        if not up and not warned and age >= 90 and size == 0:
            warned = True
            print("[hint] After 90 s the engine has printed nothing and is not listening. It is probably stuck "
                  "before loading; see logs/ for details.", flush=True)


def _stop_engine(engine, console, asked_at):
    if asked_at[0] is None:
        asked_at[0] = time.time()
        print(f"Stop requested. Saving the world and shutting down (up to {STOP_GRACE}s).", flush=True)
        console.send("stop\n")
    elif time.time() - asked_at[0] > STOP_GRACE and engine.poll() is None:
        print("The engine did not stop on its own. Ending it.", flush=True)
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(engine.pid, sig)
            except ProcessLookupError:
                break
            time.sleep(5)


def run(modded):
    wine.ensure_display()
    command, folder = _command(modded)
    started = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    log_path = settings.LOGS_DIR / f"engine-{started}.log"
    for old in sorted(settings.LOGS_DIR.glob("engine-*.log"))[:-9]:
        old.unlink()
    raw_path = os.path.join(tempfile.gettempdir(), f"coop-engine-{started}.log")
    open(raw_path, "wb").close()

    console = ConsoleInput()
    output = EngineOutput(raw_path, log_path)
    output.start()
    stop = threading.Event()
    threading.Thread(target=_heartbeat, args=(settings.SERVER_PORT, raw_path, stop), daemon=True).start()

    step("Starting the server" + (" with mods..." if modded else "..."))
    note("launch: " + " ".join(command))
    with open(raw_path, "ab") as raw:
        engine = subprocess.Popen(command, cwd=folder, env=wine.environment(), stdin=console.stdin_for_engine(),
                                  stdout=raw, stderr=subprocess.STDOUT, start_new_session=True)
    asked_at = [None]
    signal.signal(signal.SIGTERM, lambda *_: _stop_engine(engine, console, asked_at))
    signal.signal(signal.SIGINT, lambda *_: _stop_engine(engine, console, asked_at))

    began = time.time()
    while engine.poll() is None:
        if asked_at[0] is not None:
            _stop_engine(engine, console, asked_at)
        time.sleep(0.5)

    stop.set()
    output.stopping = True
    output.join(timeout=10)
    os.remove(raw_path)
    code = engine.returncode
    duration = int(time.time() - began)
    step(f"The server stopped after {duration}s (exit code {code}).")
    (settings.LOGS_DIR / "last-exit.txt").write_text(f"exit_code={code} duration={duration}s ended={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
    scrub.scrub()
    return code
