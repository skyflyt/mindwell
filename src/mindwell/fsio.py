"""Atomic file writes.

``Path.write_text`` opens its target with mode ``"w"``, which truncates the
file before writing the new content. Anything that fails between those two
steps - an encoding error in the payload, a full disk, a killed process -
leaves the file at zero bytes, and the caller sees an exception that looks
recoverable while the data is already gone. This destroyed the same
production vault file twice in five days before this module existed; both
times a stray surrogate raised during the encode, after the truncate.

``atomic_write_text`` closes that window. It encodes first, so a bad payload
fails before anything touches disk. It writes to a sibling temporary file and
fsyncs it, then moves it over the target with ``os.replace``, which is atomic
on POSIX and NTFS. A reader observes the old content or the new content,
never an empty file.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write ``text`` to ``path`` so the file is never observable half-written.

    The temporary file lives in ``path``'s own directory because
    ``os.replace`` is only atomic within one filesystem.
    """
    data = text.encode(encoding)
    atomic_write_bytes(path, data)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomically replace binary content, including backup and restore files."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent),
                               prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
