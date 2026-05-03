import re


PLAYER_NAME_MIN_LENGTH = 3
PLAYER_NAME_MAX_LENGTH = 20
PLAYER_NAME_PATTERN = re.compile(
    r"^(?:[._'-])?[A-Za-z0-9]+(?:[ _.'-][A-Za-z0-9]+)*(?:[._'-])?$"
)
PLAYER_NAME_ERROR_MESSAGE = (
    "Use letters and numbers with single spaces, hyphens (-), apostrophes ('), "
    "underscores (_), or periods (.). No repeated separators, and spaces cannot "
    "appear at the start or end."
)
PLAYER_NAME_LENGTH_ERROR_MESSAGE = (
    f"Use between {PLAYER_NAME_MIN_LENGTH} and {PLAYER_NAME_MAX_LENGTH} characters."
)
PLAYER_NAME_PROFANITY_ERROR_MESSAGE = "Name contains disallowed language."
DEFAULT_PLAYER_NAME_DIGITS = 8
DEFAULT_PLAYER_NAME_MODULUS = 10**DEFAULT_PLAYER_NAME_DIGITS
DEFAULT_PLAYER_NAME_MULTIPLIER = 54_435_761
DEFAULT_PLAYER_NAME_INCREMENT = 70_460_293

PLAYER_NAME_PROFANITY_TERMS = {
    "bitch",
    "cock",
    "cunt",
    "dick",
    "fuck",
    "fucking",
    "motherfucker",
    "nigga",
    "nigger",
    "pussy",
    "shit",
    "slut",
    "whore",
}

PLAYER_NAME_LEETSPEAK_MAP = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
        "!": "i",
    }
)


def _contains_profanity(value: str) -> bool:
    normalized_value = value.lower().translate(PLAYER_NAME_LEETSPEAK_MAP)
    tokens = re.findall(r"[a-z0-9]+", normalized_value)

    if any(token in PLAYER_NAME_PROFANITY_TERMS for token in tokens):
        return True

    collapsed = "".join(tokens)
    if any(term in collapsed for term in PLAYER_NAME_PROFANITY_TERMS):
        return True

    return False


def clean_player_name(value: str) -> str:
    cleaned_value = (value or "").strip()
    if not cleaned_value:
        raise ValueError("Name is required.")
    if not PLAYER_NAME_MIN_LENGTH <= len(cleaned_value) <= PLAYER_NAME_MAX_LENGTH:
        raise ValueError(PLAYER_NAME_LENGTH_ERROR_MESSAGE)
    if not PLAYER_NAME_PATTERN.fullmatch(cleaned_value):
        raise ValueError(PLAYER_NAME_ERROR_MESSAGE)
    if _contains_profanity(cleaned_value):
        raise ValueError(PLAYER_NAME_PROFANITY_ERROR_MESSAGE)
    return cleaned_value


def generate_default_player_name(player_id: int) -> str:
    scrambled_id = (
        (player_id * DEFAULT_PLAYER_NAME_MULTIPLIER) + DEFAULT_PLAYER_NAME_INCREMENT
    ) % DEFAULT_PLAYER_NAME_MODULUS
    return f"player_{scrambled_id:0{DEFAULT_PLAYER_NAME_DIGITS}d}"
