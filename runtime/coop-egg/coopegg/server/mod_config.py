import json
import os
import re

from .. import settings
from ..output.streams import note

LEVELS = ("VeryEasy", "Easy", "Realistic")
BOOL = "bool"
INT = "int"
FLOAT = "float"

OPTIONS = (
    ("COOP_PLAYER_RECEIVED_DAMAGE", "difficulty", "playerReceivedDamage", LEVELS, "VeryEasy"),
    ("COOP_PLAYER_TROOPS_RECEIVED_DAMAGE", "difficulty", "playerTroopsReceivedDamage", LEVELS, "Easy"),
    ("COOP_COMBAT_AI_DIFFICULTY", "difficulty", "combatAIDifficulty", LEVELS, "Easy"),
    ("COOP_RECRUITMENT_DIFFICULTY", "difficulty", "recruitmentDifficulty", LEVELS, "Easy"),
    ("COOP_PLAYER_MAP_MOVEMENT_SPEED", "difficulty", "playerMapMovementSpeed", LEVELS, "VeryEasy"),
    ("COOP_STEALTH_DIFFICULTY", "difficulty", "stealthAndDisguiseDifficulty", LEVELS, "Easy"),
    ("COOP_PERSUASION_SUCCESS_CHANCE", "difficulty", "persuasionSuccessChance", LEVELS, "VeryEasy"),
    ("COOP_CLAN_MEMBER_DEATH_CHANCE", "difficulty", "clanMemberDeathChance", LEVELS, "Easy"),
    ("COOP_BATTLE_DEATH", "difficulty", "battleDeath", LEVELS, "Easy"),
    ("COOP_BIRTH_AND_DEATH", "difficulty", "birthAndDeath", BOOL, "0"),
    ("COOP_AUTO_ALLOCATE_PERKS", "difficulty", "autoAllocateClanMemberPerks", BOOL, "0"),
    ("COOP_FAST_FORWARD", "modOptions", "fastForwardEnabled", BOOL, "1"),
    ("COOP_AUTO_PAUSE", "modOptions", "autoPauseEnabled", BOOL, "1"),
    ("COOP_CLIENT_CHEATS", "modOptions", "clientsCanUseCheats", BOOL, "0"),
    ("COOP_RESOURCES_IN_SETTLEMENTS", "modOptions", "goldFoodInfluenceChangeInSettlements", BOOL, "0"),
    ("COOP_RESOURCES_IN_BATTLES", "modOptions", "goldFoodInfluenceChangeInBattles", ("Disabled", "OneDayMax", "Enabled"), "OneDayMax"),
    ("COOP_RESOURCES_OFFLINE", "modOptions", "goldFoodInfluenceChangeForDisconnectedPlayers", BOOL, "0"),
    ("COOP_AI_JOIN_WINDOW_HOURS", "modOptions", "playerBattleAiJoinWindowHours", INT, "24"),
    ("COOP_SPEED_LIMIT_IN_BATTLE", "modOptions", "speedLimitWhilePlayersInBattle", BOOL, "1"),
    ("COOP_WANDERER_LIMIT", "modOptions", "wandererLimit", INT, "32"),
    ("COOP_WANDERER_LIMIT_SCALES", "modOptions", "wandererLimitScalesWithPlayers", BOOL, "0"),
    ("COOP_KINGDOM_CLAN_TIER", "modOptions", "playerKingdomClanTierRequired", INT, "4"),
    ("COOP_SMITHING_RECOVERY_OUTSIDE", "modOptions", "smithingStaminaRecoveryOutsideSettlements", BOOL, "0"),
    ("COOP_SMITHING_RECOVERY_MULTIPLIER", "modOptions", "smithingStaminaRecoveryMultiplier", FLOAT, "0.1"),
    ("COOP_LOOTERS_MULTIPLIER", "modOptions", "maximumLootersMultiplier", FLOAT, "1.0"),
    ("COOP_LORD_DEFECTION_RETRIES", "modOptions", "lordDefectionRetries", ("Vanilla", "NeverExpire", "AlwaysRetry"), "Vanilla"),
    ("COOP_HERO_EXECUTIONS", "modOptions", "enableHeroExecutions", BOOL, "1"),
    ("COOP_CLAN_MEMBER_EXECUTIONS", "modOptions", "enablePlayerClanMemberExecutions", BOOL, "0"),
)

TRUE_WORDS = ("1", "true", "yes", "on")
FALSE_WORDS = ("0", "false", "no", "off")
LIVE_VALUE = r'"(?:[^"\\]|\\.)*"|true|false|-?\d+(?:\.\d+)?'


def _format(kind, raw, label):
    word = raw.strip()
    if kind == BOOL:
        if word.lower() in TRUE_WORDS:
            return "true"
        if word.lower() in FALSE_WORDS:
            return "false"
    elif kind == INT:
        if re.fullmatch(r"\d+", word):
            return word
    elif kind == FLOAT:
        try:
            if float(word) >= 0:
                return json.dumps(float(word))
        except ValueError:
            pass
    else:
        for allowed in kind:
            if word.lower() == allowed.lower():
                return json.dumps(allowed)
    note(f"config: {label} has an invalid value ({raw!r}); left as it is")
    return None


def _chosen():
    chosen = []
    for variable, section, key, kind, default in OPTIONS:
        raw = os.environ.get(variable, "").strip()
        if raw:
            value = _format(kind, raw, key)
            if value is not None:
                chosen.append((section, key, value, value != _format(kind, default, key)))
    return chosen


def _set(text, section, key, value):
    live = re.compile(rf'(?m)^(\s*"{re.escape(key)}"\s*:\s*)(?:{LIVE_VALUE})')
    text, count = live.subn(lambda m: m.group(1) + value, text, count=1)
    if count:
        return text, True
    opening = re.compile(rf'(?m)^(\s*"{re.escape(section)}"\s*:\s*\{{[^\n]*\n)')
    text, count = opening.subn(lambda m: f'{m.group(1)}    "{key}": {value},\n', text, count=1)
    return text, bool(count)


def apply():
    chosen = _chosen()
    path = settings.coop_data_dir().parent / "mod-config.json"
    if path.exists():
        text = path.read_text(encoding="utf-8-sig")
    else:
        chosen = [item for item in chosen if item[3]]
        if not chosen:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        text = '{\n  "difficulty": {\n  },\n  "modOptions": {\n  },\n}\n'
        note("config: mod-config.json did not exist yet; creating it with only the settings changed in the Panel")

    for section, key, value, _changed in chosen:
        text, done = _set(text, section, key, value)
        if not done:
            note(f"config: could not place {key} in mod-config.json; left as it is")
    path.write_text(text, encoding="utf-8")
    note(f"config: mod-config.json updated from {len(chosen)} Panel setting(s)")
