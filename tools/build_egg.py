#!/usr/bin/env python3
import base64
import io
import json
import re
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 65000


def pack_runtime():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", compresslevel=9) as tar:
        for path in sorted((ROOT / "runtime" / "coop-egg").rglob("*")):
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            info = tar.gettarinfo(str(path), arcname=str(path.relative_to(ROOT / "runtime" / "coop-egg")))
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            info.mode = 0o755 if path.is_dir() else 0o644
            tar.addfile(info, path.open("rb") if path.is_file() else None)
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return "\n".join(re.findall(".{1,3000}", encoded))


def main():
    definition = json.loads((ROOT / "egg-source" / "definition.json").read_text(encoding="utf-8"))
    script = (ROOT / "egg-source" / "install.sh").read_text(encoding="utf-8").replace("\r\n", "\n")
    script = script.replace("@@PAYLOAD@@", pack_runtime())
    if len(script.encode()) > LIMIT:
        sys.exit(f"install script is {len(script.encode())} bytes; the Panel allows about {LIMIT}")

    variables = []
    for variable in definition["variables"]:
        variable = dict(variable)
        variable["field_type"] = "text"
        variables.append(variable)

    egg = {
        "_comment": "Bannerlord Coop (unofficial) egg. Built by tools/build_egg.py; edit egg-source/ and runtime/, not this file.",
        "meta": {"version": "PTDL_v2", "update_url": None},
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "name": definition["name"],
        "author": definition["author"],
        "description": definition["description"],
        "features": None,
        "docker_images": definition["docker_images"],
        "file_denylist": [],
        "startup": definition["startup"],
        "config": {
            "files": "{}",
            "startup": json.dumps({"done": definition["done"]}),
            "logs": "{}",
            "stop": definition["stop"],
        },
        "scripts": {
            "installation": {
                "script": script,
                "container": definition["install_container"],
                "entrypoint": "bash",
            }
        },
        "variables": variables,
    }
    target = ROOT / "egg-bannerlord-coop.json"
    target.write_text(json.dumps(egg, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {target.name}: install script {len(script.encode())} bytes of {LIMIT}")


if __name__ == "__main__":
    main()
