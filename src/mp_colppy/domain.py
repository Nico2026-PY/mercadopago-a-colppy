from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Mapping


ALIASES: dict[str, tuple[str, ...]] = {
    "source_id": ("ID DE OPERACIÓN EN MERCADO PAGO", "SOURCE_ID"),
    "transaction_type": ("TIPO DE OPERACIÓN", "TRANSACTION_TYPE"),
    "transaction_date": ("FECHA DE ORIGEN", "TRANSACTION_DATE", "TRANSACTION_DATE_SHORT"),
    "gross_amount": ("VALOR DE LA COMPRA", "TRANSACTION_AMOUNT"),
    "payer_name": ("PAGADOR", "PAYER_NAME"),
    "payer_id_type": (
        "TIPO DE IDENTIFICACIÓN DEL PAGADOR",
        "PAYER_ID_TYPE",
        "PAYER_IDENTIFICATION_TYPE",
    ),
    "payer_id_number": (
        "NÚMERO DE IDENTIFICACIÓN DEL PAGADOR",
        "PAYER_ID",
        "PAYER_ID_NUMBER",
        "PAYER_IDENTIFICATION_NUMBER",
    ),
    "bank_name": ("BANCO DE ORIGEN", "POI_BANK_NAME"),
    "payment_method": ("MEDIO DE PAGO", "PAYMENT_METHOD"),
    "store_name": ("NOMBRE DE LOCAL", "STORE_NAME"),
}

REQUIRED_FIELDS = ("source_id", "transaction_type", "transaction_date", "gross_amount")
KNOWN_TRANSACTION_TYPES = {
    "Pago aprobado",
    "PAYOUTS",
    "Devolución de dinero",
    "Reclamo",
}


@dataclass(frozen=True, slots=True)
class Movement:
    key: str
    source_id: str
    date: date
    occurred_at: str
    transaction_type: str
    amount: Decimal
    concept: str
    receipt: str
    source_file: str
    row_number: int
    raw: Mapping[str, Any] = field(compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class ParseIssue:
    source_file: str
    row_number: int
    message: str


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def value_for(row: Mapping[str, Any], field_name: str) -> Any:
    for alias in ALIASES[field_name]:
        if alias in row and not _blank(row[alias]):
            return row[alias]
    return None


def _identifier(value: Any) -> str:
    if _blank(value):
        raise ValueError("Falta ID de operación de Mercado Pago")
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def _decimal(value: Any) -> Decimal:
    if _blank(value):
        raise ValueError("Falta valor de la compra")
    if isinstance(value, str):
        cleaned = value.strip().replace("$", "").replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
    else:
        cleaned = str(value)
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Valor de la compra inválido: {value}") from exc


def _date_and_timestamp(value: Any) -> tuple[date, str]:
    if _blank(value):
        raise ValueError("Falta fecha de origen")
    if isinstance(value, datetime):
        return value.date(), value.isoformat()
    if isinstance(value, date):
        return value, value.isoformat()
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.date(), text
    except ValueError:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                parsed_date = datetime.strptime(text[:10], fmt).date()
                return parsed_date, text
            except ValueError:
                continue
    raise ValueError(f"Fecha de origen inválida: {value}")


def _text(value: Any) -> str:
    return "" if _blank(value) else str(value).strip()


def _receipt(source_id: str, transaction_type: str) -> str:
    suffix = {
        "Devolución de dinero": "-DEV",
        "Reclamo": "-REC",
        "PAYOUTS": "-PAYOUT",
    }.get(transaction_type, "")
    return f"MP-{source_id}{suffix}"


def normalize_row(row: Mapping[str, Any], source_file: str | Path, row_number: int = 2) -> Movement:
    source_id = _identifier(value_for(row, "source_id"))
    transaction_type = _text(value_for(row, "transaction_type"))
    if not transaction_type:
        raise ValueError("Falta tipo de operación")
    if transaction_type not in KNOWN_TRANSACTION_TYPES:
        raise ValueError(f"Tipo de operación no reconocido: {transaction_type}")
    movement_date, occurred_at = _date_and_timestamp(value_for(row, "transaction_date"))
    amount = _decimal(value_for(row, "gross_amount"))
    if amount == 0:
        raise ValueError("El valor de la compra es cero")

    payer_id_number = _text(value_for(row, "payer_id_number"))
    concept_parts = []
    if transaction_type != "Pago aprobado":
        concept_parts.append(transaction_type)
    concept_parts.extend(
        (
            _text(value_for(row, "store_name")),
            _text(value_for(row, "payer_name")),
        )
    )
    if payer_id_number:
        concept_parts.extend(
            (
                _text(value_for(row, "payer_id_type")),
                payer_id_number,
            )
        )
    concept: list[str] = []
    for part in concept_parts:
        if part and part not in concept:
            concept.append(part)
    concept_text = " - ".join(concept)[:255] or "Mercado Pago"
    amount_text = format(amount, ".2f")
    key = "|".join((source_id, transaction_type, occurred_at, amount_text))

    return Movement(
        key=key,
        source_id=source_id,
        date=movement_date,
        occurred_at=occurred_at,
        transaction_type=transaction_type,
        amount=amount,
        concept=concept_text,
        receipt=_receipt(source_id, transaction_type),
        source_file=Path(source_file).name,
        row_number=row_number,
        raw=dict(row),
    )
