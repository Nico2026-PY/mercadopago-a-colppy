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
            "release/Launcher.exe",
            "release/MercadoPagoColppy-Windows.zip",
            "release/SHA256SUMS.txt",
            "git push origin $tag",
            "gh release list",
            "gh release",
        ):
            self.assertIn(required_text, workflow)
        self.assertNotIn("gh release view", workflow)

    def test_application_icon_is_valid_and_bundled_in_both_executables(self):
        png = (PROJECT_ROOT / "assets" / "app-icon.png").read_bytes()
        ico = (PROJECT_ROOT / "assets" / "app-icon.ico").read_bytes()
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(ico.startswith(b"\x00\x00\x01\x00"))
        for spec_name in ("MercadoPagoColppy.spec", "MercadoPagoColppyLauncher.spec"):
            spec = (PROJECT_ROOT / spec_name).read_text(encoding="utf-8")
            self.assertIn('("assets/app-icon.png", "assets")', spec)
            self.assertIn('icon=["assets/app-icon.ico"]', spec)

    def test_packaging_script_uses_an_explicit_release_allowlist(self):
        script = (PROJECT_ROOT / "scripts" / "package_portable.ps1").read_text(encoding="utf-8")
        for filename in (
            "MercadoPagoColppy.exe",
            "MercadoPagoColppyLauncher.exe",
            "Launcher.exe",
            "version.json",
        ):
            self.assertIn(filename, script)
        self.assertIn('$AllowedFiles = @(\n    "MercadoPagoColppy.exe",\n    "version.json"\n)', script)
        self.assertNotIn('"MercadoPagoColppyLauncher.exe",\n    "version.json"', script)
        self.assertNotIn("LEEME.txt", script)
        for forbidden in ("datos", "salidas", "respaldos"):
            self.assertNotIn(f'New-Item -ItemType Directory -Force -Path (Join-Path $PortableRoot "{forbidden}")', script)


if __name__ == "__main__":
    unittest.main()
