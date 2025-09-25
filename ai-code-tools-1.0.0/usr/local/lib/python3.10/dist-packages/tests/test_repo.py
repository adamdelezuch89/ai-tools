import os
import shutil
import subprocess
import sys
import unittest
import logging
from io import StringIO
from unittest.mock import patch, MagicMock

from ai_tools_lib import repo, helpers

class TestDumpRepo(unittest.TestCase):

    def setUp(self):
        """Tworzy tymczasową strukturę katalogów i repozytorium Git do testów."""
        self.test_dir = os.path.abspath("test_project_repo")
        os.makedirs(os.path.join(self.test_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, ".venv/lib"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "node_modules/some-lib"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, ".github/workflows"), exist_ok=True)

        with open(os.path.join(self.test_dir, helpers.CONFIG_FILENAME), "w") as f:
            f.write("""
output_dir: .dump-outputs
blacklisted_paths:
  - ".venv/"
  - "*.lock"
whitelisted_paths:
  - ".github/workflows/main.yaml"
""")
        with open(os.path.join(self.test_dir, "src/main.py"), "w") as f: f.write("print('hello')\n# line 2")
        with open(os.path.join(self.test_dir, "package.json"), "w") as f: f.write("{}")
        with open(os.path.join(self.test_dir, "node_modules/some-lib/index.js"), "w") as f: f.write("// lib")
        with open(os.path.join(self.test_dir, ".venv/lib/a.py"), "w") as f: f.write("# venv file")
        with open(os.path.join(self.test_dir, "yarn.lock"), "w") as f: f.write("lock file")
        with open(os.path.join(self.test_dir, ".github/workflows/main.yaml"), "w") as f: f.write("name: CI")

        subprocess.run(["git", "init"], cwd=self.test_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(os.path.join(self.test_dir, ".gitignore"), "w") as f:
            f.write("node_modules/\n")

        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        self.log_stream = StringIO()
        self.logger = logging.getLogger('ai_tools')
        self.stream_handler = logging.StreamHandler(self.log_stream)
        self.logger.addHandler(self.stream_handler)

    def tearDown(self):
        self.logger.removeHandler(self.stream_handler)
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_dump_repo_respects_all_ignores(self):
        """Testuje, czy dump-repo ignoruje pliki z .gitignore, blacklisty i czy uwzględnia whitelistę."""
        with patch.object(sys, 'argv', ['dump-repo']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        logs = self.log_stream.getvalue()

        # Oczekujemy 3 plików: src/main.py, package.json, i whitelisted .github/workflows/main.yaml
        self.assertIn("Znaleziono 3 plików do przetworzenia (łącznie 4 linii kodu)", logs)
        self.assertIn("File: src/main.py", output)
        self.assertIn("File: package.json", output)
        self.assertIn("File: .github/workflows/main.yaml", output)

        # Sprawdzamy, czy pliki są poprawnie ignorowane/blacklistowane
        self.assertNotIn("File: node_modules/some-lib/index.js", output) # .gitignore
        self.assertNotIn("File: .venv/lib/a.py", output) # blacklisted
        self.assertNotIn("File: yarn.lock", output) # blacklisted
        self.assertNotIn("File: .gitignore", output) # domyślnie blacklisted

    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_dump_specific_directory(self):
        """Testuje dumpowanie tylko określonego katalogu."""
        with patch.object(sys, 'argv', ['dump-repo', 'src']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        logs = self.log_stream.getvalue()

        # W zakresie 'src' powinien być tylko jeden plik
        self.assertIn("Znaleziono 1 plików do przetworzenia (łącznie 2 linii kodu)", logs)
        self.assertIn("File: src/main.py", output)

        # Pliki poza zakresem 'src' nie powinny być w zrzucie
        self.assertNotIn("File: package.json", output)
        self.assertNotIn("File: .github/workflows/main.yaml", output)

if __name__ == '__main__':
    unittest.main()