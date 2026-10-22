import sys

from . import mod_list, settings
from .mods import prepare
from .output import scrub, streams
from .server import config, launch, mod_config, update, wine


def main():
    streams.start_startup_log()
    streams.step("Bannerlord Coop server starting.")
    streams.note("Steam login: " + ("set" if settings.STEAM_ACCOUNT else "NOT set"))

    scrub.scrub()
    update.ensure_installed()

    if not settings.ACCEPT_EULA:
        streams.fail(update.eula_message())

    prepare.create_addon_folders()
    wine.ensure_prefix()
    config.apply()
    mod_config.apply()
    modded = prepare.run()
    mod_list.write()

    sys.exit(launch.run(modded))
