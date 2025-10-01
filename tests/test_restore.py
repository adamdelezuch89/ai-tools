import os
import shutil
import subprocess
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock

from ai_tools.cli import dump_repo as repo
from ai_tools.utils import helpers
from ai_tools.utils.temp_storage import parse_dump_file, get_dump_by_ref


class TestRestoreFunctionality(unittest.TestCase):
    """Testy funkcji restore dla dump-repo"""
    
    def setUp(self):
        """Tworzy tymczasową strukturę katalogów i repozytorium Git."""
        self.test_dir = os.path.abspath("test_project_restore")
        os.makedirs(os.path.join(self.test_dir, "src"), exist_ok=True)
        
        # Konfiguracja z explicite output_dir dla testów
        with open(os.path.join(self.test_dir, helpers.CONFIG_FILENAME), "w") as f:
            f.write(f"output_dir: {os.path.join(self.test_dir, '.dump-outputs')}\n")
        
        # Utwórz testowe pliki
        with open(os.path.join(self.test_dir, "src/app.py"), "w") as f:
            f.write("# Original content\nprint('original')\n")
        with open(os.path.join(self.test_dir, "config.json"), "w") as f:
            f.write('{"version": "1.0"}\n')
        
        # Inicjalizuj Git repo
        subprocess.run(["git", "init"], cwd=self.test_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "add", "."], cwd=self.test_dir, stdout=subprocess.DEVNULL)
        
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('ai_tools.cli.dump_repo.pyperclip', MagicMock())
    def test_restore_from_dump(self):
        """Test przywracania plików z dumpu"""
        # 1. Utwórz dump manualnie
        dump_dir = os.path.join(self.test_dir, '.dump-outputs')
        os.makedirs(dump_dir, exist_ok=True)
        
        dump_content = """---
File: src/app.py
---
```python
# Original content
print('original')
```

---
File: config.json
---
```json
{"version": "1.0"}
```
"""
        dump_path = os.path.join(dump_dir, "20251001_120000-repo-dump.txt")
        with open(dump_path, 'w') as f:
            f.write(dump_content)
        
        # 2. Zmodyfikuj pliki
        with open("src/app.py", "w") as f:
            f.write("# MODIFIED\nprint('modified')\n")
        with open("config.json", "w") as f:
            f.write('{"version": "2.0"}\n')
        
        # 3. Sprawdź że pliki są zmodyfikowane
        with open("src/app.py", "r") as f:
            self.assertIn("MODIFIED", f.read())
        
        # 4. Parsuj dump
        files = parse_dump_file(dump_path)
        
        # 5. Sprawdź że dump zawiera pliki
        self.assertEqual(len(files), 2)
        file_paths = [f[0] for f in files]
        self.assertIn("src/app.py", file_paths)
        self.assertIn("config.json", file_paths)
        
        # 6. Przywróć pliki
        for file_path, content in files:
            full_path = os.path.join(self.test_dir, file_path)
            with open(full_path, 'w') as f:
                f.write(content)
        
        # 7. Sprawdź że pliki zostały przywrócone
        with open("src/app.py", "r") as f:
            content = f.read()
            self.assertIn("original", content)
            self.assertNotIn("MODIFIED", content)
        
        with open("config.json", "r") as f:
            content = f.read()
            self.assertIn('"version": "1.0"', content)
    
    def test_get_dump_by_ref_empty(self):
        """Test get_dump_by_ref z pustym ref (ostatni dump)"""
        dump_dir = tempfile.mkdtemp()
        
        # Utwórz 3 pliki z różnymi timestampami
        filenames = ["20251001_120000-repo-dump.txt", 
                     "20251002_120000-repo-dump.txt",
                     "20251003_120000-repo-dump.txt"]
        
        for i, filename in enumerate(filenames):
            filepath = os.path.join(dump_dir, filename)
            with open(filepath, 'w') as f:
                f.write(f"dump {i+1}")
            # Ustaw różne czasy modyfikacji (rosnące)
            mtime = 1000000000 + i * 10000
            os.utime(filepath, (mtime, mtime))
        
        # Pusty ref powinien zwrócić najnowszy
        result = get_dump_by_ref(dump_dir, "")
        self.assertIsNotNone(result)
        self.assertIn("20251003", os.path.basename(result))  # Najnowszy
        
        shutil.rmtree(dump_dir)
    
    def test_get_dump_by_ref_number(self):
        """Test get_dump_by_ref z numerem"""
        dump_dir = tempfile.mkdtemp()
        
        # Utwórz 3 pliki z różnymi timestampami
        filenames = ["20251001_120000-repo-dump.txt",
                     "20251002_120000-repo-dump.txt", 
                     "20251003_120000-repo-dump.txt"]
        
        for i, filename in enumerate(filenames):
            filepath = os.path.join(dump_dir, filename)
            with open(filepath, 'w') as f:
                f.write(f"dump {i+1}")
            mtime = 1000000000 + i * 10000
            os.utime(filepath, (mtime, mtime))
        
        # 1 = najnowszy (20251003 ma najnowszy mtime)
        result = get_dump_by_ref(dump_dir, "1")
        self.assertIn("20251003", os.path.basename(result))
        
        # 2 = drugi od końca
        result = get_dump_by_ref(dump_dir, "2")
        self.assertIn("20251002", os.path.basename(result))
        
        # 3 = trzeci od końca
        result = get_dump_by_ref(dump_dir, "3")
        self.assertIn("20251001", os.path.basename(result))
        
        shutil.rmtree(dump_dir)
    
    def test_parse_dump_file(self):
        """Test parsowania pliku dumpu"""
        dump_dir = tempfile.mkdtemp()
        dump_file = os.path.join(dump_dir, "test-dump.txt")
        
        # Utwórz testowy dump
        with open(dump_file, 'w') as f:
            f.write("""---
File: src/app.py
---
```python
print('hello')
```

---
File: config.json
---
```json
{"key": "value"}
```
""")
        
        # Parse dump
        files = parse_dump_file(dump_file)
        
        # Sprawdź wyniki
        self.assertEqual(len(files), 2)
        
        paths = [f[0] for f in files]
        self.assertIn("src/app.py", paths)
        self.assertIn("config.json", paths)
        
        # Sprawdź zawartość
        for path, content in files:
            if path == "src/app.py":
                self.assertEqual(content, "print('hello')")
            elif path == "config.json":
                self.assertEqual(content, '{"key": "value"}')
        
        shutil.rmtree(dump_dir)

    def test_parse_dump_file_with_tricky_content(self):
        """Test parsowania pliku dumpu z problematyczną zawartością (--- i ``` w środku)."""
        dump_dir = tempfile.mkdtemp()
        dump_file = os.path.join(dump_dir, "tricky-dump.txt")

        tricky_content = """Some text
---
Another line with triple-dash
And a nested code block:
```
nested
```
End of content."""

        # Utwórz testowy dump
        with open(dump_file, 'w', encoding='utf-8') as f:
            f.write(f"""---
File: src/tricky.txt
---
```text
{tricky_content}
```

---
File: src/another.txt
---
```text
another file content
```
""")
        
        # Parse dump
        files = parse_dump_file(dump_file)
        
        # Sprawdź wyniki
        self.assertEqual(len(files), 2)
        
        paths = [f[0] for f in files]
        self.assertIn("src/tricky.txt", paths)
        self.assertIn("src/another.txt", paths)
        
        # Sprawdź zawartość
        for path, content in files:
            if path == "src/tricky.txt":
                self.assertEqual(content, tricky_content)
            elif path == "src/another.txt":
                self.assertEqual(content, 'another file content')
        
        shutil.rmtree(dump_dir)


if __name__ == '__main__':
    unittest.main()

