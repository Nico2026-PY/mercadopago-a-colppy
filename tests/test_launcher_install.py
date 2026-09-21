from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import launcher
from src.mp_colppy.updater import UpdateError


class LauncherInstallTests(unittest.TestCase):
    def test_local_root_uses_windows_local_appdata(self):
        with TemporaryDirectory() as temp:
            with patch.dict("os.environ", {"LOCALAPPDATA": temp}, clear=False):
                local_root = getattr(launcher, "local_app_root", None)
                self.assertIsNotNone(local_root, "Falta la raíz local del instalador")
                self.assertEqual(local_root(), Path(temp) / "MercadoPagoColppy")

    def test_installed_launch_failure_reaches_launcher_error_handler(self):
        with TemporaryDirectory() as temp:
            launcher_type = getattr(launcher, "LauncherApp", None)
            self.assertIsNotNone(launcher_type, "Falta el launcher instalador")
            app = object.__new__(launcher_type)
            app.app_root = Path(temp)

            with self.assertLogs(level="ERROR") as captured:
                with self.assertRaisesRegex(UpdateError, "versión instalada"):
                    app._launch_installed()

        self.assertTrue(any("aplicación instalada" in line for line in captured.output))


if __name__ == "__main__":
    unittest.main()
