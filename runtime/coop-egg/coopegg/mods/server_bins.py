import fnmatch
import shutil
from pathlib import Path

from .. import settings
from ..output.streams import note, step
from . import manifest
from .deps import unify

SERVER_FOLDER = "bin/Win64_Shipping_Server"
NEVER_COPY = ("0Harmony.dll", "Mono.Cecil*.dll", "MonoMod*.dll", "cimgui.dll", "glfw3.dll")
MCM_UI_FILES = ("Bannerlord.MBOptionScreen.v*.dll", "MCM.UI.Adapter.MCMv5.dll")


def _copy_submodule_dlls(module, server_dir):
    provided = 0
    client_folders = [module / f for f in manifest.CLIENT_BIN_FOLDERS]
    for dll in manifest.dll_names(module / "SubModule.xml"):
        if (server_dir / dll).is_file():
            continue
        source = next((f / dll for f in client_folders if (f / dll).is_file()), None)
        if source is None:
            step(f"WARNING: {module.name}: {dll} is not in any bin folder; the engine will skip this part of the mod.")
            continue
        server_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, server_dir / dll)
        note(f"server-bin: {module.name}: {dll} <- {source.parent.name}")
        provided += 1
    return provided


def _copy_dependencies(client_dir, server_dir):
    for source in sorted(client_dir.iterdir()):
        target = server_dir / source.name
        if target.exists():
            continue
        if source.is_file() and source.suffix.lower() == ".dll":
            if not any(fnmatch.fnmatchcase(source.name, pattern) for pattern in NEVER_COPY):
                shutil.copyfile(source, target)
        elif source.is_file() and source.suffix.lower() not in (".pdb", ".so"):
            shutil.copyfile(source, target)
        elif source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("*.dll", "*.pdb", "*.so"))


def _set_aside_client_animations(module):
    data = module / "ModuleData"
    if not data.is_dir():
        return
    for pattern in ("*action_sets*.xml", "*action_types*.xml"):
        for path in data.glob(pattern):
            path.rename(str(path) + ".disabled-for-server")
            note(f"server-bin: {module.name}: {path.name} set aside (client-only animations)")


def _drop_mcm_screens(module, server_dir):
    if module.name != "Bannerlord.MBOptionScreen":
        return
    for pattern in MCM_UI_FILES:
        for path in server_dir.glob(pattern):
            path.unlink()


def _engine_dirs():
    runtime = list((settings.ENGINE_DIR / "dotnet" / "shared" / "Microsoft.NETCore.App").glob("*/"))
    stock = [settings.MODULES_DIR / m / SERVER_FOLDER
             for m in ("Native", "SandBox", "SandBoxCore", "Sandbox", "DedicatedServer.Windows")]
    return runtime + stock


def prepare_all():
    coop_bin = settings.MODULES_DIR / "Coop" / SERVER_FOLDER
    engine_dirs = _engine_dirs()
    deps_json = settings.SHARED_BIN / "TaleWorlds.Starter.DotNetCore.deps.json"
    windows_desktop = settings.SHARED_BIN / "Microsoft.WindowsDesktop.App"
    stand_ins = settings.ASSETS_DIR / "stubs" / "standins"
    message_box_stubs = settings.ASSETS_DIR / "stubs" / "module-local"
    provided = 0

    for module in manifest.mod_modules():
        server_dir = module / SERVER_FOLDER
        client_dir = manifest.client_bin_folder(module)
        provided += _copy_submodule_dlls(module, server_dir)

        if server_dir.is_dir():
            if client_dir:
                _copy_dependencies(client_dir, server_dir)
            _drop_mcm_screens(module, server_dir)
        _set_aside_client_animations(module)

        if server_dir.is_dir() and coop_bin.is_dir():
            unify.unify(str(server_dir), coop_bin, module.name, engine_dirs, deps_json,
                        [windows_desktop], stand_ins, str(settings.SHARED_BIN))

        if server_dir.is_dir() and client_dir and message_box_stubs.is_dir():
            for stub in message_box_stubs.glob("*.dll"):
                target = server_dir / stub.name
                if not target.is_file() or target.read_bytes() != stub.read_bytes():
                    shutil.copyfile(stub, target)
                    note(f"server-bin: {module.name}: {stub.name} <- headless stand-in")
    if provided:
        step(f"Made {provided} mod DLL(s) loadable by the server engine.")
