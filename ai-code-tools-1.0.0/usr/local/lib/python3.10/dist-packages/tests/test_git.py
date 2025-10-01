import os
import shutil
import subprocess
import sys
import unittest
import logging
from io import StringIO
from unittest.mock import patch, MagicMock

from ai_tools_lib import git, helpers

class TestDumpGit(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.abspath("test_project_git")
        os.makedirs(self.test_dir, exist_ok=True)

        with open(os.path.join(self.test_dir, helpers.CONFIG_FILENAME), "w") as f:
            f.write("output_dir: .dump-outputs\n")

        subprocess.run(["git", "init"], cwd=self.test_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.test_dir)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir)

        with open(os.path.join(self.test_dir, "committed.txt"), "w") as f: f.write("initial content")
        subprocess.run(["git", "add", "."], cwd=self.test_dir)
        subprocess.run(["git", "commit", "-m", "initial commit"], cwd=self.test_dir, stdout=subprocess.DEVNULL)

        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # --- POPRAWKA: Konfiguracja przechwytywania logów ---
        self.log_stream = StringIO()
        self.logger = logging.getLogger('ai_tools')
        self.stream_handler = logging.StreamHandler(self.log_stream)
        self.logger.addHandler(self.stream_handler)


    def tearDown(self):
        # --- POPRAWKA: Usunięcie przechwytywarki logów ---
        self.logger.removeHandler(self.stream_handler)

        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('ai_tools_lib.git.pyperclip', MagicMock())
    def test_dump_git_staged(self):
        with open("staged.txt", "w") as f: f.write("staged content")
        subprocess.run(["git", "add", "staged.txt"], cwd=self.test_dir)

        with patch.object(sys, 'argv', ['dump-git', '--staged']):
            git.main()

        output = git.pyperclip.copy.call_args[0][0]
        self.assertIn("File: staged.txt", output)
        self.assertNotIn("File: committed.txt", output)
        
        # --- POPRAWKA: Sprawdzanie przechwyconych logów ---
        self.assertIn("Znaleziono 1 zmienionych plików do przetworzenia (łącznie 1 linii kodu)", self.log_stream.getvalue())


    @patch('ai_tools_lib.git.pyperclip', MagicMock())
    def test_dump_git_unstaged_and_untracked(self):
        with open("committed.txt", "a") as f: f.write("\nunstaged change")
        with open("untracked.txt", "w") as f: f.write("untracked file")

        with patch.object(sys, 'argv', ['dump-git', '--unstaged']):
            git.main()

        output = git.pyperclip.copy.call_args[0][0]
        self.assertIn("File: committed.txt", output)
        self.assertIn("File: untracked.txt", output)

    @patch('ai_tools_lib.git.pyperclip', MagicMock())
    def test_dump_git_all(self):
        with open("staged.txt", "w") as f: f.write("staged")
        subprocess.run(["git", "add", "staged.txt"], cwd=self.test_dir)
        with open("untracked.txt", "w") as f: f.write("untracked")
        with open("committed.txt", "a") as f: f.write("\nunstaged")

        with patch.object(sys, 'argv', ['dump-git']):
            git.main()
        
        output = git.pyperclip.copy.call_args[0][0]
        self.assertIn("File: staged.txt", output)
        self.assertIn("File: untracked.txt", output)
        self.assertIn("File: committed.txt", output)

    # NOWE TESTY DLA BLACKLIST/WHITELIST
    
    def _write_config(self, config_content):
        """Pomocnicza funkcja do nadpisywania konfiguracji."""
        with open(os.path.join(self.test_dir, helpers.CONFIG_FILENAME), "w") as f:
            f.write(config_content)

    @patch('ai_tools_lib.git.pyperclip', MagicMock())
    def test_blacklisted_changed_files_excluded(self):
        """Testuje, czy zmienione pliki z blacklist są wykluczane."""
        # Tworzymy strukturę katalogów
        os.makedirs("src", exist_ok=True)
        os.makedirs("tests", exist_ok=True)
        
        with open("src/app.py", "w") as f: f.write("app code")
        with open("tests/test.py", "w") as f: f.write("test code")
        
        subprocess.run(["git", "add", "."], cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        # Konfiguracja z blacklist
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - "tests/"
""")
        
        with patch.object(sys, 'argv', ['dump-git', '--staged']):
            git.main()
        
        output = git.pyperclip.copy.call_args[0][0]
        
        # src/app.py powinno być w dumpie
        self.assertIn("File: src/app.py", output)
        # tests/test.py jest blacklisted
        self.assertNotIn("File: tests/test.py", output)

    @patch('ai_tools_lib.git.pyperclip', MagicMock())
    def test_blacklisted_without_slash(self):
        """Testuje blacklist bez ukośnika na końcu."""
        os.makedirs("build", exist_ok=True)
        
        with open("build/output.js", "w") as f: f.write("build output")
        with open("main.js", "w") as f: f.write("main code")
        
        subprocess.run(["git", "add", "."], cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - "build"
""")
        
        with patch.object(sys, 'argv', ['dump-git', '--staged']):
            git.main()
        
        output = git.pyperclip.copy.call_args[0][0]
        
        self.assertIn("File: main.js", output)
        self.assertNotIn("File: build/output.js", output)

    @patch('ai_tools_lib.git.pyperclip', MagicMock())
    def test_whitelisted_in_gitignored(self):
        """Testuje whitelist dla plików które byłyby zignorowane."""
        # Ten test jest trochę inny dla git - pliki które są zmienione
        # są już poza .gitignore, więc testujemy po prostu whitelist
        os.makedirs("logs", exist_ok=True)
        os.makedirs("important", exist_ok=True)
        
        with open("logs/debug.log", "w") as f: f.write("debug")
        with open("important/config.json", "w") as f: f.write("{}")
        
        subprocess.run(["git", "add", "-f", "."], cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - "*.log"
whitelisted_paths:
  - "important/"
""")
        
        with patch.object(sys, 'argv', ['dump-git', '--staged']):
            git.main()
        
        output = git.pyperclip.copy.call_args[0][0]
        
        self.assertIn("File: important/config.json", output)
        self.assertNotIn("File: logs/debug.log", output)

    @patch('ai_tools_lib.git.pyperclip', MagicMock())
    def test_blacklisted_parent_whitelisted_child(self):
        """Testuje blacklisted katalog z whitelisted podkatalogiem."""
        os.makedirs("vendor/libs", exist_ok=True)
        os.makedirs("vendor/other", exist_ok=True)
        
        with open("vendor/readme.txt", "w") as f: f.write("vendor")
        with open("vendor/libs/important.js", "w") as f: f.write("important")
        with open("vendor/other/stuff.js", "w") as f: f.write("stuff")
        
        subprocess.run(["git", "add", "-f", "."], cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - "vendor/"
whitelisted_paths:
  - "vendor/libs/"
""")
        
        with patch.object(sys, 'argv', ['dump-git', '--staged']):
            git.main()
        
        output = git.pyperclip.copy.call_args[0][0]
        
        # vendor/libs/ jest whitelisted
        self.assertIn("File: vendor/libs/important.js", output)
        # vendor/ jest blacklisted
        self.assertNotIn("File: vendor/readme.txt", output)
        self.assertNotIn("File: vendor/other/stuff.js", output)

    @patch('ai_tools_lib.git.pyperclip', MagicMock())
    def test_conflicting_paths_error(self):
        """Testuje, czy konflikt między whitelist i blacklist jest wykrywany."""
        self._write_config("""
output_dir: .dump-outputs
blacklisted_paths:
  - "src"
whitelisted_paths:
  - "src/"
""")
        
        os.makedirs("src", exist_ok=True)
        with open("src/app.py", "w") as f: f.write("app")
        subprocess.run(["git", "add", "."], cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        # Oczekujemy SystemExit
        with self.assertRaises(SystemExit) as cm:
            with patch.object(sys, 'argv', ['dump-git', '--staged']):
                git.main()
        
        self.assertEqual(cm.exception.code, 1)
        
        logs = self.log_stream.getvalue()
        self.assertTrue('nieprawidłow' in logs.lower() or 'błąd' in logs.lower())

if __name__ == '__main__':
    unittest.main()
