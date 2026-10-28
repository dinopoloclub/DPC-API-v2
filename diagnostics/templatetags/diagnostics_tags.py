"""Template filters used by the report browser"""

from dataclasses import dataclass

from django import template

from .. import games, grouping

register = template.Library()


@dataclass(frozen=True)
class StackFrame:
    """One line of a stack trace, and whether it's engine code"""

    text: str
    is_library: bool


@register.filter
def game_name(code: str) -> str:
    """Full game name for a game code (MO,MA)"""
    return games.game_name(code)


@register.filter
def stack_frames(stack_trace: str) -> list[StackFrame]:
    """Split a stack trace into lines and mark engine frames"""
    return [
        StackFrame(text=line, is_library=grouping.is_library_frame(line))
        for line in stack_trace.strip().splitlines()
        if line.strip()
    ]


@register.filter
def is_multiline(value: str) -> bool:
    """If a value is long or has multiple lines. It will get shown as a block in this case"""
    return "\n" in value or len(value) > 120
