import os
import subprocess
import time
from pathlib import Path

from .. import settings
from ..output.streams import note, step


def environment():
    env = dict(os.environ)
    env.update({
        "WINEPREFIX": str(settings.WINEPREFIX),
        "WINEDEBUG": "-all",
        "DOTNET_EnableWriteXorExecute": "0",
        "HEADLESS_DIAG_LOG": "Z:" + str(settings.LOGS_DIR / "headless-diag.log").replace("/", "\\"),
    })
    if settings.ACCEPT_EULA:
        env["DS_ACCEPT_EULA"] = "true"
    return env


def ensure_display():
    display = os.environ.get("DISPLAY", "")
    if display and Path("/tmp/.X11-unix", "X" + display.lstrip(":").split(".")[0]).exists():
        return
    step("Starting a virtual display...")
    subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1024x768x16"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    os.environ["DISPLAY"] = ":99"
    time.sleep(2)


def ensure_prefix():
    if (settings.WINEPREFIX / "system.reg").exists():
        return
    step("Setting up Wine for the first time...")
    env = environment()
    subprocess.run(["wineboot", "--init"], env=env, check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["wineserver", "-w"], env=env, check=False)
    note("wine: prefix created")
