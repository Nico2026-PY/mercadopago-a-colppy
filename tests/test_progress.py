from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openpyxl import Workbook

from src.mp_colppy.excel_io import read_mercadopago_files


HEADERS = [
    "ID DE OPERACIÓN EN MERCADO PAGO",
    "TIPO DE OPERACIÓN",
    "FECHA DE ORIGEN",
    "VALOR DE LA COMPRA",
]


class ProgressTests(unittest.TestCase):
    def test_excel_analysis_reports_monotonic_progress_ending_at_100(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "reporte.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(HEADERS)
            for index in range(1, 8):
                sheet.append([index, "Pago aprobado", f"2026-09-{index:02d}", index * 100])
            workbook.save(path)
            events: list[tuple[int, str]] = []

            result = read_mercadopago_files([path], progress=lambda value, message: events.append((value, message)))

        values = [value for value, _message in events]
        self.assertEqual(len(result.movements), 7)
        self.assertTrue(events)
        self.assertEqual(values[0], 0)
        self.assertEqual(values[-1], 100)
        self.assertEqual(values, sorted(values))
        self.assertTrue(all(0 <= value <= 100 for value in values))
        self.assertTrue(all(message for _value, message in events))

    def test_empty_selection_still_completes_progress(self):
        events: list[int] = []

        result = read_mercadopago_files([], progress=lambda value, _message: events.append(value))

        self.assertEqual(result.total_rows, 0)
        self.assertEqual(events, [0, 100])


if __name__ == "__main__":
    unittest.main()
