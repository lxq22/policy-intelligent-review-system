from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


@dataclass(frozen=True)
class StoredFile:
    relative_path: str
    original_name: str
    mime_type: str
    size: int
    sha256: str


class FileStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, upload: UploadFile, namespace: str) -> StoredFile:
        directory = (self.root / namespace).resolve()
        if not directory.is_relative_to(self.root):
            raise ValueError("文件存储目录不安全")
        directory.mkdir(parents=True, exist_ok=True)

        original_name = Path(upload.filename or "未命名文件").name
        suffix = Path(original_name).suffix.lower()
        target = directory / f"{uuid4().hex}{suffix}"
        temporary = directory / f".{target.name}.{uuid4().hex}.tmp"
        digest = hashlib.sha256()
        size = 0
        try:
            upload.file.seek(0)
            with temporary.open("wb") as output:
                while chunk := upload.file.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

        return StoredFile(
            relative_path=target.relative_to(self.root).as_posix(),
            original_name=original_name,
            mime_type=upload.content_type or "application/octet-stream",
            size=size,
            sha256=digest.hexdigest(),
        )

    def resolve(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("文件路径不安全")
        return path

    def delete(self, relative_path: str) -> None:
        self.resolve(relative_path).unlink(missing_ok=True)
