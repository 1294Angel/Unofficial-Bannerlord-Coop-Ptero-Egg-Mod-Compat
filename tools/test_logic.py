import os
import sys
import tempfile
import unittest
from pathlib import Path

TEMP = tempfile.mkdtemp()
os.environ.update({"EGG_ROOT": TEMP, "SERVER_PORT": "4310", "SAVE_NAME": "mysave", "SERVER_PASSWORD": 'pa"ss'})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runtime" / "coop-egg"))

from coopegg import settings
from coopegg.mods import load_order, manifest
from coopegg.mods.fixes import bundled_frameworks, client_only, combat_params, soft_deps
from coopegg.output.console_filter import QuietConsole
from coopegg.server import config, mod_config


settings.SERVER_DIR.mkdir(parents=True, exist_ok=True)


def make_module(name, xml_body, files=None):
    folder = settings.MODULES_DIR / name
    (folder / "ModuleData").mkdir(parents=True, exist_ok=True)
    (folder / "SubModule.xml").write_text(xml_body, encoding="utf-8")
    for relative, text in (files or {}).items():
        (folder / relative).parent.mkdir(parents=True, exist_ok=True)
        (folder / relative).write_text(text, encoding="utf-8")
    return folder


SUBMODULE = """<Module>
  <Name value="{0}"/><Id value="{0}"/>
  <DependedModules><DependedModule Id="Native"/>{1}</DependedModules>
  <SubModules>
    <SubModule><Name value="Main"/><DLLName value="{2}"/><Tags/></SubModule>
  </SubModules>
</Module>
"""


class ServerConfig(unittest.TestCase):
    def test_first_start_creates_a_working_file(self):
        (settings.coop_data_dir() / "server-config.json").unlink(missing_ok=True)
        config.apply()
        text = (settings.coop_data_dir() / "server-config.json").read_text()
        for expected in ('"saveName": "mysave"', '"port": 4310', '"steam": false', '"password": "pa\\"ss"'):
            self.assertIn(expected, text)

    def test_existing_file_keeps_comments_and_changes_only_the_settings(self):
        path = settings.coop_data_dir() / "server-config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{\n  // keep me\n  "saveName": "old",\n  "port": 4200,\n  "steam": true,\n'
                        '  "password": "",\n  "autosaveMinutes": 9,\n}\n')
        config.apply()
        text = path.read_text()
        self.assertIn("// keep me", text)
        self.assertIn('"autosaveMinutes": 5', text)
        self.assertIn('"saveName": "mysave"', text)
        self.assertIn('"port": 4310', text)
        self.assertIn('"steam": false', text)

    def test_commented_out_key_is_not_mistaken_for_a_live_one(self):
        path = settings.coop_data_dir() / "server-config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{\n  // "port": 1,\n  "port": 2,\n}\n')
        config.apply()
        text = path.read_text()
        self.assertIn('// "port": 1,', text)
        self.assertIn('"port": 4310', text)


class ModConfig(unittest.TestCase):
    def setUp(self):
        self.path = settings.coop_data_dir().parent / "mod-config.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.unlink(missing_ok=True)
        for variable, *_rest in mod_config.OPTIONS:
            os.environ.pop(variable, None)

    def tearDown(self):
        for variable, *_rest in mod_config.OPTIONS:
            os.environ.pop(variable, None)

    def test_nothing_set_touches_nothing(self):
        mod_config.apply()
        self.assertFalse(self.path.exists())

    def test_panel_defaults_do_not_create_a_file_but_do_overwrite_an_existing_one(self):
        for variable, _section, _key, _kind, default in mod_config.OPTIONS:
            os.environ[variable] = default
        mod_config.apply()
        self.assertFalse(self.path.exists())
        self.path.write_text('{\n  "modOptions": {\n    "wandererLimit": 99,\n  }\n}\n')
        mod_config.apply()
        self.assertIn('"wandererLimit": 32', self.path.read_text())

    def test_changes_live_keys_and_adds_commented_out_ones(self):
        self.path.write_text('{\n  "difficulty": {\n    // "battleDeath": "Easy",\n    "birthAndDeath": true,\n  },\n'
                             '  "modOptions": {\n    "wandererLimit": 32,\n    "lordDefectionRetries": "Vanilla",\n  }\n}\n')
        os.environ.update({"COOP_BIRTH_AND_DEATH": "0", "COOP_BATTLE_DEATH": "realistic", "COOP_WANDERER_LIMIT": "50",
                           "COOP_LORD_DEFECTION_RETRIES": "AlwaysRetry", "COOP_LOOTERS_MULTIPLIER": "1.5"})
        mod_config.apply()
        text = self.path.read_text()
        self.assertIn('"birthAndDeath": false', text)
        self.assertIn('// "battleDeath": "Easy",', text)
        self.assertIn('    "battleDeath": "Realistic",', text)
        self.assertIn('"wandererLimit": 50', text)
        self.assertIn('"lordDefectionRetries": "AlwaysRetry"', text)
        self.assertIn('"maximumLootersMultiplier": 1.5', text)

    def test_invalid_values_are_skipped_and_missing_file_is_created(self):
        os.environ.update({"COOP_WANDERER_LIMIT": "lots", "COOP_AUTO_PAUSE": "false", "COOP_BATTLE_DEATH": "Hard"})
        mod_config.apply()
        text = self.path.read_text()
        self.assertIn('"autoPauseEnabled": false', text)
        self.assertNotIn("wandererLimit", text)
        self.assertNotIn("battleDeath", text)

    def test_every_option_has_a_panel_variable(self):
        import json
        definition = json.loads((Path(__file__).resolve().parent.parent / "egg-source" / "definition.json").read_text(encoding="utf-8"))
        panel = {v["env_variable"] for v in definition["variables"]}
        self.assertEqual({o[0] for o in mod_config.OPTIONS} - panel, set())


