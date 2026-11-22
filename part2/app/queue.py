"""Queue stored as one name per line.

The HTTP server must call these functions. Tests call them directly,
with a temporary directory, and do not start Docker.
"""

from __future__ import annotations

from pathlib import Path
from time import sleep


def clean_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("invalid name")
    cleaned = name.strip()
    if not cleaned or len(cleaned) > 40 or name.splitlines() != [name]:
        raise ValueError("invalid name")
    cleaned.encode("utf-8")
    return cleaned


def read_names(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []


def join(path: str | Path, name: str) -> int:
    """Append one person and return the ticket number.

    The ticket number is how many names are in the file after this join.
    Strip spaces around the name before storing it.
    Raise ValueError, and do not create or change the file, when the
    stripped name is empty, longer than 40 characters, or the original
    name contains a newline.
    """
    name = clean_name(name)
    path = Path(path)
    ticket = len(read_names(path)) + 1
    # Make the overlap easier to see in the before-lock experiment.
    sleep(0.02)
    with path.open("a", encoding="utf-8") as queue:
        queue.write(name + "\n")
    return ticket


def take(path: str | Path) -> str:
    """Remove and return the first name.

    Raise LookupError when the file is missing or has no names.
    """
    path = Path(path)
    names = read_names(path)
    if not names:
        raise LookupError("empty queue")
    path.write_text("".join(name + "\n" for name in names[1:]), encoding="utf-8")
    return names[0]
