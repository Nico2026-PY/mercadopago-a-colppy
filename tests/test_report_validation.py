from datetime import date
from pathlib import Path
import unittest

from src.mp_colppy.companies import Company
from src.mp_colppy.report_validation import classify_period, detect_company_from_paths, output_filename


class CompanyDetectionTests(unittest.TestCase):
    def setUp(self):
        self.first = Company("a" * 32, "Compañía Norte")
        self.second = Company("b" * 32, "Empresa Dos")
        self.companies = (self.first, self.second)

    def test_detects_company_from_filename_ignoring_accents_and_case(self):
        result = detect_company_from_paths(
            [Path("MP COMPANIA NORTE DIARIO 18-09-2026.xlsx")],
            self.companies,
        )

        self.assertEqual(result.status, "matched")
        self.assertEqual(result.company_id, self.first.id)

    def test_reports_mixed_companies_in_one_selection(self):
        result = detect_company_from_paths(
            [Path("MP Compañía Norte 09-2026.csv"), Path("MP Empresa Dos 09-2026.xls")],
            self.companies,
        )

        self.assertEqual(result.status, "mixed")
        self.assertIsNone(result.company_id)

    def test_reports_unknown_when_no_configured_company_is_in_filename(self):
        result = detect_company_from_paths([Path("reporte_mercadopago.xlsx")], self.companies)

        self.assertEqual(result.status, "unknown")
        self.assertIsNone(result.company_id)


class PeriodClassificationTests(unittest.TestCase):
    def test_one_calendar_day_is_daily(self):
        result = classify_period([date(2026, 9, 18), date(2026, 9, 18)])

        self.assertEqual(result.mode, "Diario")
        self.assertIsNone(result.error)

    def test_multiple_days_in_one_month_are_monthly(self):
        result = classify_period([date(2026, 9, 1), date(2026, 9, 30)])

        self.assertEqual(result.mode, "Mensual")
        self.assertIsNone(result.error)

    def test_multiple_months_are_blocked(self):
        result = classify_period([date(2026, 8, 31), date(2026, 9, 1)])

        self.assertIsNone(result.mode)
        self.assertIn("más de un mes", result.error or "")


class OutputFilenameTests(unittest.TestCase):
    def test_daily_name_uses_company_and_full_date(self):
        self.assertEqual(
            output_filename("Compañía Norte", "Diario", date(2026, 9, 18), date(2026, 9, 18)),
            "MP Compañía Norte DIARIO 18-09-2026.csv",
        )

    def test_monthly_name_uses_company_month_and_year(self):
        self.assertEqual(
            output_filename("Compañía Norte", "Mensual", date(2026, 9, 1), date(2026, 9, 30)),
            "MP Compañía Norte MENSUAL 09-2026.csv",
        )


if __name__ == "__main__":
    unittest.main()
