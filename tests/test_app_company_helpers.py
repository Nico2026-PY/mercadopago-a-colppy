import unittest

from src.mp_colppy.app import company_id_for_name, company_names, require_selected_company
from src.mp_colppy.companies import Company, CompanyConfig


class AppCompanyHelperTests(unittest.TestCase):
    def setUp(self):
        self.first = Company("a" * 32, "Empresa Uno")
        self.second = Company("b" * 32, "Empresa Dos")
        self.config = CompanyConfig((self.first, self.second), self.second.id)

    def test_company_names_preserve_local_display_order(self):
        self.assertEqual(company_names(self.config), ("Empresa Uno", "Empresa Dos"))

    def test_company_id_is_resolved_from_display_name(self):
        self.assertEqual(company_id_for_name(self.config, "Empresa Uno"), self.first.id)
        self.assertIsNone(company_id_for_name(self.config, "No existe"))

    def test_selected_company_is_required(self):
        self.assertEqual(require_selected_company(self.config), self.second)
        with self.assertRaisesRegex(ValueError, "empresa"):
            require_selected_company(CompanyConfig())


if __name__ == "__main__":
    unittest.main()
