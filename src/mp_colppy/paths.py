from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys


@dataclass(frozen=True, slots=True)
class CompanyPaths:
    company_id: str
    data: Path
    database: Path
    outputs: Path
    backups: Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path
    data: Path
    database: Path
    outputs: Path
    backups: Path
    config: Path
    company_data: Path

    def for_company(self, company_id: str) -> CompanyPaths:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", company_id):
            raise ValueError("El identificador de empresa no es válido")
        data = self.company_data / company_id
        outputs = self.outputs / company_id
        backups = self.backups / company_id
        for directory in (data, outputs, backups):
            directory.mkdir(parents=True, exist_ok=True)
        return CompanyPaths(company_id, data, data / "historial.db", outputs, backups)


def resolve_app_paths(
    executable: str | Path | None = None,
    frozen: bool | None = None,
    source_root: str | Path | None = None,
) -> AppPaths:
    explicit_home = os.environ.get("MP_COLPPY_HOME", "").strip()
    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if explicit_home:
        root = Path(explicit_home).resolve()
    elif is_frozen:
        executable_path = Path(executable or sys.executable).resolve()
        root = executable_path.parent
    else:
        root = Path(source_root).resolve() if source_root else Path(__file__).resolve().parents[2]

    data = root / "datos"
    outputs = root / "salidas"
    backups = root / "respaldos"
    company_data = data / "empresas"
    for directory in (data, company_data, outputs, backups):
        directory.mkdir(parents=True, exist_ok=True)
    return AppPaths(root, data, data / "historial.db", outputs, backups, data / "config.json", company_data)
