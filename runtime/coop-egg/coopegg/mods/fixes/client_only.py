import re

from ... import settings
from ...output.streams import note, step
from .. import manifest

CLIENT_ONLY_DLLS = {
    "BattleArtilleryReworked.dll", "RF_BattleAI.dll", "EOE.CustomBattlePatch.dll",
    "Bannerlord.ModuleLoader.Bannerlord.EncyclopediaExtender.dll", "BetterTroopHUD.dll",
    "TroopSort.dll", "ExceptionSentry.Core.dll", "RealBattleSize.dll", "ChooseYourTroops.dll",
}
TAG = '<Tag key="DedicatedServerType" value="none" />'
LEAVE_ALONE = {"Native", "SandBoxCore", "Sandbox", "Coop", "DedicatedServer.Windows"}


def _tag(block):
    if re.search(r'key\s*=\s*"DedicatedServerType"', block, re.I):
        return None
    for pattern, replacement in (
        (r"<Tags\s*/>", f"<Tags>\n        {TAG}\n      </Tags>"),
        (r"(<Tags\s*>)", r"\1\n        " + TAG),
        (r"(</SubModule>)", f"  <Tags>\n        {TAG}\n      </Tags>\n    \\1"),
    ):
        new, count = re.subn(pattern, replacement, block, count=1, flags=re.I)
        if count:
            return new
    return None


def apply():
    modules_tagged = 0
    for module in manifest.mod_modules():
        if module.name in LEAVE_ALONE:
            continue
        path = module / "SubModule.xml"
        text = manifest.read(path)
        tagged = []

        def tag_block(match):
            block = match.group(0)
            dll = manifest.DLL_NAME.search(block)
            if not dll or dll.group(1) not in CLIENT_ONLY_DLLS:
                return block
            new = _tag(block)
            if new is None:
                return block
            tagged.append(dll.group(1))
            return new

        new_text = manifest.SUBMODULE_BLOCK.sub(tag_block, text)
        if tagged:
            manifest.keep_original(path)
            manifest.write(path, new_text)
            modules_tagged += 1
            note(f"client-only: {module.name} -> skipped on the server: {', '.join(tagged)}")

        for block in manifest.SUBMODULE_BLOCK.findall(new_text):
            dll = manifest.DLL_NAME.search(block)
            if dll:
                skipped = re.search(r'key\s*=\s*"DedicatedServerType"', block, re.I)
                note(f"client-only: {module.name}: {'SKIP' if skipped else 'LOAD'} {dll.group(1)}")
    if modules_tagged:
        step(f"Set {modules_tagged} mod(s) to skip their client-only parts on the server.")
