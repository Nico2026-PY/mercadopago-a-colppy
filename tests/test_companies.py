from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.mp_colppy.companies import CompanyConfigError, CompanyConfigRepository


class CompanyConfigTests(unittest.TestCase):
    def test_first_load_is_empty_and_does_not_create_real_company_names(self):
        with TemporaryDirectory() as temp:
            repo = CompanyConfigRepository(Path(temp) / "config.json")

            config = repo.load()

            self.assertEqual(config.companies, ())
            self.assertIsNone(config.selected_company_id)

    def test_add_trims_name_persists_company_and_selects_first(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            repo = CompanyConfigRepository(path)

            saved = repo.add("  Empresa de prueba  ")
            loaded = CompanyConfigRepository(path).load()

            self.assertEqual(saved, loaded)
            self.assertEqual(loaded.companies[0].name, "Empresa de prueba")
            self.assertRegex(loaded.companies[0].id, r"^[a-f0-9]{32}$")
            self.assertEqual(loaded.selected_company_id, loaded.companies[0].id)

    def test_duplicate_names_are_rejected_case_insensitively(self):
        with TemporaryDirectory() as temp:
            repo = CompanyConfigRepository(Path(temp) / "config.json")
            repo.add("Empresa Uno")

            with self.assertRaisesRegex(ValueError, "Ya existe"):
                repo.add(" empresa uno ")

    def test_rename_preserves_id_and_selection(self):
        with TemporaryDirectory() as temp:
            repo = CompanyConfigRepository(Path(temp) / "config.json")
            original = repo.add("Nombre inicial").companies[0]

            config = repo.rename(original.id, "Nombre actualizado")

            self.assertEqual(config.companies[0].id, original.id)
            self.assertEqual(config.companies[0].name, "Nombre actualizado")
            self.assertEqual(config.selected_company_id, original.id)

    def test_select_persists_selected_company(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            repo = CompanyConfigRepository(path)
            first = repo.add("Primera").companies[0]
            second = repo.add("Segunda").companies[1]

            repo.select(second.id)

            self.assertEqual(CompanyConfigRepository(path).load().selected_company_id, second.id)
            self.assertNotEqual(first.id, second.id)

    def test_malformed_configuration_reports_a_clear_error(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text("{not-json", encoding="utf-8")

            with self.assertRaisesRegex(CompanyConfigError, "configuración"):
                CompanyConfigRepository(path).load()


if __name__ == "__main__":
    unittest.main()
