from . import settings
from .output.streams import note
from .steam import workshop

PAGE = "https://steamcommunity.com/sharedfiles/filedetails/?id={}"


def write():
    ids = settings.WORKSHOP_MODS
    if not ids:
        settings.MOD_LIST_FILE.unlink(missing_ok=True)
        return
    titles = {item_id: d.get("title", "") for item_id, d in workshop.remote_details(ids).items()}
    lines = ["Mods this server runs. Players install the same ones, in this order:", ""]
    for number, item_id in enumerate(ids, 1):
        lines += [f"{number}. {titles.get(item_id) or 'Workshop item ' + item_id}", f"   {PAGE.format(item_id)}"]
    lines += ["", "Subscribe to each item on Steam, then start the game.", ""]
    settings.MOD_LIST_FILE.write_text("\n".join(lines), encoding="utf-8")
    note(f"modlist: wrote {settings.MOD_LIST_FILE.name} ({len(ids)} mods)")
