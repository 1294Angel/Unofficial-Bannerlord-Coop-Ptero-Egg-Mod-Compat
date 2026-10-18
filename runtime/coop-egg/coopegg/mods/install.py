import shutil

from .. import settings
from ..output.streams import fail, note, step
from ..steam import workshop
from . import manifest

STAMP = ".installed_version"


def workshop_mods(item_ids):
    installed = []
    items = workshop.fetch_all(item_ids) if item_ids else {}
    missing = [i for i in item_ids if items[i] is None]
    if missing:
        fail(f"Workshop item(s) {', '.join(missing)} could not be downloaded. Steam may be refusing them for "
             "now (try again later), or the ID is wrong. Fix 'Workshop mods' in the Startup tab and start again.")
    for item_id in item_ids:
        item = items[item_id]
        found = manifest.find_manifest(item.path)
        module = manifest.module_id(found) if found else ""
        if not module:
            step(f"WARNING: Workshop item {item_id} is not a Bannerlord module (no usable SubModule.xml); skipping it.")
            continue

        destination = settings.MODULES_DIR / module
        stamp = destination / STAMP
        unchanged = (item.version and (destination / "SubModule.xml").is_file()
                     and stamp.is_file() and stamp.read_text().strip() == item.version)
        if unchanged:
            note(f"mods: {module} ({item_id}) is up to date")
        else:
            step(f"Installing mod {module} ({item_id})")
            shutil.rmtree(destination, ignore_errors=True)
            shutil.copytree(found.parent, destination, symlinks=True)
            if item.version:
                stamp.write_text(item.version)
        installed.append(module)

    _remove_dropped_mods(installed + local_mod_ids())
    return installed


def _remove_dropped_mods(keep):
    if not settings.MODULES_DIR.is_dir():
        return
    for folder in settings.MODULES_DIR.iterdir():
        if folder.is_dir() and folder.name not in settings.STOCK_MODULES and folder.name not in keep:
            note(f"mods: removing {folder.name} (no longer in the mod list)")
            shutil.rmtree(folder)


def local_mod_ids():
    folder = settings.ADDONS_DIR / "local-mods"
    if not folder.is_dir():
        return []
    return [d.name for d in sorted(folder.iterdir()) if (d / "SubModule.xml").is_file()]


def local_mods():
    installed = []
    for module in local_mod_ids():
        step(f"Installing local mod {module}")
        destination = settings.MODULES_DIR / module
        shutil.rmtree(destination, ignore_errors=True)
        shutil.copytree(settings.ADDONS_DIR / "local-mods" / module, destination, symlinks=True)
        installed.append(module)
    return installed
