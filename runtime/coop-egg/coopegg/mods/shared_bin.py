import shutil

from .. import settings
from ..output.streams import note, step
from . import manifest

STOCK_WITH_DLLS = ("Native", "SandBox", "SandBoxCore", "Sandbox", "DedicatedServer.Windows")
COOP_PINNED = {"Common.dll", "Coop.Core.dll", "Coop.Steam.dll", "Coop.dll", "GameInterface.dll", "Missions.dll"}
HEADLESS_UNSAFE = {"cimgui.dll", "BattleArtilleryReworked.dll", "EOE.CustomBattlePatch.dll",
                   "RF_BattleAI.dll", "StoryMode.dll"}
CLIENT_BIN = ("bin/Win64_Shipping_Server", "bin/Win64_Shipping_Client", "bin/Gaming.Desktop.x64_Shipping_Client")


def clean():
    if not settings.ORIGINAL_SHARED_BIN.is_file() or not settings.SHARED_BIN.is_dir():
        return
    original = set(settings.ORIGINAL_SHARED_BIN.read_text().split())
    stock_names = set()
    for module in STOCK_WITH_DLLS:
        stock_names.update(p.name for p in (settings.MODULES_DIR / module / "bin").glob("*/*.dll"))
    removed = 0
    for dll in settings.SHARED_BIN.glob("*.dll"):
        if dll.name not in original and dll.name not in stock_names:
            dll.unlink()
            removed += 1
    note(f"shared-bin: removed {removed} DLL(s) that were not part of the server download")


def add_stock_module_dlls():
    for name in STOCK_WITH_DLLS:
        module = settings.MODULES_DIR / name
        source = next((module / f for f in CLIENT_BIN if (module / f).is_dir()), None)
        client = manifest.client_bin_folder(module)
        if source is None:
            continue
        for dll in sorted(source.glob("*.dll")):
            if client and source != client and not (client / dll.name).exists():
                continue
            if dll.name in COOP_PINNED or dll.name in HEADLESS_UNSAFE:
                continue
            target = settings.SHARED_BIN / dll.name
            if not target.exists():
                shutil.copyfile(dll, target)
                note(f"shared-bin: {dll.name} <- {name}")
            elif target.read_bytes() != dll.read_bytes():
                note(f"shared-bin: WARNING {dll.name} from {name} differs from the copy already there; kept the existing one")


def publish_coop_harmony():
    coop_copy = settings.MODULES_DIR / "Coop" / "bin" / "Win64_Shipping_Server" / "0Harmony.dll"
    target = settings.SHARED_BIN / "0Harmony.dll"
    if coop_copy.is_file() and settings.SHARED_BIN.is_dir() and (
            not target.is_file() or target.read_bytes() != coop_copy.read_bytes()):
        shutil.copyfile(coop_copy, target)
        note("shared-bin: Coop's 0Harmony.dll published as the single Harmony runtime")


def install_stubs():
    stubs = settings.ASSETS_DIR / "stubs"
    replaced = 0
    for stub in sorted(stubs.glob("*.dll")):
        for existing in settings.ENGINE_DIR.rglob(stub.name):
            shutil.copyfile(stub, existing)
            replaced += 1
        target = settings.SHARED_BIN / stub.name
        if settings.SHARED_BIN.is_dir() and not target.exists():
            shutil.copyfile(stub, target)
    note(f"shared-bin: {replaced} crash-report renderer(s) replaced by stand-ins")


def install_client_view_files():
    folder = settings.ADDONS_DIR / "client-view-dlls"
    placed = 0
    for dll in sorted(folder.glob("*.dll")) if folder.is_dir() else []:
        target = settings.SHARED_BIN / dll.name
        if target.exists() and target.read_bytes() != dll.read_bytes():
            note(f"client-view: {dll.name} is already provided by the server; left alone")
            continue
        shutil.copyfile(dll, target)
        placed += 1
    if placed:
        step(f"Added {placed} client View assembly(ies) from addons/client-view-dlls/.")
