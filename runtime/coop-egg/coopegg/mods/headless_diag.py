import shutil

from .. import settings
from ..output.streams import note


def install():
    source = settings.ASSETS_DIR / "headless-diag" / "HeadlessDiag"
    destination = settings.MODULES_DIR / "HeadlessDiag"
    shutil.rmtree(destination, ignore_errors=True)
    shutil.copytree(source, destination)
    (settings.LOGS_DIR / "headless-diag.log").unlink(missing_ok=True)
    note("mods: HeadlessDiag installed")
