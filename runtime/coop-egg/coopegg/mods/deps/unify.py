import os
import re
import shutil

from ...output.streams import note
from .pe_metadata import assembly_version, read_metadata

FORWARDED = {"System.Configuration": "System.Configuration.ConfigurationManager"}
ENGINE_FOLDER_ASSEMBLIES = [
    "System.Configuration.ConfigurationManager", "System.Diagnostics.EventLog",
    "System.Security.Cryptography.ProtectedData", "System.Security.Permissions",
    "Microsoft.Win32.SystemEvents", "System.Windows.Extensions",
]


def _version_text(version):
    return ".".join(str(part) for part in version)


def _dll_names(*folders):
    names = set()
    for folder in folders:
        if os.path.isdir(folder):
            names.update(os.path.splitext(f)[0].lower() for f in os.listdir(folder) if f.lower().endswith(".dll"))
    return names


def _names_in_deps_json(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return {os.path.splitext(n)[0].lower() for n in re.findall(r'"([^"/\\]+\.dll)"', f.read())}
    except OSError:
        return set()


def prefer_coops_newer_copies(module_dir, coop_dir, label):
    replaced = conflicts = 0
    for name in sorted(os.listdir(module_dir)):
        theirs, ours = os.path.join(module_dir, name), os.path.join(coop_dir, name)
        if not name.lower().endswith(".dll") or not os.path.isfile(ours):
            continue
        theirs_version, ours_version = assembly_version(theirs), assembly_version(ours)
        if theirs_version is None or ours_version is None:
            continue
        if ours_version > theirs_version:
            shutil.copyfile(ours, theirs)
            note(f"deps: {label}: {name} {_version_text(theirs_version)} -> Coop's {_version_text(ours_version)}")
            replaced += 1
        elif ours_version < theirs_version:
            note(f"deps: {label}: WARNING {name} is {_version_text(theirs_version)} but Coop has the older "
                 f"{_version_text(ours_version)}; left as it is, whichever loads first wins")
            conflicts += 1
    return replaced, conflicts


def copy_missing_references(module_dir, sources, already_provided, label, shared_dir):
    known = {os.path.splitext(f)[0].lower() for f in os.listdir(module_dir) if f.lower().endswith(".dll")}
    known |= already_provided
    queue = [os.path.join(module_dir, f) for f in sorted(os.listdir(module_dir)) if f.lower().endswith(".dll")]
    copied, used_facade = [], False

    while queue:
        path = queue.pop()
        metadata = read_metadata(path)
        if not metadata:
            continue
        references = list(metadata[1])
        for facade, real in FORWARDED.items():
            if facade in references and real not in references:
                references.append(real)
                used_facade = True
        for name in references:
            if name.lower() in known or name.lower() == "0harmony":
                continue
            source = next((os.path.join(d, name + ".dll") for d in sources
                           if os.path.isfile(os.path.join(d, name + ".dll"))), None)
            if source is None:
                continue
            known.add(name.lower())
            target = os.path.join(module_dir, name + ".dll")
            shutil.copyfile(source, target)
            copied.append(name)
            note(f"deps: {label}: {name}.dll was missing (needed by {os.path.basename(path)}); copied")
            queue.append(target)

    if used_facade and shared_dir and os.path.isdir(shared_dir):
        for name in ENGINE_FOLDER_ASSEMBLIES:
            for folder in sources:
                source = os.path.join(folder, name + ".dll")
                if os.path.isfile(source):
                    target = os.path.join(shared_dir, name + ".dll")
                    if not os.path.exists(target):
                        shutil.copyfile(source, target)
                    break
    return copied


def refresh_standins(module_dir, standin_dir, label):
    if not os.path.isdir(standin_dir):
        return
    for name in os.listdir(standin_dir):
        target, source = os.path.join(module_dir, name), os.path.join(standin_dir, name)
        if name.lower().endswith(".dll") and os.path.isfile(target):
            with open(target, "rb") as a, open(source, "rb") as b:
                if a.read() != b.read():
                    shutil.copyfile(source, target)
                    note(f"deps: {label}: {name} replaced by the stand-in")


def unify(module_dir, coop_dir, label, engine_dirs, deps_json, extra_sources, standin_dir, shared_dir):
    replaced, conflicts = prefer_coops_newer_copies(module_dir, str(coop_dir), label)
    provided = _dll_names(*engine_dirs) | _names_in_deps_json(deps_json)
    sources = [str(coop_dir)] + [str(d) for d in extra_sources] + [str(standin_dir)]
    copied = copy_missing_references(module_dir, sources, provided, label, shared_dir)
    refresh_standins(module_dir, str(standin_dir), label)
    return replaced, conflicts, len(copied)
