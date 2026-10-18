import json
import re
import time

SERVING = re.compile(r"^\[DedicatedServer\] SERVING")
PULSE = re.compile(r"^\[DedicatedServer\] pulse: (.*)$")
DS_EVENT = re.compile(r"^@DS@(\{.*\})\s*$")
ALERT = re.compile(r"error|exception|fatal|crash|fail|warn|refus|denied|timeout", re.I)
COMMAND_ECHO = re.compile(r"^\[DedicatedServer\] > ")
ENGINE_STATS = re.compile(r"^\[DedicatedServer Engine\]")
ENGINE_TIMESTAMP = re.compile(r"^\[\d{2}:\d{2}:\d{2}\.\d+\]")

ALWAYS_DROP = [
    re.compile(r"^\[HeadlessDiag\]"),
    re.compile(r"^\[headless MessageBox\]"),
    re.compile(r"^\[watch\]"),
    re.compile(r"Could not find the event index"),
    re.compile(r"^IL_[0-9A-F]{4}:"),
    re.compile(r"^X connection to :\d+ broken"),
    re.compile(r"^Total Size: "),
    re.compile(r"^(Loading Time:|Windows Free Memory:|Finished All)"),
    re.compile(r"^\s*\d+ -> \w+"),
    re.compile(r"^\s*$"),
]

STATUS_EVERY = 600
MAX_LINE = 400


class QuietConsole:

    def __init__(self, port="", log_name=""):
        self.port = port
        self.log_name = log_name
        self.serving = False
        self.out = []
        self.last_players = None
        self.last_line = None
        self.same_line_count = 0
        self.hidden_repeats = 0
        self.last_command_at = 0.0
        self.last_status_at = 0.0
        self.shown_commands = False

    def feed(self, line):
        self.out = []
        self._handle(line.rstrip("\r\n"))
        return self.out

    def _write(self, text):
        self.out.append(text if len(text) <= MAX_LINE else text[:MAX_LINE] + " ...")

    def _repeat_summary(self):
        if self.hidden_repeats:
            plural = "s" if self.hidden_repeats > 1 else ""
            self._write(f"    (previous line repeated {self.hidden_repeats} more time{plural})")
            self.hidden_repeats = 0

    def _emit(self, line):
        if line == self.last_line:
            self.same_line_count += 1
            if self.same_line_count <= 2:
                self._write(line)
            else:
                self.hidden_repeats += 1
            return
        self._repeat_summary()
        self.last_line = line
        self.same_line_count = 1
        self._write(line)

    def _banner(self):
        port = f" on UDP port {self.port}" if self.port else ""
        self._write("")
        self._write("=" * 70)
        self._write(f" SERVER UP{port} - streamlined console")
        self._write(" Type a command below and press Enter. 'help' lists them.")
        self._write(" Built in: status, players, say <message>, kick <player>, save, stop")
        if self.log_name:
            self._write(f" Full engine output: {self.log_name}")
        self._write("=" * 70)
        self._write("")

    def _event(self, raw):
        try:
            event = json.loads(raw)
        except ValueError:
            return
        kind = event.get("ev")
        if kind == "players":
            names = [(p.get("name") or str(p.get("id", ""))) if isinstance(p, dict) else str(p)
                     for p in event.get("list", [])]
            if names != self.last_players:
                self.last_players = names
                self._repeat_summary()
                self._write(f"[players] {len(names)} online" + (": " + ", ".join(names) if names else ""))
        elif kind == "state":
            self._repeat_summary()
            self._write(f"[state] {event.get('phase', '?')}")
        elif kind == "commands" and not self.shown_commands:
            self.shown_commands = True
            builtin = ", ".join(event.get("builtin", []))
            self._write(f"[commands] built in: {builtin}; {len(event.get('game', []))} game commands "
                        "(e.g. campaign.add_gold_to_hero) - 'help' for the full list")

    def _handle(self, line):
        if not self.serving:
            self._write(line)
            if SERVING.search(line):
                self.serving = True
                self.last_status_at = time.time()
                self._banner()
            return

        event = DS_EVENT.match(line)
        if event:
            self._event(event.group(1))
            return
        if COMMAND_ECHO.match(line):
            self.last_command_at = time.time()
        pulse = PULSE.match(line)
        if pulse:
            self._pulse(pulse.group(1))
            return
        if line.startswith("@DS@"):
            return
        if ENGINE_TIMESTAMP.match(line) or ENGINE_STATS.match(line):
            if not ALERT.search(line):
                return
        elif any(pattern.search(line) for pattern in ALWAYS_DROP):
            return
        self._emit(line)

    def _pulse(self, text):
        if time.time() - self.last_command_at < 3:
            self._emit("[DedicatedServer] status: " + text)
        elif time.time() - self.last_status_at >= STATUS_EVERY:
            self.last_status_at = time.time()
            self._repeat_summary()
            self._write(f"[status] {text}")
