from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openpyxl import Workbook

from src.mp_colppy.history import HistoryRepository
from src.mp_colppy.service import ImportService


HEADERS = [
    "ID DE OPERACIÓN EN MERCADO PAGO",
    "TIPO DE OPERACIÓN",
    "FECHA DE ORIGEN",
    "VALOR DE LA COMPRA",
    "PAGADOR",
]


def write_report(path: Path, rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


class ServiceTests(unittest.TestCase):
    def test_analysis_deduplicates_selected_files(self):
        with TemporaryDirectory() as temp:
            base = Path(temp)
            first = base / "dia1.xlsx"
            second = base / "dia1_copia.xlsx"
            row = [101, "Pago aprobado", "2026-09-01T10:00:00-03:00", 1000, "Ana"]
            write_report(first, [row])
            write_report(second, [row])
            service = ImportService(HistoryRepository(base / "historial.db", base / "respaldos"))

            result = service.analyze([first, second], "Diario")

        self.assertEqual(len(result.unique_movements), 1)
        self.assertEqual(len(result.new_movements), 1)
        self.assertEqual(result.duplicate_count, 1)
        self.assertEqual(result.net_total, 1000)

    def test_analysis_excludes_previously_confirmed_movement(self):
        with TemporaryDirectory() as temp:
            base = Path(temp)
            daily = base / "diario.xlsx"
            monthly = base / "mensual.xlsx"
            row = [101, "Pago aprobado", "2026-09-01T10:00:00-03:00", 1000, "Ana"]
            write_report(daily, [row])
            write_report(monthly, [row, [102, "Pago aprobado", "2026-09-02T10:00:00-03:00", 2000, "Luis"]])
            repo = HistoryRepository(base / "historial.db", base / "respaldos")
            service = ImportService(repo)
            daily_result = service.analyze([daily], "Diario")
            service.confirm_import(daily_result, base / "importado_diario.xlsx")

            monthly_result = service.analyze([monthly], "Mensual")

        self.assertEqual(len(monthly_result.already_imported), 1)
        self.assertEqual(len(monthly_result.new_movements), 1)
        self.assertEqual(monthly_result.new_movements[0].source_id, "102")


if __name__ == "__main__":
    unittest.main()
