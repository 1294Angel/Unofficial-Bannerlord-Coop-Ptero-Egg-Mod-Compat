from .. import settings
from ..output.streams import step
from . import headless_diag, install, load_order, server_bins, shared_bin
from .fixes import bundled_frameworks, client_only, combat_params, map_cache, soft_deps

ADDONS_READMES = {
    "local-mods": "Put a mod that is not on the Steam Workshop here, in a folder named after its module Id\n"
                  "(the Id in its SubModule.xml), so that addons/local-mods/<ModuleId>/SubModule.xml exists.\n"
                  "It is installed automatically at the next start.\n",
    "client-view-dlls": "Only needed if a mod fails with a missing *.View or *.ViewModelCollection assembly.\n"
                        "Copy those DLLs from your own Bannerlord install into this folder (the list is in the\n"
                        "egg's README). They are added automatically at the next start.\n",
}


def create_addon_folders():
    for name, text in ADDONS_READMES.items():
        folder = settings.ADDONS_DIR / name
        folder.mkdir(parents=True, exist_ok=True)
        readme = folder / "README.txt"
        if not readme.exists():
            readme.write_text(text)


def run():
    wanted = settings.WORKSHOP_MODS
    local = install.local_mod_ids()
    if not wanted and not local:
        load_order.remove()
        return False

    step(f"Preparing {len(wanted) + len(local)} mod(s) for the server...")
    workshop_modules = install.workshop_mods(wanted)
    headless_diag.install()
    local_modules = install.local_mods()
    load_order.write(workshop_modules, local_modules)

    client_only.apply()
    map_cache.apply()
    soft_deps.apply()
    bundled_frameworks.apply()
    combat_params.apply()

    shared_bin.clean()
    shared_bin.add_stock_module_dlls()
    server_bins.prepare_all()
    shared_bin.install_client_view_files()
    shared_bin.install_stubs()
    shared_bin.publish_coop_harmony()
    return True
