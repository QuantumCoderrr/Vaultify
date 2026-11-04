"""Password generation and strength analysis utilities."""

import math
import re
import secrets
import string
from dataclasses import dataclass

AMBIGUOUS = set("Il1O0o")
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?/"

WORDLIST = (
    "amber anchor apple arrow atlas aurora autumn badge bamboo beacon berry blaze "
    "breeze bridge brook cabin cactus canyon carbon cedar cinder citrus cliff cloud "
    "comet copper coral cosmos crane crystal dawn delta desert drift dune eagle echo "
    "ember falcon fern fjord flame forest fossil frost galaxy garden glacier granite "
    "harbor hazel horizon island ivory jade jasmine jungle kayak kernel lagoon lantern "
    "lemon lotus lunar maple marble meadow meteor mint mirror monsoon mosaic nebula "
    "nectar nova oasis ocean olive onyx orbit orchid otter palm panda pebble pepper "
    "pixel planet plume polar prism quartz quill radar raven reef ripple river rocket "
    "saffron sapphire sequoia shadow sierra silver solar spark spruce summit sunset "
    "talon thunder tide timber topaz tulip tundra velvet violet vortex walnut willow "
    "winter zenith zephyr"
).split()


def generate_password(
    length: int = 20,
    lowercase: bool = True,
    uppercase: bool = True,
    digits: bool = True,
    symbols: bool = True,
    exclude_ambiguous: bool = False,
) -> str:
    """Generate a cryptographically secure random password.

    At least one character from every selected class is guaranteed.
    """
    length = max(4, min(int(length), 128))
    pools = []
    if lowercase:
        pools.append(string.ascii_lowercase)
    if uppercase:
        pools.append(string.ascii_uppercase)
    if digits:
        pools.append(string.digits)
    if symbols:
        pools.append(SYMBOLS)
    if not pools:
        pools.append(string.ascii_lowercase)
    if exclude_ambiguous:
        pools = ["".join(c for c in pool if c not in AMBIGUOUS) for pool in pools]

    alphabet = "".join(pools)
    chars = [secrets.choice(pool) for pool in pools]
    chars += [secrets.choice(alphabet) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def generate_passphrase(words: int = 5, separator: str = "-", capitalize: bool = True,
                        add_number: bool = True) -> str:
    words = max(3, min(int(words), 12))
    chosen = [secrets.choice(WORDLIST) for _ in range(words)]
    if capitalize:
        chosen = [w.capitalize() for w in chosen]
    if add_number:
        chosen.append(str(secrets.randbelow(100)))
    return separator.join(chosen)


@dataclass
class Strength:
    score: int  # 0..4
    label: str
    entropy: float
    feedback: list[str]

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "label": self.label,
            "entropy": round(self.entropy, 1),
            "feedback": self.feedback,
        }


LABELS = ["Very weak", "Weak", "Fair", "Strong", "Excellent"]
COMMON = {
    "password", "123456", "12345678", "qwerty", "letmein", "welcome", "admin",
    "iloveyou", "monkey", "dragon", "football", "abc123", "111111", "sunshine",
    "princess", "master", "shadow", "baseball", "superman", "trustno1",
}


def estimate_strength(password: str) -> Strength:
    """Rough entropy-based strength estimate with actionable feedback."""
    if not password:
        return Strength(0, LABELS[0], 0.0, ["Enter a password."])

    pool = 0
    if re.search(r"[a-z]", password):
        pool += 26
    if re.search(r"[A-Z]", password):
        pool += 26
    if re.search(r"\d", password):
        pool += 10
    if re.search(r"[^A-Za-z0-9]", password):
        pool += 33
    entropy = len(password) * math.log2(pool) if pool else 0.0

    feedback = []
    if len(password) < 12:
        feedback.append("Use at least 12 characters.")
    if not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password):
        feedback.append("Mix upper and lower case letters.")
    if not re.search(r"\d", password):
        feedback.append("Add some numbers.")
    if not re.search(r"[^A-Za-z0-9]", password):
        feedback.append("Add symbols.")
    if re.search(r"(.)\1{2,}", password):
        entropy *= 0.75
        feedback.append("Avoid repeated characters.")
    lowered = password.lower()
    if any(w in lowered for w in COMMON | {"qwerty", "1234", "abcd"}):
        entropy = min(entropy, 25)
        feedback.append("Avoid common words and sequences.")
    elif re.fullmatch(r"[A-Za-z]+\d{1,4}[^A-Za-z0-9]?", password):
        entropy *= 0.6
        feedback.append("A word followed by a number is easy to guess.")

    if entropy < 28:
        score = 0
    elif entropy < 40:
        score = 1
    elif entropy < 60:
        score = 2
    elif entropy < 80:
        score = 3
    else:
        score = 4
    return Strength(score, LABELS[score], entropy, feedback)
