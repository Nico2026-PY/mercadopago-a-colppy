from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError
import unittest
from zipfile import ZipFile

from src.mp_colppy import updater as updater_module
from src.mp_colppy.updater import LATEST_RELEASE_API, ReleaseInfo, fetch_latest_release, is_newer, parse_version


class _Response(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


class UpdaterTests(unittest.TestCase):
    def test_launcher_checks_the_public_project_repository(self):
        self.assertEqual(
            LATEST_RELEASE_API,
            "https://api.github.com/repos/Nico2026-PY/mercadopago-a-colppy/releases/latest",
        )

    def test_parses_semantic_release_tags(self):
        self.assertEqual(parse_version("v1.2.0"), (1, 2, 0))
        self.assertEqual(parse_version("1.2.3"), (1, 2, 3))
        with self.assertRaises(ValueError):
            parse_version("release-latest")

    def test_compares_versions(self):
        self.assertTrue(is_newer("1.2.0", "v1.3.0"))
        self.assertFalse(is_newer("1.2.0", "v1.2.0"))
        self.assertFalse(is_newer("2.0.0", "v1.9.9"))

    def test_reads_valid_github_release_response(self):
        payload = json.dumps(
            {"tag_name": "v1.4.0", "html_url": "https://github.com/example/project/releases/tag/v1.4.0"}
        ).encode("utf-8")
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["user_agent"] = request.headers.get("User-agent")
            captured["timeout"] = timeout
            return _Response(payload)

        result = fetch_latest_release("https://api.github.com/repos/example/project/releases/latest", timeout=3.5, opener=opener)

        self.assertEqual(result, ReleaseInfo("1.4.0", "https://github.com/example/project/releases/tag/v1.4.0"))
        self.assertEqual(captured["timeout"], 3.5)
        self.assertEqual(captured["user_agent"], "MercadoPagoColppy-Launcher")

    def test_network_and_malformed_responses_do_not_block_startup(self):
        def offline(_request, timeout):
            raise URLError("offline")

        def malformed(_request, timeout):
            return _Response(b"not-json")

        self.assertIsNone(fetch_latest_release("https://api.github.com/test", opener=offline))
        self.assertIsNone(fetch_latest_release("https://api.github.com/test", opener=malformed))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class InstallableReleaseTests(unittest.TestCase):
    def test_selects_exact_archive_and_checksum_assets(self):
        client_type = getattr(updater_module, "UpdateClient", None)
        self.assertIsNotNone(client_type, "Falta el cliente instalador de Releases")
        payload = {
            "tag_name": "v1.2.0",
            "assets": [
                {"name": "other.zip", "browser_download_url": "https://example.test/other"},
                {"name": "MercadoPagoColppy-Windows.zip", "browser_download_url": "https://example.test/app.zip"},
                {"name": "SHA256SUMS.txt", "browser_download_url": "https://example.test/SHA256SUMS.txt"},
            ],
        }

        def open_fixture(_request, timeout):
            return _Response(json.dumps(payload).encode("utf-8"))

        release = client_type(opener=open_fixture).latest_release()

        self.assertEqual(str(release.version), "v1.2.0")
        self.assertEqual(release.archive_url, "https://example.test/app.zip")
        self.assertEqual(release.checksum_url, "https://example.test/SHA256SUMS.txt")

    def test_verifies_expected_sha256(self):
        verify = getattr(updater_module, "verify_sha256", None)
        self.assertIsNotNone(verify, "Falta la verificación SHA-256")
        with TemporaryDirectory() as temp:
            path = Path(temp) / "release.zip"
            path.write_bytes(b"release bytes")
            verify(path, sha256(path).upper())

    def test_rejects_wrong_sha256(self):
        verify = getattr(updater_module, "verify_sha256", None)
        error_type = getattr(updater_module, "UpdateError", RuntimeError)
        self.assertIsNotNone(verify, "Falta la verificación SHA-256")
        with TemporaryDirectory() as temp:
            path = Path(temp) / "release.zip"
            path.write_bytes(b"release bytes")
            with self.assertRaisesRegex(error_type, "SHA-256"):
                verify(path, "0" * 64)

    def test_rejects_zip_traversal_before_writing_files(self):
        extract = getattr(updater_module, "safe_extract_zip", None)
        error_type = getattr(updater_module, "UpdateError", RuntimeError)
        self.assertIsNotNone(extract, "Falta la extracción segura")
        with TemporaryDirectory() as temp:
            archive = Path(temp) / "bad.zip"
            destination = Path(temp) / "out"
            with ZipFile(archive, "w") as handle:
                handle.writestr("safe.txt", "must not be extracted")
                handle.writestr("../escape.txt", "bad")
            with self.assertRaisesRegex(error_type, "ruta insegura"):
                extract(archive, destination)
            self.assertEqual(list(destination.rglob("*")), [])

    def test_rejects_windows_absolute_path_in_zip(self):
        extract = getattr(updater_module, "safe_extract_zip", None)
        error_type = getattr(updater_module, "UpdateError", RuntimeError)
        self.assertIsNotNone(extract, "Falta la extracción segura")
        with TemporaryDirectory() as temp:
            archive = Path(temp) / "bad.zip"
            with ZipFile(archive, "w") as handle:
                handle.writestr("C:/Windows/escape.txt", "bad")
            with self.assertRaisesRegex(error_type, "ruta insegura"):
                extract(archive, Path(temp) / "out")


class InstallationTests(unittest.TestCase):
    def _build_release(self, directory: Path, executable_text: str = "new") -> Path:
        archive = directory / "release.zip"
        with ZipFile(archive, "w") as handle:
            handle.writestr("MercadoPagoColppy.exe", executable_text)
            handle.writestr("version.json", '{"version":"1.1.0"}')
        return archive

    def test_installs_version_without_overwriting_local_company_data(self):
        install = getattr(updater_module, "install_release", None)
        self.assertIsNotNone(install, "Falta la instalación automática")
        with TemporaryDirectory() as temp:
            root = Path(temp) / "app"
            history = root / "datos" / "empresas" / "aguera" / "historial.db"
            history.parent.mkdir(parents=True)
            history.write_text("keep", encoding="utf-8")
            archive = self._build_release(Path(temp))

            executable = install(archive, "v1.1.0", sha256(archive), root)

            manifest = json.loads((root / "current.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], "v1.1.0")
            self.assertEqual(executable, root / "versions" / "v1.1.0" / "MercadoPagoColppy.exe")
            self.assertEqual(history.read_text(encoding="utf-8"), "keep")

    def test_failed_install_keeps_current_manifest(self):
        install = getattr(updater_module, "install_release", None)
        error_type = getattr(updater_module, "UpdateError", RuntimeError)
        self.assertIsNotNone(install, "Falta la instalación automática")
        with TemporaryDirectory() as temp:
            root = Path(temp) / "app"
            root.mkdir()
            current = root / "current.json"
            current.write_text('{"version":"v1.0.0","executable":"old.exe"}', encoding="utf-8")
            archive = self._build_release(Path(temp))
            with self.assertRaisesRegex(error_type, "SHA-256"):
                install(archive, "v1.1.0", "0" * 64, root)
            self.assertEqual(json.loads(current.read_text(encoding="utf-8"))["version"], "v1.0.0")

    @unittest.skipIf(os.name == "nt", "La prueba usa un script POSIX con extensión .exe")
    def test_launches_current_version_with_persistent_home_environment(self):
        launch = getattr(updater_module, "launch_current", None)
        self.assertIsNotNone(launch, "Falta el arranque de la versión instalada")
        with TemporaryDirectory() as temp:
            root = Path(temp) / "app"
            version = root / "versions" / "v1.0.0"
            version.mkdir(parents=True)
            executable = version / "MercadoPagoColppy.exe"
            marker = root / "launched.txt"
            executable.write_text(f"#!/bin/sh\nprintf '%s' \"$MP_COLPPY_HOME\" > '{marker}'\n", encoding="utf-8")
            executable.chmod(0o755)
            (root / "current.json").write_text(
                json.dumps({"version": "v1.0.0", "executable": str(executable)}),
                encoding="utf-8",
            )
            process = launch(root)
            self.assertEqual(process.wait(timeout=5), 0)
            self.assertEqual(marker.read_text(encoding="utf-8"), str(root.resolve()))


if __name__ == "__main__":
    unittest.main()
