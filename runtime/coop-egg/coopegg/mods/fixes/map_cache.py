import shutil

from ... import settings
from ...output.streams import note, step
from .. import manifest

CACHE_NAME = "settlements_distance_cache_Default.bin"


def _same(a, b):
    return a.read_bytes() == b.read_bytes()


def apply():
    sandbox_cache = settings.MODULES_DIR / "SandBox" / "ModuleData" / "DistanceCaches" / CACHE_NAME
    stock_copy = sandbox_cache.with_name(CACHE_NAME + ".stock")
    if not sandbox_cache.is_file():
        return

    for module in manifest.mod_modules():
        mod_cache = module / "ModuleData" / "DistanceCaches" / CACHE_NAME
        if mod_cache.is_file():
            if _same(mod_cache, sandbox_cache):
                return
            if not stock_copy.exists():
                shutil.copyfile(sandbox_cache, stock_copy)
            shutil.copyfile(mod_cache, sandbox_cache)
            step(f"Using {module.name}'s settlement distance cache (it replaces the map).")
            return

    if stock_copy.is_file() and not _same(stock_copy, sandbox_cache):
        shutil.copyfile(stock_copy, sandbox_cache)
        note("map-cache: restored SandBox's own distance cache (no map mod installed)")
