from __future__ import annotations

import hashlib
import json
import os
import socket
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


class CoordinationError(RuntimeError):
    pass


def digest(path: Path) -> str:
    if not path.exists(): return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class Lease:
    token: str
    target: str
    replica: str
    base_hash: str
    expires: float


class Coordinator:
    """Local lock + shared lease + committed baseline; never edits the target."""
    def __init__(self, vault: Path, local: Path, shared: Path, replica: str | None = None):
        self.vault, self.local, self.shared = vault, local, shared
        self.replica = replica or socket.gethostname()
        self.local.mkdir(parents=True, exist_ok=True); self.shared.mkdir(parents=True, exist_ok=True)

    def paths(self, target: str):
        key = hashlib.sha256(target.lower().encode()).hexdigest()[:24]
        return self.local / f"{key}.lock", self.shared / f"{key}.lease", self.shared / f"{key}.baseline"

    @staticmethod
    def create(path: Path, data: dict):
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle: json.dump(data, handle)

    @staticmethod
    def read(path: Path):
        try: return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): return None

    def begin(self, target: str, ttl: int = 300) -> Lease:
        local, shared, baseline = self.paths(target); token = uuid.uuid4().hex
        try: self.create(local, {"token": token})
        except FileExistsError as exc: raise CoordinationError("local writer active") from exc
        current = digest(self.vault / target); committed = self.read(baseline)
        if committed and committed["hash"] != current:
            local.unlink(missing_ok=True); raise CoordinationError("replica stale")
        lease = Lease(token, target, self.replica, current, time.time() + ttl)
        try: self.create(shared, asdict(lease))
        except FileExistsError as exc:
            local.unlink(missing_ok=True); raise CoordinationError("shared writer active") from exc
        if not committed: baseline.write_text(json.dumps({"hash": current}), encoding="utf-8")
        return lease

    def verify(self, lease: Lease):
        local, shared, baseline = self.paths(lease.target)
        if self.read(local).get("token") != lease.token or self.read(shared).get("token") != lease.token:
            raise CoordinationError("lease token mismatch")
        if lease.expires < time.time(): raise CoordinationError("lease expired")
        if digest(self.vault / lease.target) != lease.base_hash: raise CoordinationError("target changed")
        if self.read(baseline)["hash"] != lease.base_hash: raise CoordinationError("baseline changed")

    def commit(self, lease: Lease):
        local, shared, baseline = self.paths(lease.target)
        if self.read(shared).get("token") != lease.token: raise CoordinationError("lease token mismatch")
        baseline.write_text(json.dumps({"hash": digest(self.vault / lease.target)}), encoding="utf-8")
        shared.unlink(missing_ok=True); local.unlink(missing_ok=True)

    def abort(self, lease: Lease):
        local, shared, _ = self.paths(lease.target)
        if (self.read(shared) or {}).get("token") == lease.token: shared.unlink(missing_ok=True)
        if (self.read(local) or {}).get("token") == lease.token: local.unlink(missing_ok=True)
