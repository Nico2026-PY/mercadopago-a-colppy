from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from .domain import Movement, ParseIssue
from .excel_io import ProgressCallback, read_mercadopago_files
from .history import HistoryRepository


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    mode: str
    source_files: list[str]
    total_rows: int
    unique_movements: list[Movement]
    new_movements: list[Movement]
    already_imported: list[Movement]
    issues: list[ParseIssue]
    duplicate_count: int

    @property
    def entries_total(self) -> Decimal:
        return sum((item.amount for item in self.new_movements if item.amount > 0), Decimal("0"))

    @property
    def exits_total(self) -> Decimal:
        return sum((item.amount for item in self.new_movements if item.amount < 0), Decimal("0"))

    @property
    def net_total(self) -> Decimal:
        return sum((item.amount for item in self.new_movements), Decimal("0"))


class ImportService:
    def __init__(self, history: HistoryRepository):
        self.history = history

    def analyze(
        self,
        paths: Sequence[str | Path],
        mode: str,
        progress: ProgressCallback | None = None,
    ) -> AnalysisResult:
        if not paths:
            raise ValueError("Seleccioná al menos un archivo de Mercado Pago")
        if mode not in {"Diario", "Mensual"}:
            raise ValueError("El modo debe ser Diario o Mensual")

        read_result = read_mercadopago_files(paths, progress=progress)
        unique_by_key: dict[str, Movement] = {}
        duplicate_count = 0
        for movement in read_result.movements:
            if movement.key in unique_by_key:
                duplicate_count += 1
                continue
            unique_by_key[movement.key] = movement

        unique_movements = sorted(
            unique_by_key.values(),
            key=lambda item: (item.date, item.occurred_at, item.receipt),
        )
        imported = self.history.imported_keys(item.key for item in unique_movements)
        already_imported = [item for item in unique_movements if item.key in imported]
        new_movements = [item for item in unique_movements if item.key not in imported]

        return AnalysisResult(
            mode=mode,
            source_files=[Path(path).name for path in paths],
            total_rows=read_result.total_rows,
            unique_movements=unique_movements,
            new_movements=new_movements,
            already_imported=already_imported,
            issues=read_result.issues,
            duplicate_count=duplicate_count,
        )

    def confirm_import(self, result: AnalysisResult, export_path: str | Path) -> int:
        return self.history.confirm_batch(
            result.mode,
            result.source_files,
            result.new_movements,
            export_path,
        )
