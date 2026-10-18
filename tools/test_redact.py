import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runtime" / "coop-egg"))
from coopegg.output.redact import Redactor

ACCOUNT, PASSWORD, ADDRESS = "fake_user77", "Hunter2-pass!", "203.0.113.7"


class HidesIdentifyingData(unittest.TestCase):
    def setUp(self):
        self.normal = Redactor(ACCOUNT, PASSWORD, [ADDRESS])
        self.everything = Redactor(ACCOUNT, PASSWORD, [ADDRESS], every_address=True)

    def hidden(self, text, *secrets, redactor=None):
        out = (redactor or self.normal).text(text)
        for secret in secrets:
            self.assertNotIn(secret, out)

    def kept(self, text, *keep, redactor=None):
        out = (redactor or self.normal).text(text)
        for item in keep:
            self.assertIn(item, out)

    def test_steam_login(self):
        self.hidden("Logging in user 'fake_user77' [U:1:698489385] to Steam", ACCOUNT, "698489385")
        self.hidden("Logging in user 'FAKE_USER77'", "FAKE_USER77")
        self.hidden("password is Hunter2-pass! ok", PASSWORD)
        self.hidden("steamid 76561198012345678", "76561198012345678")
        self.kept("user fake_user77x is a different word", "fake_user77x")

    def test_addresses(self):
        self.hidden("SERVER_IP=203.0.113.7", ADDRESS)
        self.hidden("peer queues: 0@81.2.3.4 worldQueue=0", "81.2.3.4")
        self.hidden("Player joined from 81.2.3.4:51234", "81.2.3.4")
        self.hidden("connected from 81.2.3.4 ok", "81.2.3.4")
        self.hidden("docker net 172.18.0.5 here", "172.18.0.5")
        self.hidden("lan 10.1.0.12 here", "10.1.0.12")
        self.hidden("connected from 10.0.0.12", "10.0.0.12")
        self.hidden("v6 [2a02:c7c:1234::1]:4210", "2a02:c7c:1234::1")

    def test_versions_and_normal_text_are_left_alone(self):
        self.kept("System.Runtime, Version=10.0.0.0, Culture=neutral", "10.0.0.0")
        self.kept("assembly-load: Microsoft.Bcl.AsyncInterfaces 10.0.0.8", "10.0.0.8")
        self.kept("unify: Serilog.dll module has 2.0.0.0, Coop has 4.2.0.0", "2.0.0.0", "4.2.0.0")
        self.kept('"fileVersion":  "1.2.3.4"', "1.2.3.4")
        self.kept("loaded: Bannerlord.Harmony 2.4.2.248", "2.4.2.248")
        self.kept("five parts 1.2.3.4.5", "1.2.3.4.5")
        self.kept("[12:34:56] engine time", "[12:34:56]")
        self.kept("listening on 0.0.0.0:4210", "0.0.0.0:4210")
        self.kept("[DedicatedServer] SERVING", "[DedicatedServer] SERVING")

    def test_steam_logs_hide_every_address(self):
        self.hidden("cache15.steamcontent.com (23.1.2.3:443 / 23.1.2.3:443)", "23.1.2.3", redactor=self.everything)
        self.hidden("local address (81.2.3.4:51000)", "81.2.3.4", redactor=self.everything)
        self.hidden("ipv6 2001:db8::1 here", "2001:db8::1", redactor=self.everything)
        self.kept("progress: 12.34 (1 / 2) at 12:34:56", "12.34", "12:34:56", redactor=self.everything)

    def test_binary_dump_keeps_its_length(self):
        data = b"MZ\x00\x00" + PASSWORD.encode() + b"\x00" + ACCOUNT.encode("utf-16-le")
        out = self.normal.blank_in_bytes(data)
        self.assertEqual(len(out), len(data))
        self.assertNotIn(PASSWORD.encode(), out)
        self.assertNotIn(ACCOUNT.encode("utf-16-le"), out)


if __name__ == "__main__":
    unittest.main()
