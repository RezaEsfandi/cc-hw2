"""Queue stored as one name per line.

The HTTP server must call these functions. Tests call them directly,
with a temporary directory, and do not start Docker.
"""

from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile


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


@contextmanager
def queue_lock(path: Path):
    # Lock a stable file. queue.txt can be replaced while this lock is held.
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


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
    with queue_lock(path):
        ticket = len(read_names(path)) + 1
        with path.open("a", encoding="utf-8") as queue:
            queue.write(name + "\n")
        return ticket


def take(path: str | Path) -> str:
    """Remove and return the first name.

    Raise LookupError when the file is missing or has no names.
    """
    path = Path(path)
    with queue_lock(path):
        names = read_names(path)
        if not names:
            raise LookupError("empty queue")
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
            temporary_path = Path(tmp.name)
            try:
                tmp.writelines(name + "\n" for name in names[1:])
                tmp.close()
                os.replace(temporary_path, path)
            finally:
                temporary_path.unlink(missing_ok=True)
        return names[0]
