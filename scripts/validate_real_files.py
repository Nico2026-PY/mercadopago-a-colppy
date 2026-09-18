from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.mp_colppy.history import HistoryRepository
from src.mp_colppy.service import ImportService


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida reportes reales de Mercado Pago sin guardar sus datos.")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()

    with TemporaryDirectory() as temp:
        base = Path(temp)
        service = ImportService(HistoryRepository(base / "historial.db", base / "respaldos"))
        result = service.analyze(args.files, "Mensual")

    repeated_ids = Counter(item.source_id for item in result.unique_movements)
    repeated_id_rows = sum(count for count in repeated_ids.values() if count > 1)
    print(f"Archivos: {len(args.files)}")
    print(f"Filas leidas: {result.total_rows}")
    print(f"Movimientos validos: {len(result.unique_movements)}")
    print(f"Filas para revisar: {len(result.issues)}")
    print(f"Duplicados exactos: {result.duplicate_count}")
    print(f"Filas con ID compartido: {repeated_id_rows}")
    print(f"Entradas: {result.entries_total}")
    print(f"Salidas: {result.exits_total}")
    print(f"Neto: {result.net_total}")

    if result.issues:
        for issue in result.issues[:20]:
            print(f"REVISAR {issue.source_file}:{issue.row_number} - {issue.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