class LoadOrder(unittest.TestCase):
    def test_frameworks_first_then_stock_then_diag_then_mods(self):
        order = load_order.write(["Zed", "Bannerlord.ButterLib", "Bannerlord.Harmony"], ["LocalMod"])
        self.assertEqual(order, ["Bannerlord.Harmony", "Bannerlord.ButterLib", "Native", "DedicatedServer.Windows",
                                 "SandBoxCore", "Sandbox", "Coop", "HeadlessDiag", "Zed", "LocalMod"])
        self.assertEqual(settings.MODULE_LIST.read_text().split(), order)


class ModFixes(unittest.TestCase):
    def test_client_only_submodule_gets_the_server_skip_tag(self):
        module = make_module("TagMe", SUBMODULE.format("TagMe", "", "RF_BattleAI.dll"))
        client_only.apply()
        text = (module / "SubModule.xml").read_text()
        self.assertIn('DedicatedServerType', text)
        self.assertTrue((module / "SubModule.xml.orig").exists())

    def test_game_mode_dependencies_are_dropped(self):
        module = make_module("NeedsStory", SUBMODULE.format(
            "NeedsStory", '<DependedModule Id="StoryMode"/><DependedModule Id="CustomBattle"/>', "X.dll"))
        soft_deps.apply()
        text = (module / "SubModule.xml").read_text()
        self.assertNotIn("StoryMode", text)
        self.assertNotIn("CustomBattle", text)
        self.assertIn('Id="Native"', text)

    def test_bundled_framework_submodule_is_removed(self):
        make_module("Bannerlord.MBOptionScreen", SUBMODULE.format("Bannerlord.MBOptionScreen", "", "MCMv5.dll"))
        module = make_module("Bundler", SUBMODULE.format("Bundler", "", "MCMv5.dll"))
        bundled_frameworks.apply()
        self.assertNotIn("MCMv5.dll", (module / "SubModule.xml").read_text())

    def test_combat_parameter_damage_start_is_raised(self):
        module = make_module("Combat", SUBMODULE.format("Combat", "", "C.dll"), {
            "ModuleData/params.xml": '<combat_parameter id="a" collision_check_starting_percent="0.5" '
                                     'collision_damage_starting_percent="0.1"/>'})
        combat_params.apply()
        self.assertIn('collision_damage_starting_percent="0.5"', (module / "ModuleData" / "params.xml").read_text())

    def test_manifest_helpers(self):
        module = make_module("Reader", SUBMODULE.format("Reader", "", "R.dll"))
        self.assertEqual(manifest.module_id(module / "SubModule.xml"), "Reader")
        self.assertEqual(manifest.dll_names(module / "SubModule.xml"), ["R.dll"])


class QuietConsoleTests(unittest.TestCase):
    def test_everything_is_shown_until_serving_then_chatter_is_hidden(self):
        console = QuietConsole("4210", "logs/x.log")
        self.assertEqual(console.feed("[Coop] loading"), ["[Coop] loading"])
        shown = console.feed("[DedicatedServer] SERVING - up")
        self.assertTrue(any("SERVER UP on UDP port 4210" in line for line in shown))
        self.assertEqual(console.feed("[DedicatedServer] pulse: t=1"), [])
        self.assertEqual(console.feed('@DS@{"ev":"players","list":[{"name":"Ann"}]}'), ["[players] 1 online: Ann"])
        self.assertEqual(console.feed("[12:00:00.123] boring engine line"), [])
        self.assertEqual(console.feed("[12:00:00.123] something failed"), ["[12:00:00.123] something failed"])


if __name__ == "__main__":
    unittest.main()
