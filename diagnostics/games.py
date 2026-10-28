"""
The games that send reports.

Reports are told apart by the "title" metadata field, which becomes Report.game. If a game has no entry here
it will still work but it will just use the code.
"""

# The game used when a report has no title (MO never sent one, MM doesn't seem to publish here)
DEFAULT_GAME = "MO"

GAME_NAMES = {
    "MA": "Mini Architect",
    "MO": "Mini Motorways",
}


def game_name(code: str) -> str:
    """The display name for a game code"""
    return GAME_NAMES.get(code, code)
