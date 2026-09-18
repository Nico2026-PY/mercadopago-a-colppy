import json
from pathlib import Path
import unittest

from src.mp_colppy.version import __version__


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ReleaseContractTests(unittest.TestCase):
    def test_version_manifest_matches_application_version(self):
        manifest = json.loads((PROJECT_ROOT / "version.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], __version__)

    def test_local_and_financial_files_are_ignored(self):
        patterns = set((PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())
        required = {"datos/", "salidas/", "respaldos/", "*.db", "*.xlsx", "*.xls", "*.csv"}
        self.assertTrue(required.issubset(patterns), required - patterns)

    def test_windows_release_builds_both_executables(self):
        self.assertTrue((PROJECT_ROOT / "MercadoPagoColppy.spec").is_file())
        self.assertTrue((PROJECT_ROOT / "MercadoPagoColppyLauncher.spec").is_file())
        workflow = (PROJECT_ROOT / ".github" / "workflows" / "build-windows.yml").read_text(encoding="utf-8")
        for required_text in (
            "contents: write",
            "branches: [main]",
            "tags:",
            'python-version: "3.14"',
            "MercadoPagoColppy.spec",
            "MercadoPagoColppyLauncher.spec",
            "git push origin $tag",
            "gh release",
        ):
            self.assertIn(required_text, workflow)

    def test_packaging_script_uses_an_explicit_release_allowlist(self):
        script = (PROJECT_ROOT / "scripts" / "package_portable.ps1").read_text(encoding="utf-8")
        for filename in (
            "MercadoPagoColppy.exe",
            "MercadoPagoColppyLauncher.exe",
            "version.json",
            "LEEME.txt",
        ):
            self.assertIn(filename, script)
        for forbidden in ("datos", "salidas", "respaldos"):
            self.assertNotIn(f'New-Item -ItemType Directory -Force -Path (Join-Path $PortableRoot "{forbidden}")', script)


if __name__ == "__main__":
    unittest.main()
