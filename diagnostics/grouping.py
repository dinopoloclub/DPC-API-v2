"""
Groups crash and error reports into Issues.

Two reports belong to the same Issue when they come from the same game and have the same
fingerprint. A fingerprint is a hash of the error message and the top N sanitized stackframes.

If grouping is too eager or too fussy, adjust the rules below, then run
`python manage.py regroup_issues` to apply them to every existing report.
"""

import hashlib
import re
from dataclasses import dataclass

from .models import Issue

# How many stack frames (after skipping logging frames) make up the fingerprint
FRAMES_IN_FINGERPRINT = 5

# Frames that are obviously not part of the error
LOGGING_FRAME_PREFIXES = (
    "UnityEngine.Debug",
    "UnityEngine.Logger",
    "UnityEngine.DebugLogHandler",
    "UnityEngine.Assertions",
    "Mini3.Diagnostics.Log",
    "Mini3.Diagnostics.Assert",
    "Mini3.Diagnostics.Verify",
    "Mini3.Diagnostics.EventMonitor",
)

# Frames from the engine and runtime rather than our own code. These are shown dimmed in the UI
LIBRARY_FRAME_PREFIXES = ("UnityEngine.", "UnityEditor.", "Unity.", "System.", "Mono.")

QUOTED_TEXT = re.compile(r"'[^']*'|\"[^\"]*\"")
GUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
HEX_NUMBER = re.compile(r"\b0x[0-9a-f]+\b", re.I)
NUMBER = re.compile(r"\d+")
WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Fingerprint:
    """Issue hash plus the parts shown in the issue list"""

    hash: str
    title: str
    culprit: str


def frame_name(line: str) -> str:
    """
    The method a stack frame line refers to, sanitized of variables / line numbers / arguments

    "Mini3.Foo:Bar (int) (at Assets/Foo.cs:12)" -> "Mini3.Foo:Bar"
    "  at Mini3.Foo.Bar () [0x00012] in <abc123>:0" -> "Mini3.Foo.Bar"
    """
    return line.strip().removeprefix("at ").split("(", 1)[0].strip()


def is_library_frame(line: str) -> bool:
    """Check if a stack frame is from engine/library code"""
    return line.strip().removeprefix("at ").startswith(LIBRARY_FRAME_PREFIXES)


def meaningful_frames(stack_trace: str) -> list[str]:
    """The method names in a stack trace, skipping log frames"""
    frames = [frame_name(line) for line in stack_trace.splitlines()]
    frames = [frame for frame in frames if frame]
    useful = [frame for frame in frames if not frame.startswith(LOGGING_FRAME_PREFIXES)]
    # If every frame is a logging frame... well, just keep that.
    return useful or frames


def normalise_message(message: str) -> str:
    """The first line of the message, stripping things that can change between runs"""
    first_line = message.strip().split("\n", 1)[0][:300]
    first_line = QUOTED_TEXT.sub("'…'", first_line)
    first_line = GUID.sub("<guid>", first_line)
    first_line = HEX_NUMBER.sub("<hex>", first_line)
    first_line = NUMBER.sub("#", first_line)
    return WHITESPACE.sub(" ", first_line)


def fingerprint_for(message: str, stack_trace: str) -> Fingerprint | None:
    """Create a fingerprint for an error, or return None if not possible (a manual report or gameover report)"""
    if not message.strip() and not stack_trace.strip():
        return None

    frames = meaningful_frames(stack_trace)[:FRAMES_IN_FINGERPRINT]
    # Compiler-generated names contain numbers that change between builds
    stable_frames = [NUMBER.sub("#", frame) for frame in frames]
    parts = [normalise_message(message), *stable_frames]

    title = message.strip().split("\n", 1)[0] or "(no message)"
    # The culprit is the first frame in our own code
    our_frames = [frame for frame in frames if not is_library_frame(frame)]
    culprit = (our_frames or frames or [""])[0]
    return Fingerprint(
        hash=hashlib.sha256("\n".join(parts).encode()).hexdigest(),
        title=title[:300],
        culprit=culprit[:300],
    )


def find_or_create_issue(game: str, message: str, stack_trace: str, reopen_resolved: bool = True) -> Issue | None:
    """Find a matching issue for a new report, or create a new one"""
    fingerprint = fingerprint_for(message, stack_trace)
    if fingerprint is None:
        return None

    issue, _ = Issue.objects.get_or_create(
        game=game,
        fingerprint=fingerprint.hash,
        defaults={"title": fingerprint.title, "culprit": fingerprint.culprit},
    )

    # A developer was overly hopeful :'(
    if reopen_resolved and issue.status == Issue.Status.RESOLVED:
        issue.status = Issue.Status.OPEN
        issue.save(update_fields=["status"])

    return issue
