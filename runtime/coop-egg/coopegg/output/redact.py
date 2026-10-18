import re

OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
IPV4 = rf"{OCTET}\.{OCTET}\.{OCTET}\.{OCTET}"
NOT_AFTER = r"(?<![\w.])"
NOT_BEFORE = r"(?![\w]|\.\d)"
KEEP = {"0.0.0.0", "127.0.0.1"}

IP_TAG = "<redacted-ip>"
USER_TAG = "<redacted-steam-user>"
PASSWORD_TAG = "<redacted>"
ID_TAG = "<redacted-steam-id>"

PRIVATE_RANGES = (
    r"(?:192\.168|172\.(?:1[6-9]|2\d|3[01])|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])|169\.254)"
    rf"\.{OCTET}\.{OCTET}"
)
ADDRESS_WORDS = (
    r"(?i)\b(?:ip|ipv4|ips|address(?:es)?|addr|from|host|endpoint|remote|peer|client|"
    r"bound to|listening on|connect(?:ed|ing)? to)\b"
)


def _hide_ip(match):
    ip = match.group("ip")
    return match.group(0) if ip in KEEP else match.group(0).replace(ip, IP_TAG)


def _hide_ten_net(match):
    return match.group(0) if match.group("ip").startswith("10.0.0.") else IP_TAG


def _hide_ipv6(match):
    text = match.group(0)
    return IP_TAG if ("::" in text or re.search(r"[a-fA-F]", text)) else text


class Redactor:
    def __init__(self, account="", password="", addresses=(), every_address=False):
        self.secrets = [s for s in (password if len(password) >= 4 else "",
                                    account if len(account) >= 3 else "") if s]
        self.rules = []
        if self.secrets and len(password) >= 4:
            self.rules.append((re.compile(re.escape(password)), PASSWORD_TAG))
        if len(account) >= 3:
            word = r"(?<![A-Za-z0-9_])" + re.escape(account) + r"(?![A-Za-z0-9_])"
            self.rules.append((re.compile(word, re.I), USER_TAG))
        for address in addresses:
            if address and address not in KEEP:
                self.rules.append((re.compile(NOT_AFTER + re.escape(address) + r"(?!\d)"), IP_TAG))

        self.rules += [
            (re.compile(r"\[U:\d:\d+\]"), ID_TAG),
            (re.compile(r"\bSTEAM_[0-5]:[01]:\d+\b"), ID_TAG),
            (re.compile(r"(?<!\d)7656119\d{10}(?!\d)"), ID_TAG),
        ]
        self.rules += self._address_rules(every_address)

    @staticmethod
    def _address_rules(every_address):
        if every_address:
            return [
                (re.compile(NOT_AFTER + rf"(?P<ip>{IPV4})(?!\d)"), _hide_ip),
                (re.compile(r"(?<![\w:.])(?=[0-9a-fA-F:]*::|(?:[0-9a-fA-F]{1,4}:){5})"
                            r"(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(?![\w:])"),
                 lambda m: IP_TAG if re.search(r"[0-9a-fA-F]", m.group(0)) else m.group(0)),
            ]
        return [
            (re.compile(NOT_AFTER + rf"(?P<ip>{IPV4}):\d{{1,5}}(?!\d)"), _hide_ip),
            (re.compile(rf"@(?P<ip>{IPV4})(?!\d)"), _hide_ip),
            (re.compile(rf"::ffff:(?P<ip>{IPV4})(?!\d)", re.I), _hide_ip),
            (re.compile(NOT_AFTER + rf"(?P<ip>{PRIVATE_RANGES})" + NOT_BEFORE), _hide_ip),
            (re.compile(NOT_AFTER + rf"(?P<ip>10\.{OCTET}\.{OCTET}\.{OCTET})" + NOT_BEFORE), _hide_ten_net),
            (re.compile(ADDRESS_WORDS + rf"[\s:=(\['\"]*(?P<ip>{IPV4})(?!\d|\.\d)"), _hide_ip),
            (re.compile(r"\[[0-9a-fA-F:]*:[0-9a-fA-F:]*:[0-9a-fA-F:]*\](?::\d{1,5})?"), _hide_ipv6),
        ]

    def text(self, text):
        try:
            for pattern, replacement in self.rules:
                text = pattern.sub(replacement, text)
            return text
        except Exception:
            return "[text removed: redaction error]\n" if text.endswith("\n") else "[text removed]"

    def blank_in_bytes(self, data):
        for secret in self.secrets:
            for encoding in ("utf-8", "utf-16-le"):
                raw = secret.encode(encoding)
                fill = "X".encode(encoding) * len(secret)
                data = re.sub(re.escape(raw), fill, data, flags=re.I)
        return data
