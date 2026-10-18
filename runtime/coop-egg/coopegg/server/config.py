import json
import re

from .. import settings
from ..output.streams import note

STRING = r'"(?:[^"\\]|\\.)*"'


def _wanted():
    return {
        "saveName": (json.dumps(settings.SAVE_NAME), STRING),
        "password": (json.dumps(settings.SERVER_PASSWORD), STRING),
        "port": (settings.SERVER_PORT, r"\d+"),
        "steam": ("false", r"true|false"),
    }


def _first_time_file():
    lines = ["{"]
    for key, (value, _kind) in _wanted().items():
        lines.append(f'  "{key}": {value},')
    lines += ['  "autosaveMinutes": 5,', '  "logFile": true', "}", ""]
    return "\n".join(lines)


def apply():
    path = settings.coop_data_dir() / "server-config.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_first_time_file(), encoding="utf-8")
        note("config: created server-config.json")
        return

    text = path.read_text(encoding="utf-8-sig")
    for key, (value, kind) in _wanted().items():
        text, count = re.subn(rf'("{key}"\s*:\s*)(?:{kind})', lambda m: m.group(1) + value, text, count=1)
        if not count:
            note(f"config: {key} not found in server-config.json; left as it is")
    path.write_text(text, encoding="utf-8")
    note("config: server-config.json updated from the Panel settings")
