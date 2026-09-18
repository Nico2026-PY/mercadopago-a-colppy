from datetime import date
from decimal import Decimal
import unittest

from src.mp_colppy.app import adaptive_window_geometry, format_currency, runtime_asset_path


class AppHelperTests(unittest.TestCase):
    def test_formats_argentine_currency(self):
        self.assertEqual(format_currency(Decimal("1234567.89")), "$ 1.234.567,89")
        self.assertEqual(format_currency(Decimal("-5000")), "-$ 5.000,00")

    def test_adapts_and_centers_window_without_maximizing(self):
        self.assertEqual(adaptive_window_geometry(1366, 768), "1160x658+103+55")
        self.assertEqual(adaptive_window_geometry(1920, 1080), "1160x720+380+180")

    def test_finds_bundled_app_icon_during_development(self):
        path = runtime_asset_path("app-icon.png")
        self.assertTrue(path.is_file())
        self.assertEqual(path.name, "app-icon.png")


if __name__ == "__main__":
    unittest.main()
