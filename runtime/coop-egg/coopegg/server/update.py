import os
import shutil

from .. import settings
from ..output.streams import fail, step
from ..steam import steamcmd, workshop

INSTALLED_VERSION = "installed-coop"


def _remember_original_shared_bin(source):
    shared = source / "engine" / "bin" / "Win64_Shipping_Server"
    names = sorted(p.name for p in shared.glob("*.dll")) if shared.is_dir() else []
    settings.STATE_DIR.mkdir(parents=True, exist_ok=True)
    settings.ORIGINAL_SHARED_BIN.write_text("\n".join(names) + "\n")


def _replace_server_files(source):
    new_copy = settings.ROOT / "DedicatedServer.new"
    shutil.rmtree(new_copy, ignore_errors=True)
    step("Copying the server files into place (this can take a few minutes)...")
    shutil.copytree(source, new_copy, symlinks=True)
    shutil.rmtree(settings.SERVER_DIR, ignore_errors=True)
    os.replace(new_copy, settings.SERVER_DIR)


def ensure_installed():
    if not settings.STEAM_ACCOUNT:
        fail("Set 'Steam account' in the Startup tab. The Coop server is downloaded with an account that owns Bannerlord.")
    if not steamcmd.available():
        fail("SteamCMD is missing. Reinstall the server from the Panel (Settings > Reinstall Server).")

    latest = workshop.remote_version(settings.COOP_ITEM)
    installed = workshop.recorded_version(INSTALLED_VERSION)
    if settings.LAUNCHER.exists() and (latest is None or latest == installed):
        return

    item = workshop.fetch(settings.COOP_ITEM)
    if item is None:
        if settings.LAUNCHER.exists():
            step("Could not download the newer Coop version; using the installed one.")
            return
        fail("The Coop server could not be downloaded. Check the Steam account and password, and Steam Guard.")

    source = item.path / "DedicatedServer"
    if not source.is_dir():
        fail("The Coop Workshop item does not contain a DedicatedServer folder. Has its packaging changed?")
    _remember_original_shared_bin(source)
    _replace_server_files(source)
    shutil.rmtree(item.path, ignore_errors=True)
    if item.version:
        workshop.record_version(INSTALLED_VERSION, item.version)
    step("Coop server installed.")


def eula_message():
    return ("The Coop server will not start until its EULA is accepted. Read DedicatedServer/EULA.md "
            "and DedicatedServer/LICENSE.txt in the Files tab, then set 'Accept Coop EULA' to 1 in "
            "the Startup tab and start the server again.")
