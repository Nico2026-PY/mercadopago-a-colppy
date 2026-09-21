from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.mp_colppy.paths import resolve_app_paths


class PathTests(unittest.TestCase):
    def test_launcher_home_keeps_company_data_outside_installed_version(self):
        with TemporaryDirectory() as temp:
            home = Path(temp) / "MercadoPagoColppy"
            executable = home / "versions" / "v1.0.1" / "MercadoPagoColppy.exe"
            with patch.dict("os.environ", {"MP_COLPPY_HOME": str(home)}, clear=False):
                paths = resolve_app_paths(executable=executable, frozen=True)

            self.assertEqual(paths.root, home.resolve())
            self.assertEqual(paths.config, home.resolve() / "datos" / "config.json")
            self.assertNotIn("versions", paths.database.parts)

    def test_frozen_app_uses_executable_folder(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            paths = resolve_app_paths(executable=root / "MercadoPagoColppy.exe", frozen=True)
            expected_root = root.resolve()

            self.assertEqual(paths.root, expected_root)
            self.assertEqual(paths.database, expected_root / "datos" / "historial.db")
            self.assertEqual(paths.outputs, expected_root / "salidas")
            self.assertEqual(paths.backups, expected_root / "respaldos")
            self.assertTrue(paths.outputs.is_dir())

    def test_source_app_can_use_explicit_project_root(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / "proyecto"
            paths = resolve_app_paths(frozen=False, source_root=root)

            self.assertEqual(paths.root, root.resolve())
            self.assertTrue(paths.data.is_dir())

    def test_company_paths_are_isolated(self):
        with TemporaryDirectory() as temp:
            paths = resolve_app_paths(frozen=False, source_root=Path(temp))

            first = paths.for_company("company-a")
            second = paths.for_company("company-b")

            self.assertNotEqual(first.database, second.database)
            self.assertEqual(first.database, paths.data / "empresas" / "company-a" / "historial.db")
            self.assertEqual(first.outputs, paths.outputs / "company-a")
            self.assertEqual(first.backups, paths.backups / "company-a")
            self.assertTrue(first.outputs.is_dir())
            self.assertTrue(first.backups.is_dir())

    def test_company_id_cannot_escape_portable_directories(self):
        with TemporaryDirectory() as temp:
            paths = resolve_app_paths(frozen=False, source_root=Path(temp))

            with self.assertRaisesRegex(ValueError, "identificador"):
                paths.for_company("../outside")


if __name__ == "__main__":
    unittest.main()
