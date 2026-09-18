from datetime import date
from decimal import Decimal
import unittest

from src.mp_colppy.app import format_currency, suggested_filename


class AppHelperTests(unittest.TestCase):
    def test_formats_argentine_currency(self):
        self.assertEqual(format_currency(Decimal("1234567.89")), "$ 1.234.567,89")
        self.assertEqual(format_currency(Decimal("-5000")), "-$ 5.000,00")

    def test_suggests_name_from_mode_and_date_range(self):
        name = suggested_filename("Mensual", date(2026, 9, 1), date(2026, 9, 30), ".xlsx")
        self.assertEqual(name, "Colppy_MP_Mensual_2026-09-01_a_2026-09-30.xlsx")


if __name__ == "__main__":
    unittest.main()
