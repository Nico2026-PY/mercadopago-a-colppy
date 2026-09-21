from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import unicodedata
from typing import Iterable, Protocol, Sequence

from .companies import Company


@dataclass(frozen=True, slots=True)
class CompanyDetection:
    status: str
    company_id: str | None
    unknown_files: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PeriodClassification:
    mode: str | None
    start: date | None
    end: date | None
    error: str | None = None
    warning: str | None = None


class DatedMovement(Protocol):
    date: date
    transaction_type: str


def _searchable(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(re.sub(r"[^A-Za-z0-9]+", " ", without_accents).casefold().split())


def detect_company_from_paths(paths: Iterable[str | Path], companies: Sequence[Company]) -> CompanyDetection:
    matched_ids: set[str] = set()
    unknown_files: list[str] = []
    normalized_companies = [(company.id, _searchable(company.name)) for company in companies]

    for raw_path in paths:
        path = Path(raw_path)
        searchable_name = f" {_searchable(path.stem)} "
        file_matches = {
            company_id
            for company_id, company_name in normalized_companies
            if company_name and f" {company_name} " in searchable_name
        }
        if len(file_matches) != 1:
            if len(file_matches) > 1:
                matched_ids.update(file_matches)
            else:
                unknown_files.append(path.name)
            continue
        matched_ids.update(file_matches)

    if len(matched_ids) > 1:
        return CompanyDetection("mixed", None, tuple(unknown_files))
    if len(matched_ids) == 1:
        company_id = next(iter(matched_ids))
        status = "partial" if unknown_files else "matched"
        return CompanyDetection(status, company_id, tuple(unknown_files))
    return CompanyDetection("unknown", None, tuple(unknown_files))


def classify_period(values: Iterable[date]) -> PeriodClassification:
    unique_dates = sorted(set(values))
    if not unique_dates:
        return PeriodClassification(None, None, None, "No hay movimientos válidos para identificar el período")
    start = unique_dates[0]
    end = unique_dates[-1]
    months = {(value.year, value.month) for value in unique_dates}
    if len(months) > 1:
        return PeriodClassification(None, start, end, "El archivo contiene movimientos de más de un mes")
    mode = "Diario" if len(unique_dates) == 1 else "Mensual"
    return PeriodClassification(mode, start, end)


def classify_movement_period(
    movements: Iterable[DatedMovement],
    selected_mode: str,
) -> PeriodClassification:
    items = list(movements)
    ordinary = classify_period(item.date for item in items)
    if ordinary.error is None or selected_mode != "Mensual":
        return ordinary

    regular_items = [item for item in items if item.transaction_type != "Reclamo"]
    if not regular_items:
        return ordinary

    regular_months = {(item.date.year, item.date.month) for item in regular_items}
    if len(regular_months) != 1:
        return ordinary

    main_month = next(iter(regular_months))
    out_of_month = [
        item for item in items if (item.date.year, item.date.month) != main_month
    ]
    if not out_of_month or any(
        item.transaction_type != "Reclamo"
        or (item.date.year, item.date.month) >= main_month
        for item in out_of_month
    ):
        return ordinary

    main_dates = sorted(
        item.date for item in items if (item.date.year, item.date.month) == main_month
    )
    claim_dates = ", ".join(
        sorted({item.date.strftime("%d/%m/%Y") for item in out_of_month})
    )
    count = len(out_of_month)
    warning = (
        f"Se incluirá {count} Reclamo de otro mes con su fecha de origen ({claim_dates})."
        if count == 1
        else f"Se incluirán {count} Reclamos de otros meses con sus fechas de origen ({claim_dates})."
    )
    return PeriodClassification("Mensual", main_dates[0], main_dates[-1], warning=warning)


def output_filename(company_name: str, mode: str, start: date, end: date) -> str:
    safe_company = re.sub(r'[<>:"/\\|?*]+', " ", company_name)
    safe_company = " ".join(safe_company.split()).strip(" .") or "Empresa"
    if mode == "Diario":
        period = start.strftime("%d-%m-%Y")
    elif mode == "Mensual":
        period = start.strftime("%m-%Y")
    else:
        raise ValueError("El modo debe ser Diario o Mensual")
    return f"MP {safe_company} {mode.upper()} {period}.csv"
