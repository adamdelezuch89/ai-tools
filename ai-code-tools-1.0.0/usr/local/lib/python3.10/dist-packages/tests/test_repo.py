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

        # Podstawowa konfiguracja (będzie modyfikowana w poszczególnych testach)
        with open(os.path.join(self.test_dir, helpers.CONFIG_FILENAME), "w") as f:
            f.write("""
output_dir: .dump-outputs
blacklisted_paths:
  - ".venv/"
  - "*.lock"
whitelisted_paths:
  - ".github/workflows/main.yaml"
""")
        
        # Podstawowe pliki
        with open(os.path.join(self.test_dir, "src/main.py"), "w") as f: 
            f.write("print('hello')\n# line 2")
        with open(os.path.join(self.test_dir, "package.json"), "w") as f: 
            f.write("{}")
        with open(os.path.join(self.test_dir, "node_modules/some-lib/index.js"), "w") as f: 
            f.write("// lib")
        with open(os.path.join(self.test_dir, ".venv/lib/a.py"), "w") as f: 
            f.write("# venv file")
        with open(os.path.join(self.test_dir, "yarn.lock"), "w") as f: 
            f.write("lock file")
        with open(os.path.join(self.test_dir, ".github/workflows/main.yaml"), "w") as f: 
            f.write("name: CI")

        # Inicjalizacja repo git
        subprocess.run(["git", "init"], cwd=self.test_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(os.path.join(self.test_dir, ".gitignore"), "w") as f:
            f.write("node_modules/\n")
        
        subprocess.run(["git", "add", ".gitignore"], cwd=self.test_dir, stdout=subprocess.DEVNULL)

        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Przechwytywanie logów
        self.log_stream = StringIO()
        self.stream_handler = logging.StreamHandler(self.log_stream)
        self.logger_to_capture = logging.getLogger('ai_tools')
        self.logger_to_capture.addHandler(self.stream_handler)
        self.repo_logger = logging.getLogger('ai_tools.repo')
        self.repo_logger.addHandler(self.stream_handler)
        self.logger_to_capture.setLevel(logging.INFO)
        self.repo_logger.setLevel(logging.INFO)

    def tearDown(self):
        self.logger_to_capture.removeHandler(self.stream_handler)
        self.repo_logger.removeHandler(self.stream_handler)
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _write_config(self, config_content):
        """Pomocnicza funkcja do nadpisywania konfiguracji."""
        with open(os.path.join(self.test_dir, helpers.CONFIG_FILENAME), "w") as f:
            f.write(config_content)

    # TEST 1: Pliki są gitignored - nie powinny być w dumpie
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_gitignored_files_excluded(self):
        """Testuje, czy pliki z .gitignore są wykluczane z dumpu."""
        # node_modules jest w .gitignore
        with patch.object(sys, 'argv', ['dump-repo']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        
        # node_modules/some-lib/index.js powinien być wykluczony
        self.assertNotIn("File: node_modules/some-lib/index.js", output)
        # Ale inne pliki powinny być
        self.assertIn("File: src/main.py", output)
        self.assertIn("File: package.json", output)

    # TEST 2: Pliki nie są gitignored, ale są w blacklisted - nie powinny być w dumpie
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_blacklisted_files_excluded(self):
        """Testuje, czy pliki z blacklist są wykluczane z dumpu."""
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - ".venv/"
  - "*.lock"
  - "src/"
whitelisted_paths: []
""")
        
        with patch.object(sys, 'argv', ['dump-repo']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        
        # src/ jest w blacklist, więc src/main.py nie powinno być
        self.assertNotIn("File: src/main.py", output)
        # .venv jest w blacklist
        self.assertNotIn("File: .venv/lib/a.py", output)
        # *.lock jest w blacklist
        self.assertNotIn("File: yarn.lock", output)
        # Ale package.json powinien być
        self.assertIn("File: package.json", output)

    # TEST 2b: Blacklist bez ukośników na końcu
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_blacklisted_directories_without_slash(self):
        """Testuje, czy katalogi w blacklist działają bez ukośnika na końcu."""
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - ".venv"
  - "src"
whitelisted_paths: []
""")
        
        # Dodaj plik src do gita, żeby był widoczny
        subprocess.run(["git", "add", "src/main.py"], cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        with patch.object(sys, 'argv', ['dump-repo']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        
        # src (bez ukośnika) powinno też wykluczyć src/main.py
        self.assertNotIn("File: src/main.py", output)
        self.assertNotIn("File: .venv/lib/a.py", output)

    # TEST 3: Pliki są gitignored, ale są whitelisted - powinny być w dumpie
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_gitignored_but_whitelisted_files_included(self):
        """Testuje, czy pliki gitignored ale whitelisted są w dumpie."""
        # .github/workflows/main.yaml jest whitelisted mimo że może być ignorowany
        with patch.object(sys, 'argv', ['dump-repo']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        
        # .github/workflows/main.yaml jest whitelisted
        self.assertIn("File: .github/workflows/main.yaml", output)

    # TEST 3b: Katalog gitignored, ale whitelisted
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_gitignored_directory_but_whitelisted_included(self):
        """Testuje, czy cały katalog gitignored ale whitelisted jest w dumpie."""
        # Dodaj plik do node_modules
        with open(os.path.join(self.test_dir, "node_modules/important.js"), "w") as f:
            f.write("// important file")
        
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths: []
whitelisted_paths:
  - "node_modules/"
""")
        
        with patch.object(sys, 'argv', ['dump-repo']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        
        # node_modules jest whitelisted mimo .gitignore
        self.assertIn("File: node_modules/important.js", output)
        self.assertIn("File: node_modules/some-lib/index.js", output)

    # TEST 4: Pliki są w obu listach - błąd/ostrzeżenie
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_conflicting_whitelist_blacklist_warning(self):
        """Testuje, czy konflikt między whitelist i blacklist generuje ostrzeżenie."""
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - "src/"
whitelisted_paths:
  - "src/"
""")
        
        subprocess.run(["git", "add", "src/main.py"], cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        # Oczekujemy SystemExit, bo log_error() kończy program
        with self.assertRaises(SystemExit) as cm:
            with patch.object(sys, 'argv', ['dump-repo']):
                repo.main()
        
        # Sprawdź kod wyjścia
        self.assertEqual(cm.exception.code, 1)
        
        logs = self.log_stream.getvalue()
        
        # Sprawdzamy czy jest błąd o konflikcie
        self.assertTrue(
            'konflikt' in logs.lower() or 'conflict' in logs.lower() or 
            'nieprawidłow' in logs.lower() or 'invalid' in logs.lower() or
            'błąd' in logs.lower() or 'error' in logs.lower(),
            f"Brak ostrzeżenia o konflikcie w logach. Logi:\n{logs}"
        )

    # TEST 4b: Konflikt z różnymi formatami (z/bez ukośnika)
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_conflicting_whitelist_blacklist_different_formats(self):
        """Testuje konflikt między whitelist i blacklist z różnymi formatami."""
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - "src"
whitelisted_paths:
  - "src/"
""")
        
        subprocess.run(["git", "add", "src/main.py"], cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        # Oczekujemy SystemExit, bo log_error() kończy program
        with self.assertRaises(SystemExit) as cm:
            with patch.object(sys, 'argv', ['dump-repo']):
                repo.main()
        
        # Sprawdź kod wyjścia
        self.assertEqual(cm.exception.code, 1)
        
        logs = self.log_stream.getvalue()
        
        # Sprawdzamy czy jest błąd o konflikcie
        # Powinno być wykryte, że "src" i "src/" to ten sam katalog
        self.assertTrue(
            'konflikt' in logs.lower() or 'conflict' in logs.lower() or 
            'nieprawidłow' in logs.lower() or 'invalid' in logs.lower() or
            'błąd' in logs.lower() or 'error' in logs.lower(),
            f"Brak ostrzeżenia o konflikcie w logach. Logi:\n{logs}"
        )

    # TEST 5: Ścieżka whitelisted, ale zagnieżdżona blacklisted
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_whitelisted_parent_blacklisted_child(self):
        """Testuje whitelisted katalog z blacklisted podkatalogiem."""
        # Tworzymy strukturę: docs/ (whitelisted) z docs/internal/ (blacklisted)
        os.makedirs(os.path.join(self.test_dir, "docs/internal"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "docs/public"), exist_ok=True)
        
        with open(os.path.join(self.test_dir, "docs/README.md"), "w") as f:
            f.write("# Public docs")
        with open(os.path.join(self.test_dir, "docs/internal/secret.md"), "w") as f:
            f.write("# Secret")
        with open(os.path.join(self.test_dir, "docs/public/guide.md"), "w") as f:
            f.write("# Guide")
        
        # Dodaj do .gitignore całe docs/
        with open(os.path.join(self.test_dir, ".gitignore"), "a") as f:
            f.write("docs/\n")
        
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - "docs/internal/"
whitelisted_paths:
  - "docs/"
""")
        
        with patch.object(sys, 'argv', ['dump-repo']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        
        # docs/ jest whitelisted, więc pliki z docs/ powinny być
        self.assertIn("File: docs/README.md", output)
        self.assertIn("File: docs/public/guide.md", output)
        # Ale docs/internal/ jest blacklisted
        self.assertNotIn("File: docs/internal/secret.md", output)

    # TEST 6: Ścieżka blacklisted, ale zagnieżdżona whitelisted
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_blacklisted_parent_whitelisted_child(self):
        """Testuje blacklisted katalog z whitelisted podkatalogiem."""
        # Tworzymy strukturę: build/ (blacklisted) z build/important/ (whitelisted)
        os.makedirs(os.path.join(self.test_dir, "build/cache"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "build/important"), exist_ok=True)
        
        with open(os.path.join(self.test_dir, "build/output.js"), "w") as f:
            f.write("// build output")
        with open(os.path.join(self.test_dir, "build/cache/temp.js"), "w") as f:
            f.write("// temp")
        with open(os.path.join(self.test_dir, "build/important/config.js"), "w") as f:
            f.write("// important config")
        
        subprocess.run(["git", "add", "-f", "build/"], cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - "build/"
whitelisted_paths:
  - "build/important/"
""")
        
        with patch.object(sys, 'argv', ['dump-repo']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        
        # build/ jest blacklisted, więc większość plików z build/ nie powinna być
        self.assertNotIn("File: build/output.js", output)
        self.assertNotIn("File: build/cache/temp.js", output)
        # Ale build/important/ jest whitelisted
        self.assertIn("File: build/important/config.js", output)

    # TEST 6b: Złożony przypadek - wielopoziomowe zagnieżdżenie
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_complex_nested_whitelist_blacklist(self):
        """Testuje złożone zagnieżdżenie whitelist/blacklist."""
        # Struktura:
        # vendor/ (blacklisted)
        #   ├── vendor/libs/ (whitelisted)
        #   │   └── vendor/libs/node_modules/ (blacklisted)
        #   └── vendor/other/
        
        os.makedirs(os.path.join(self.test_dir, "vendor/libs/node_modules"), exist_ok=True)
        os.makedirs(os.path.join(self.test_dir, "vendor/other"), exist_ok=True)
        
        with open(os.path.join(self.test_dir, "vendor/readme.txt"), "w") as f:
            f.write("vendor readme")
        with open(os.path.join(self.test_dir, "vendor/libs/important.js"), "w") as f:
            f.write("important lib")
        with open(os.path.join(self.test_dir, "vendor/libs/node_modules/dep.js"), "w") as f:
            f.write("dependency")
        with open(os.path.join(self.test_dir, "vendor/other/stuff.js"), "w") as f:
            f.write("other stuff")
        
        subprocess.run(["git", "add", "-f", "vendor/"], cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - "vendor/"
  - "vendor/libs/node_modules/"
whitelisted_paths:
  - "vendor/libs/"
""")
        
        with patch.object(sys, 'argv', ['dump-repo']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        
        # vendor/ jest blacklisted
        self.assertNotIn("File: vendor/readme.txt", output)
        self.assertNotIn("File: vendor/other/stuff.js", output)
        # vendor/libs/ jest whitelisted
        self.assertIn("File: vendor/libs/important.js", output)
        # vendor/libs/node_modules/ jest blacklisted
        self.assertNotIn("File: vendor/libs/node_modules/dep.js", output)

    # BONUS TEST: Sprawdzenie czy .gitignore sam nie jest dumpowany
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_gitignore_file_itself_excluded(self):
        """Testuje, czy sam plik .gitignore nie jest dumpowany."""
        with patch.object(sys, 'argv', ['dump-repo']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        
        # .gitignore nie powinien być w dumpie
        self.assertNotIn("File: .gitignore", output)

    # BONUS TEST: Wildcardy w blacklist
    @patch('ai_tools_lib.repo.pyperclip', MagicMock())
    def test_wildcard_patterns_in_blacklist(self):
        """Testuje, czy wzorce wildcard w blacklist działają poprawnie."""
        os.makedirs(os.path.join(self.test_dir, "logs"), exist_ok=True)
        
        with open(os.path.join(self.test_dir, "app.log"), "w") as f:
            f.write("log content")
        with open(os.path.join(self.test_dir, "logs/debug.log"), "w") as f:
            f.write("debug log")
        with open(os.path.join(self.test_dir, "config.txt"), "w") as f:
            f.write("config")
        
        subprocess.run(["git", "add", "-f", "*.log", "logs/", "config.txt"], 
                      cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - "*.log"
whitelisted_paths: []
""")
        
        with patch.object(sys, 'argv', ['dump-repo']):
            result_code = repo.main()
            self.assertEqual(result_code, 0)

        output = repo.pyperclip.copy.call_args[0][0]
        
        # Wszystkie pliki .log powinny być wykluczone
        self.assertNotIn("File: app.log", output)
        self.assertNotIn("File: logs/debug.log", output)
        # Ale config.txt powinien być
        self.assertIn("File: config.txt", output)


# --- POCZĄTEK BLOKU DO URUCHAMIANIA TESTÓW Z LOGOWANIEM ---
if __name__ == '__main__':
    # Konfiguruje logowanie tak, aby WSZYSTKIE komunikaty na poziomie INFO i wyższym
    # były drukowane w konsoli podczas uruchamiania tego pliku.
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        stream=sys.stdout
    )
    unittest.main()
# --- KONIEC BLOKU ---
