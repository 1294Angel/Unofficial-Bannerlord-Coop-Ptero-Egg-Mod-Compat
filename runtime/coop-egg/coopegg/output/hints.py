import re

RULES = [
    ("Coop EULA not accepted",
     r"EULA acceptance required",
     "Read DedicatedServer/EULA.md and LICENSE.txt, then set 'Accept Coop EULA' to 1 in the Startup tab."),
    ("A system call was blocked (Bad system call)",
     r"Bad system call|SIGSYS",
     "The node's Docker seccomp profile blocks something Wine needs. See 'Troubleshooting' in the README."),
    ("Out of memory",
     r"Out of memory: true|OutOfMemory|\bKilled\b",
     "Raise the server's Memory limit, or run fewer mods."),
    ("Port already in use",
     r"address already in use|Address already in use",
     "Another server uses this port. Give each server its own allocation."),
    ("Virtual display (Xvfb) failed",
     r"Server is already active for display|Fatal server error|Cannot open display|unable to open display",
     "Restart the server once. If it keeps happening, the node ran out of display numbers."),
    ("A mod failed to load",
     r"HandleSubmoduleLoadError",
     "Open logs/headless-diag.log and look for 'loader:' lines naming the mod; remove that mod and restart."),
    ("A mod's Harmony patch failed",
     r"HarmonyException|Patching exception in method",
     "The method named in the message belongs to a mod that is not compatible with a dedicated server."),
    ("Engine crashed",
     r"Detected server process in a crashed state",
     "Read the lines just before this message, and logs/headless-diag.log."),
]


class Hints:
    def __init__(self, show):
        self.show = show
        self.seen = set()
        self.rules = [(name, re.compile(pattern), fix) for name, pattern, fix in RULES]

    def check(self, line):
        for name, pattern, fix in self.rules:
            if name not in self.seen and pattern.search(line):
                self.seen.add(name)
                self.show(f"[hint] {name}")
                self.show(f"[hint]   {fix}")
