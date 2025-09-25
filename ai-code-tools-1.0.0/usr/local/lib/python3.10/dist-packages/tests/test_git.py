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

if __name__ == '__main__':
    unittest.main()