import os
import shutil
import sys
import unittest
from io import StringIO # <-- POPRAWKA: Dodano brakujący import
from unittest.mock import patch, MagicMock

from ai_tools_lib import patcher

class TestAiPatch(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.abspath("test_project_patcher")
        os.makedirs(self.test_dir, exist_ok=True)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('ai_tools_lib.patcher.pyperclip')
    def test_patch_create_and_update(self, mock_pyperclip):
        # Stworzenie istniejącego pliku
        with open("existing.js", "w") as f:
            f.write("// old content")

        mock_pyperclip.paste.return_value = """
---
File: new_component.js
---
```javascript
export const New = () => {};
```

---
File: existing.js
---
```javascript
// new content
```
"""
        with patch.object(sys, 'argv', ['ai-patch']):
            patcher.main()

        # Sprawdzenie nowego pliku
        self.assertTrue(os.path.exists("new_component.js"))
        with open("new_component.js", "r") as f:
            self.assertIn("export const New", f.read())

        # Sprawdzenie zaktualizowanego pliku
        with open("existing.js", "r") as f:
            self.assertIn("// new content", f.read())

    @patch('ai_tools_lib.patcher.pyperclip')
    def test_patch_security_prevents_path_traversal(self, mock_pyperclip):
        # Ścieżka, która próbuje wyjść z katalogu roboczego
        evil_path = "../evil.txt"
        mock_pyperclip.paste.return_value = f"""
{evil_path}
```
you have been hacked
```
"""
        with patch.object(sys, 'argv', ['ai-patch']):
            result = patcher.main()

        # Sprawdzenie, że funkcja zwróciła 0 (brak plików do przetworzenia to sukces)
        self.assertEqual(result, 0)
        # Sprawdzenie, czy plik nie został utworzony poza katalogiem projektu
        self.assertFalse(os.path.exists(os.path.abspath(os.path.join(self.test_dir, "..", "evil.txt"))))

if __name__ == '__main__':
    unittest.main()