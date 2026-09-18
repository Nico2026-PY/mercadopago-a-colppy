from io import BytesIO
import json
from urllib.error import URLError
import unittest

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


if __name__ == "__main__":
    unittest.main()
