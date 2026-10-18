import os
import time

from .. import settings
from .redact import Redactor
from .streams import note

MARKER = settings.STATE_DIR / "scrubbed-at"
GAME_LOG_SUFFIXES = (".txt", ".log", ".json", ".xml", ".html", ".dmp", ".mdmp")


def _files_under(folder, suffixes, newer_than, skip_dirs=()):
    for dirpath, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in names:
            path = os.path.join(dirpath, name)
            if suffixes and not name.lower().endswith(suffixes):
                continue
            try:
                if os.path.getmtime(path) > newer_than:
                    yield path
            except OSError:
                pass


def _steam_logs(newer_than):
    big = ("steamapps", "depotcache", "package", "public", "siteserverui")
    roots = [settings.ROOT / ".steam", settings.ROOT / ".local" / "share" / "Steam",
             settings.ROOT / "Steam", settings.ROOT / "steamcmd", settings.STEAM_CONTENT]
    for root in roots:
        for path in _files_under(root, None, newer_than, skip_dirs=big):
            if f"{os.sep}logs{os.sep}" in path or path.endswith(("_log.txt", "stderr.txt")):
                yield path


def _game_logs(newer_than):
    prefix = settings.WINEPREFIX / "drive_c"
    for path in _files_under(prefix / "ProgramData" / "Mount and Blade II Bannerlord", GAME_LOG_SUFFIXES, newer_than):
        yield path
    docs = settings.wine_documents()
    for path in _files_under(docs, GAME_LOG_SUFFIXES, newer_than):
        if f"{os.sep}logs{os.sep}" in path or f"{os.sep}ModLogs{os.sep}" in path or path.endswith(".log"):
            yield path
    for path in _files_under(prefix / "users", (".txt",), newer_than):
        if os.sep + "Desktop" + os.sep in path:
            yield path


def _rewrite(path, redactor):
    with open(path, "rb") as f:
        data = f.read()
    if b"\x00" in data[:8192] or path.lower().endswith((".dmp", ".mdmp")):
        new = redactor.blank_in_bytes(data)
    else:
        text = data.decode("utf-8", "replace")
        clean = "".join(redactor.text(line) for line in text.splitlines(keepends=True))
        new = data if clean == text else clean.encode("utf-8")
    if new != data:
        mode = os.stat(path).st_mode & 0o7777
        tmp = path + ".redact-tmp"
        with open(tmp, "wb") as f:
            f.write(new)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
        return True
    return False


def scrub(steam_only=False):
    settings.STATE_DIR.mkdir(parents=True, exist_ok=True)
    since = MARKER.stat().st_mtime if MARKER.exists() else 0
    started = time.time()
    changed = 0
    jobs = [(_steam_logs, Redactor(settings.STEAM_ACCOUNT, settings.STEAM_PASSWORD,
                                   settings.HIDDEN_ADDRESSES, every_address=True))]
    if not steam_only:
        jobs.append((_game_logs, Redactor(settings.STEAM_ACCOUNT, settings.STEAM_PASSWORD,
                                          settings.HIDDEN_ADDRESSES)))
    for finder, redactor in jobs:
        for path in finder(since):
            try:
                changed += _rewrite(path, redactor)
            except OSError as error:
                note(f"scrub: could not clean {os.path.basename(path)}: {error.__class__.__name__}")
    if not steam_only:
        MARKER.touch()
        os.utime(MARKER, (started, started))
    note(f"scrub: {changed} file(s) cleaned")
    return changed

