import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .. import settings
from ..output.streams import note, step
from . import steamcmd

DETAILS_API = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
ATTEMPTS = 3


@dataclass
class Item:
    id: str
    path: Path
    version: Optional[str]


def remote_details(item_ids):
    form = {"itemcount": len(item_ids)}
    for number, item_id in enumerate(item_ids):
        form[f"publishedfileids[{number}]"] = item_id
    try:
        with urllib.request.urlopen(DETAILS_API, urllib.parse.urlencode(form).encode(), timeout=20) as reply:
            details = json.load(reply)["response"]["publishedfiledetails"]
    except Exception as error:
        note(f"workshop: Steam details lookup failed ({error.__class__.__name__})")
        return {}
    return {d["publishedfileid"]: d for d in details if d.get("result", 1) == 1}


def remote_version(item_id):
    details = remote_details([item_id]).get(item_id, {})
    return str(details["time_updated"]) if details.get("time_updated") else None


def cached_path(item_id):
    path = settings.STEAM_CONTENT / "steamapps" / "workshop" / "content" / settings.APP_ID / item_id
    return path if path.is_dir() and any(path.iterdir()) else None


def recorded_version(name):
    try:
        return (settings.STATE_DIR / name).read_text().strip() or None
    except OSError:
        return None


def record_version(name, version):
    settings.STATE_DIR.mkdir(parents=True, exist_ok=True)
    (settings.STATE_DIR / name).write_text(str(version))


def _download(item_ids):
    commands = []
    for item_id in item_ids:
        commands += ["+workshop_download_item", settings.APP_ID, item_id]
    output = steamcmd.run(*commands).text
    return {i for i in item_ids if f"Downloaded item {i} " in output and cached_path(i)}


def fetch_all(item_ids):
    remote = {i: str(d["time_updated"]) for i, d in remote_details(item_ids).items() if d.get("time_updated")}
    items, todo = {}, []
    for item_id in item_ids:
        cached = cached_path(item_id)
        if cached and remote.get(item_id) and remote[item_id] == recorded_version(f"download-{item_id}"):
            note(f"workshop {item_id}: up to date ({remote[item_id]})")
            items[item_id] = Item(item_id, cached, remote[item_id])
        else:
            todo.append(item_id)

    for attempt in range(1, ATTEMPTS + 1):
        if not todo:
            break
        step(f"Downloading {len(todo)} Workshop item(s): {', '.join(todo)}")
        done = _download(todo)
        for item_id in todo:
            if item_id in done:
                if remote.get(item_id):
                    record_version(f"download-{item_id}", remote[item_id])
                items[item_id] = Item(item_id, cached_path(item_id), remote.get(item_id))
        todo = [i for i in todo if i not in done]
        if todo:
            step(f"Attempt {attempt} of {ATTEMPTS}: {len(todo)} item(s) did not download: {', '.join(todo)}")

    for item_id in todo:
        older = cached_path(item_id)
        if older:
            step(f"Workshop item {item_id}: using the version downloaded earlier.")
            items[item_id] = Item(item_id, older, recorded_version(f"download-{item_id}"))
        else:
            items[item_id] = None
    return items


def fetch(item_id):
    return fetch_all([item_id])[item_id]
