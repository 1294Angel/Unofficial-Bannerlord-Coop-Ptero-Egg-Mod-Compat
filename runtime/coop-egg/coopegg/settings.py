import os
from pathlib import Path

ROOT = Path(os.environ.get("EGG_ROOT", "/home/container"))

APP_ID = "261550"
COOP_ITEM = "3770450698"

SERVER_DIR = ROOT / "DedicatedServer"
LAUNCHER = SERVER_DIR / "BannerlordCoopServer.exe"
ENGINE_DIR = SERVER_DIR / "engine"
MODULES_DIR = ENGINE_DIR / "Modules"
SHARED_BIN = ENGINE_DIR / "bin" / "Win64_Shipping_Server"
MODULE_LIST = SERVER_DIR / "modded-server-modules.txt"

CODE_DIR = ROOT / "coop-egg"
ASSETS_DIR = CODE_DIR / "coopegg" / "assets"
STATE_DIR = ROOT / ".state"
ORIGINAL_SHARED_BIN = STATE_DIR / "original-shared-bin.txt"
LOGS_DIR = ROOT / "logs"
ADDONS_DIR = ROOT / "addons"
MOD_LIST_FILE = ROOT / "modlist.txt"

STEAMCMD_SH = ROOT / "steamcmd" / "steamcmd.sh"
STEAM_CONTENT = ROOT / "steam-content"
WINEPREFIX = Path(os.environ.get("WINEPREFIX", ROOT / ".wine"))

STOCK_MODULES = {
    "Native", "SandBox", "SandBoxCore", "Sandbox", "Coop",
    "DedicatedServer.Windows", "StoryMode", "CustomBattle", "BirthAndDeath",
}
CLIENT_GAME_MODES = ("CustomBattle", "StoryMode", "BirthAndDeath")


def wine_documents():
    users = WINEPREFIX / "drive_c" / "users"
    if users.is_dir():
        for user in sorted(users.iterdir()):
            if user.name != "Public":
                return user / "Documents" / "Mount and Blade II Bannerlord"
    return users / "container" / "Documents" / "Mount and Blade II Bannerlord"


def coop_data_dir():
    return wine_documents() / "CoopData" / "DedicatedServer"


def _flag(name):
    return os.environ.get(name, "0").strip().lower() in ("1", "true", "yes", "on")


STEAM_ACCOUNT = os.environ.pop("STEAM_ACCOUNT", "").strip()
STEAM_PASSWORD = os.environ.pop("STEAM_ACCOUNT_PASSWORD", "")

ACCEPT_EULA = _flag("ACCEPT_EULA")
SERVER_PASSWORD = os.environ.get("SERVER_PASSWORD", "")
SAVE_NAME = os.environ.get("SAVE_NAME", "").strip() or "saveauto1"
SERVER_PORT = os.environ.get("SERVER_PORT", "4200").strip() or "4200"
WORKSHOP_MODS = [m.strip() for m in os.environ.get("WORKSHOP_MODS", "").split(",") if m.strip()]

HIDDEN_ADDRESSES = [
    os.environ.get(name, "").strip() for name in ("SERVER_IP", "INTERNAL_IP")
]
