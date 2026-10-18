import re

from ... import settings
from ...output.streams import note, step
from .. import manifest

LEAVE_ALONE = {"Native", "SandBoxCore", "Sandbox", "Coop", "DedicatedServer.Windows"}


def _dependency(module_id):
    return re.compile(
        r"[ \t]*<DependedModule\b[^>]*\bId\s*=\s*[\"']" + re.escape(module_id)
        + r"[\"'][^>]*?(?:/>|>\s*</DependedModule>)[ \t]*\r?\n?", re.I)


def apply():
    patterns = [(name, _dependency(name)) for name in settings.CLIENT_GAME_MODES]
    changed = 0
    for module in manifest.mod_modules():
        if module.name in LEAVE_ALONE:
            continue
        path = module / "SubModule.xml"
        text = manifest.read(path)
        removed = []
        for name, pattern in patterns:
            text, hits = pattern.subn("", text)
            if hits:
                removed.append(name)
        if removed:
            manifest.keep_original(path)
            manifest.write(path, text)
            changed += 1
            note(f"soft-deps: {module.name}: dropped {', '.join(removed)}")
    if changed:
        step(f"Dropped client-only game-mode dependencies from {changed} mod(s).")
