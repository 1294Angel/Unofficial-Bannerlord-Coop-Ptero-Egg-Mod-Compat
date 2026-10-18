import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .. import settings

SUBMODULE_BLOCK = re.compile(r"<SubModule>.*?</SubModule>", re.S)
DLL_NAME = re.compile(r'<DLLName\s+value\s*=\s*"([^"]+)"', re.I)
CLIENT_BIN_FOLDERS = ("bin/Win64_Shipping_Client", "bin/Gaming.Desktop.x64_Shipping_Client")


def read(path):
    return Path(path).read_bytes().decode("utf-8-sig", "replace")


def write(path, text, bom=False):
    Path(path).write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))


def has_bom(path):
    return Path(path).read_bytes().startswith(b"\xef\xbb\xbf")


def keep_original(path):
    backup = Path(str(path) + ".orig")
    if not backup.exists():
        backup.write_bytes(Path(path).read_bytes())


def find_manifest(folder):
    folder = Path(folder)
    for candidate in [folder] + sorted(p for p in folder.iterdir() if p.is_dir()):
        for entry in candidate.iterdir():
            if entry.name.lower() == "submodule.xml":
                return entry
    return None


def module_id(manifest):
    try:
        node = ET.fromstring(Path(manifest).read_bytes()).find("Id")
        return node.get("value") if node is not None else ""
    except ET.ParseError:
        return ""


def dll_names(manifest):
    return DLL_NAME.findall(read(manifest))


def mod_modules():
    if not settings.MODULES_DIR.is_dir():
        return []
    return [d for d in sorted(settings.MODULES_DIR.iterdir())
            if d.is_dir() and d.name not in settings.STOCK_MODULES and (d / "SubModule.xml").is_file()]


def client_bin_folder(module):
    for folder in CLIENT_BIN_FOLDERS:
        if (Path(module) / folder).is_dir():
            return Path(module) / folder
    return None
