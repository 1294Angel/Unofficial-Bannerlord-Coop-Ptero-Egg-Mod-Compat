from ... import settings
from ...output.streams import note, step
from .. import manifest
from ..load_order import FRAMEWORKS


def apply():
    provided = set()
    for name in FRAMEWORKS:
        path = settings.MODULES_DIR / name / "SubModule.xml"
        if path.is_file():
            provided.update(dll.lower() for dll in manifest.dll_names(path))

    removed = 0
    for module in manifest.mod_modules():
        if module.name in FRAMEWORKS or module.name == "HeadlessDiag":
            continue
        path = module / "SubModule.xml"
        bom = manifest.has_bom(path)
        text = manifest.read(path)
        gone = []

        def drop(match):
            dll = manifest.DLL_NAME.search(match.group(0))
            if dll and dll.group(1).lower() in provided:
                gone.append(dll.group(1))
                return ""
            return match.group(0)

        new_text = manifest.SUBMODULE_BLOCK.sub(drop, text)
        if gone:
            manifest.keep_original(path)
            manifest.write(path, new_text, bom)
            removed += len(gone)
            note(f"bundled-frameworks: {module.name}: removed {', '.join(sorted(set(gone)))}")
    if removed:
        step(f"Removed {removed} duplicate framework submodule(s) bundled inside mods.")
