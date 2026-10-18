import re

from ... import settings
from ...output.streams import note, step
from .. import manifest

COMBAT_PARAMETER = re.compile(r"<combat_parameter\b[^>]*>", re.S)
COMMENT = re.compile(r"(<!--.*?-->)", re.S)
CHECK_START = re.compile(r'collision_check_starting_percent\s*=\s*"([^"]*)"')
DAMAGE_START = re.compile(r'collision_damage_starting_percent\s*=\s*"([^"]*)"')
PITCH_ATTRIBUTE = re.compile(r'(max_pitch_multiplier\s*=\s*")([^"]*)(")')
PITCH_XSLT = re.compile(r'(name\s*=\s*"max_pitch_multiplier"\s*>\s*)([0-9.]+)(\s*<)')
PARTICLE_EFFECT = re.compile(r'<effect\s+name\s*=\s*"([^"]+)"')
PARTICLE_USE = re.compile(r'particle\s*=\s*"([^"]+)"')
EMPTY_COLLISIONS = ('<?xml version="1.0" encoding="utf-8"?>\n<base type="collision_infos">\n'
                    '  <collision_infos>\n  </collision_infos>\n</base>\n')


def _raise_damage_start(match, fixed):
    element = match.group(0)
    check, damage = CHECK_START.search(element), DAMAGE_START.search(element)
    if not (check and damage):
        return element
    try:
        if float(damage.group(1)) >= float(check.group(1)):
            return element
    except ValueError:
        return element
    name = re.search(r'\bid\s*=\s*"([^"]*)"', element)
    fixed.append(name.group(1) if name else "?")
    return element[:damage.start(1)] + check.group(1) + element[damage.end(1):]


def _raise_pitch(match, raised):
    try:
        if float(match.group(2)) < 1.0:
            raised.append(match.group(2))
            return match.group(1) + "1.0" + match.group(3)
    except ValueError:
        pass
    return match.group(0)


def _fix_data_file(path, module):
    raw = path.read_bytes()
    if b"<combat_parameter" not in raw and b"max_pitch_multiplier" not in raw:
        return False
    text = raw.decode("utf-8-sig", "replace")
    fixed, raised = [], []
    parts = COMMENT.split(text)
    text = "".join(p if p.startswith("<!--") else COMBAT_PARAMETER.sub(lambda m: _raise_damage_start(m, fixed), p)
                   for p in parts)
    text = PITCH_XSLT.sub(lambda m: _raise_pitch(m, raised), PITCH_ATTRIBUTE.sub(lambda m: _raise_pitch(m, raised), text))
    if not (fixed or raised):
        return False
    manifest.write(path, text, bom=raw.startswith(b"\xef\xbb\xbf"))
    note(f"combat-params: {module.name}/{path.name}: {len(fixed)} entries raised, {len(raised)} pitch values raised")
    return True


def _known_particles():
    names = set()
    for module in settings.MODULES_DIR.iterdir():
        data = module / "ModuleData"
        if data.is_dir():
            for xml in data.glob("*.xml"):
                if "particle" in xml.name.lower():
                    names.update(PARTICLE_EFFECT.findall(xml.read_bytes().decode("utf-8", "replace")))
    return names


def _empty_unusable_collision_files(modules):
    known = _known_particles()
    count = 0
    for module in modules:
        path = module / "ModuleData" / "collision_infos.xml"
        if not path.is_file():
            continue
        used = set(PARTICLE_USE.findall(path.read_bytes().decode("utf-8", "replace"))) - {""}
        missing = sorted(used - known)
        if missing:
            path.replace(str(path) + ".disabled-for-server")
            path.write_text(EMPTY_COLLISIONS, encoding="utf-8")
            count += 1
            note(f"combat-params: {module.name}/collision_infos.xml emptied (client-only particles: {', '.join(missing[:4])})")
    return count


def apply():
    modules = manifest.mod_modules()
    changed = 0
    for module in modules:
        data = module / "ModuleData"
        if data.is_dir():
            for path in sorted(data.iterdir()):
                if path.suffix.lower() in (".xml", ".xsl") and path.is_file():
                    changed += _fix_data_file(path, module)
    changed += _empty_unusable_collision_files(modules)
    if changed:
        step(f"Adjusted {changed} mod data file(s) the server engine cannot accept as they are.")
