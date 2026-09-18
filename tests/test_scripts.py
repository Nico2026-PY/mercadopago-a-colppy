from pathlib import Path
import subprocess
import sys
import unittest


class ScriptTests(unittest.TestCase):
    def test_validation_script_runs_from_project_root(self):
        project_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "scripts/validate_real_files.py", "--help"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Valida reportes reales", result.stdout)


if __name__ == "__main__":
    unittest.main()
