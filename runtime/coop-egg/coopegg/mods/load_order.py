from .. import settings
from ..output.streams import note

FRAMEWORKS = ["Bannerlord.Harmony", "Bannerlord.ButterLib", "Bannerlord.UIExtenderEx", "Bannerlord.MBOptionScreen"]
BASE = ["Native", "DedicatedServer.Windows", "SandBoxCore", "Sandbox", "Coop"]
DIAG = "HeadlessDiag"


def write(workshop_modules, local_modules):
    mods = list(dict.fromkeys(workshop_modules + local_modules))
    frameworks = [m for m in FRAMEWORKS if m in mods]
    others = [m for m in mods if m not in FRAMEWORKS and m not in BASE and m != DIAG]
    order = frameworks + BASE + [DIAG] + others
    settings.MODULE_LIST.write_text("\n".join(order) + "\n")
    note("mods: load order " + " -> ".join(order))
    return order


def remove():
    settings.MODULE_LIST.unlink(missing_ok=True)
