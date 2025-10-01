import os
import sys
import unittest
from unittest.mock import patch
from io import StringIO

from ai_tools_lib.helpers import _extract_path_from_text, _find_blocks_with_regex, parse_patch_content


class TestExtractPathFromText(unittest.TestCase):
    """Testy dla funkcji wyodrębniania ścieżek z tekstu."""

    def test_simple_path(self):
        """Test dla prostej ścieżki pliku."""
        result = _extract_path_from_text("notes.txt")
        self.assertEqual(result, "notes.txt")

    def test_relative_path_with_dot_slash(self):
        """Test dla ścieżki względnej zaczynającej się od ./"""
        result = _extract_path_from_text("./src/main.py")
        self.assertEqual(result, "./src/main.py")

    def test_relative_path_with_double_dot(self):
        """Test dla ścieżki względnej z ../ - powinna być odrzucona ze względów bezpieczeństwa."""
        with patch('sys.stdout', new_callable=StringIO):
            result = _extract_path_from_text("../data/input.csv")
        self.assertIsNone(result)

    def test_path_with_markdown_backticks(self):
        """Test dla ścieżki otoczonej backticks markdown."""
        result = _extract_path_from_text("`src/components/Button.tsx`")
        self.assertEqual(result, "src/components/Button.tsx")

    def test_path_with_markdown_asterisks(self):
        """Test dla ścieżki otoczonej gwiazdkami markdown."""
        result = _extract_path_from_text("**./config/settings.json**")
        self.assertEqual(result, "./config/settings.json")

    def test_path_with_markdown_brackets(self):
        """Test dla ścieżki w nawiasach kwadratowych markdown."""
        result = _extract_path_from_text("[obrazy/photo.png]")
        self.assertEqual(result, "obrazy/photo.png")

    def test_path_with_at_prefix(self):
        """Test dla ścieżki z prefiksem @ (aliasy)."""
        result = _extract_path_from_text("@alias/utils.js")
        self.assertEqual(result, "alias/utils.js")

    def test_path_with_asterisk_suffix(self):
        """Test dla ścieżki z gwiazdką na końcu."""
        result = _extract_path_from_text("docs/readme.md*")
        self.assertEqual(result, "docs/readme.md")

    def test_multiple_paths_returns_last(self):
        """Test że zwraca ostatnią znalezioną ścieżkę."""
        result = _extract_path_from_text("src/test.py i potem data/file.csv")
        self.assertEqual(result, "data/file.csv")

    def test_multiple_paths_with_different_formats(self):
        """Test dla wielu ścieżek w różnych formatach (path traversal odrzucane)."""
        with patch('sys.stdout', new_callable=StringIO):
            result = _extract_path_from_text("Tutaj przykłady: ./src/main.py  ../data/input.csv")
        # ../data/input.csv jest odrzucane, więc zwraca ./src/main.py
        self.assertEqual(result, "./src/main.py")

    def test_path_in_sentence(self):
        """Test dla ścieżki w środku zdania."""
        result = _extract_path_from_text("Zmień plik `src/components/Button.tsx` teraz")
        self.assertEqual(result, "src/components/Button.tsx")

    def test_path_in_sentence_with_period_at_end(self):
        """Test dla ścieżki w zdaniu kończącym się kropką."""
        result = _extract_path_from_text("Zmień plik src/main.py.")
        self.assertEqual(result, "src/main.py")

    def test_path_with_period_at_end_and_backticks(self):
        """Test dla ścieżki w backticks w zdaniu z kropką."""
        result = _extract_path_from_text("Proszę zaktualizować `config/settings.json`.")
        self.assertEqual(result, "config/settings.json")

    def test_no_path_found(self):
        """Test gdy nie ma żadnej ścieżki."""
        result = _extract_path_from_text("Bez ścieżki tutaj")
        self.assertIsNone(result)

    def test_text_with_dots_but_no_path(self):
        """Test dla tekstu z kropkami ale bez poprawnej ścieżki."""
        result = _extract_path_from_text("To jest tekst... bez ścieżki.")
        self.assertIsNone(result)

    def test_empty_string(self):
        """Test dla pustego ciągu znaków."""
        result = _extract_path_from_text("")
        self.assertIsNone(result)

    def test_only_whitespace(self):
        """Test dla ciągu znaków zawierającego tylko białe znaki."""
        result = _extract_path_from_text("   \n\t  ")
        self.assertIsNone(result)

    def test_path_with_hyphens_and_underscores(self):
        """Test dla ścieżki z myślnikami i podkreśleniami."""
        result = _extract_path_from_text("src/my-component_file.tsx")
        self.assertEqual(result, "src/my-component_file.tsx")

    def test_path_with_multiple_markdown_wrappers(self):
        """Test dla ścieżki z wieloma znacznikami markdown."""
        result = _extract_path_from_text("**[`docs/readme.md`]**")
        self.assertEqual(result, "docs/readme.md")

    def test_path_with_nested_directories(self):
        """Test dla głęboko zagnieżdżonej ścieżki."""
        result = _extract_path_from_text("src/components/forms/inputs/TextInput.tsx")
        self.assertEqual(result, "src/components/forms/inputs/TextInput.tsx")

    def test_path_traversal_is_rejected(self):
        """Test że ścieżki z path traversal (..) są odrzucane."""
        with patch('sys.stdout', new_callable=StringIO):
            result = _extract_path_from_text("../evil.txt")
        self.assertIsNone(result)

    def test_path_traversal_in_middle_is_rejected(self):
        """Test że ścieżki z path traversal w środku są odrzucane."""
        with patch('sys.stdout', new_callable=StringIO):
            result = _extract_path_from_text("../config/settings.json")
        self.assertIsNone(result)

    def test_path_traversal_with_valid_paths(self):
        """Test że path traversal nie wpływa na inne ścieżki w tym samym tekście."""
        with patch('sys.stdout', new_callable=StringIO):
            result = _extract_path_from_text("../evil.txt oraz src/main.py")
        # Powinien zwrócić src/main.py (ignorując ../evil.txt)
        self.assertEqual(result, "src/main.py")


class TestFindBlocksWithRegex(unittest.TestCase):
    """Testy dla funkcji wyszukiwania bloków kodu markdown."""

    def test_simple_code_block(self):
        """Test dla prostego bloku kodu."""
        text = """```python
print("hello")
```"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 1)
        opening_start, content_start, content_end, content = blocks[0]
        self.assertEqual(content, 'print("hello")')

    def test_code_block_with_info_string(self):
        """Test dla bloku z info string (typ języka)."""
        text = """```javascript
console.log("test");
```"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 1)
        _, _, _, content = blocks[0]
        self.assertEqual(content, 'console.log("test");')

    def test_code_block_without_info_string(self):
        """Test dla bloku bez info string."""
        text = """```
plain text
```"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 1)
        _, _, _, content = blocks[0]
        self.assertEqual(content, 'plain text')

    def test_nested_code_blocks_returns_only_outer(self):
        """Test że zagnieżdżone bloki zwracają tylko zewnętrzny."""
        text = """```markdown
To jest markdown z zagnieżdżonym blokiem:
```python
nested code
```
koniec markdowna
```"""
        blocks = _find_blocks_with_regex(text)
        # Powinien zwrócić tylko zewnętrzny blok
        self.assertEqual(len(blocks), 1)
        _, _, _, content = blocks[0]
        self.assertIn('nested code', content)
        self.assertIn('koniec markdowna', content)

    def test_multiple_blocks_at_same_level(self):
        """Test dla wielu bloków na tym samym poziomie."""
        text = """```python
first block
```

Some text

```javascript
second block
```"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 2)
        _, _, _, content1 = blocks[0]
        _, _, _, content2 = blocks[1]
        self.assertEqual(content1, 'first block')
        self.assertEqual(content2, 'second block')

    def test_unclosed_block_shows_warning(self):
        """Test że niezamknięty blok generuje ostrzeżenie."""
        text = """```python
unclosed block
"""
        with patch('sys.stdout', new_callable=StringIO):
            blocks = _find_blocks_with_regex(text)
        # Nie powinien znaleźć żadnych bloków (niezamknięty)
        self.assertEqual(len(blocks), 0)

    def test_block_with_tildes(self):
        """Test dla bloku z ~~~ zamiast ```."""
        text = """~~~python
code with tildes
~~~"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 1)
        _, _, _, content = blocks[0]
        self.assertEqual(content, 'code with tildes')

    def test_block_with_longer_markers(self):
        """Test dla bloku z dłuższymi znacznikami (4+ znaki)."""
        text = """````python
code with 4 backticks
````"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 1)
        _, _, _, content = blocks[0]
        self.assertEqual(content, 'code with 4 backticks')

    def test_closer_with_same_number_of_backticks(self):
        """Test że zamykający z taką samą liczbą znaków zamyka blok (standardowe użycie)."""
        text = """```python
code
```"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 1)
        _, _, _, content = blocks[0]
        self.assertEqual(content, 'code')

    def test_four_backticks_matched_correctly(self):
        """Test że 4 backticki są poprawnie dopasowane."""
        text = """````markdown
code with 4 backticks
````"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 1)
        _, _, _, content = blocks[0]
        self.assertEqual(content, 'code with 4 backticks')

    def test_indented_code_blocks(self):
        """Test dla bloków z wcięciem."""
        text = """    ```python
    indented code
    ```"""
        blocks = _find_blocks_with_regex(text)
        # Funkcja ignoruje wcięcia i znajduje bloki
        self.assertEqual(len(blocks), 1)
        _, _, _, content = blocks[0]
        self.assertIn('indented code', content)

    def test_block_without_trailing_newline(self):
        """Test dla bloku bez końcowej nowej linii."""
        text = """```python
code without trailing newline```"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 1)

    def test_mixed_backticks_and_tildes_dont_match(self):
        """Test że backticki i tyldy nie pasują do siebie."""
        text = """```python
code
~~~"""
        with patch('sys.stdout', new_callable=StringIO):
            blocks = _find_blocks_with_regex(text)
        # Nie powinien zamknąć bloku (różne typy znaczników)
        self.assertEqual(len(blocks), 0)

    def test_empty_code_block(self):
        """Test dla pustego bloku kodu."""
        text = """```
```"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 1)
        _, _, _, content = blocks[0]
        self.assertEqual(content, '')

    def test_block_positions_are_correct(self):
        """Test że pozycje bloków są poprawnie zwracane."""
        text = """prefix text
```python
content
```
suffix"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 1)
        opening_start, content_start, content_end, content = blocks[0]
        
        # Sprawdź że opening_start wskazuje na początek ```
        self.assertEqual(text[opening_start:opening_start+3], '```')
        
        # Sprawdź że content to faktycznie zawartość
        self.assertEqual(content, 'content')
        
        # Sprawdź że możemy wyciągnąć zawartość używając pozycji
        self.assertEqual(text[content_start:content_end], 'content')

    def test_multiple_nested_levels(self):
        """Test dla wielopoziomowego zagnieżdżenia."""
        text = """````markdown
Outer block
```html
Middle block
~~python
Inner block
~~
End middle
```
End outer
````"""
        blocks = _find_blocks_with_regex(text)
        # Powinien zwrócić tylko zewnętrzny blok
        self.assertEqual(len(blocks), 1)
        _, _, _, content = blocks[0]
        self.assertIn('Outer block', content)
        self.assertIn('End outer', content)

    def test_blocks_sorted_by_position(self):
        """Test że bloki są sortowane według pozycji."""
        text = """first
```
block1
```
middle
```
block2
```
end"""
        blocks = _find_blocks_with_regex(text)
        self.assertEqual(len(blocks), 2)
        # Sprawdź że są w kolejności wystąpienia
        opening1, _, _, content1 = blocks[0]
        opening2, _, _, content2 = blocks[1]
        self.assertLess(opening1, opening2)
        self.assertEqual(content1, 'block1')
        self.assertEqual(content2, 'block2')


class TestParsePatchContent(unittest.TestCase):
    """Testy dla funkcji parsowania zawartości patchy."""

    def test_simple_patch(self):
        """Test dla prostego patcha."""
        content = """
src/main.py
```python
print("Hello World")
```
"""
        patches = parse_patch_content(content)
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0][0], "src/main.py")
        self.assertEqual(patches[0][1], 'print("Hello World")')

    def test_multiple_patches(self):
        """Test dla wielu patchy."""
        content = """
src/file1.py
```python
# File 1
```

src/file2.js
```javascript
// File 2
```
"""
        patches = parse_patch_content(content)
        self.assertEqual(len(patches), 2)
        self.assertEqual(patches[0][0], "src/file1.py")
        self.assertEqual(patches[1][0], "src/file2.js")

    def test_patch_with_markdown_wrapped_path(self):
        """Test dla patcha ze ścieżką w markdown."""
        content = """
`src/components/Button.tsx`
```tsx
export const Button = () => {};
```
"""
        patches = parse_patch_content(content)
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0][0], "src/components/Button.tsx")

    def test_patch_with_path_in_sentence(self):
        """Test dla patcha ze ścieżką w zdaniu."""
        content = """
Zaktualizuj plik src/main.py.
```python
def hello():
    pass
```
"""
        patches = parse_patch_content(content)
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0][0], "src/main.py")

    def test_patch_with_at_prefix_path(self):
        """Test dla patcha ze ścieżką z prefiksem @."""
        content = """
@components/Button.tsx
```tsx
export default Button;
```
"""
        patches = parse_patch_content(content)
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0][0], "components/Button.tsx")

    def test_empty_content(self):
        """Test dla pustej zawartości."""
        patches = parse_patch_content("")
        self.assertEqual(patches, [])

    def test_code_block_without_path(self):
        """Test dla bloku kodu bez ścieżki - powinien być pominięty."""
        content = """
Jakiś tekst bez ścieżki
```python
print("orphan code")
```
"""
        # Powinien wyświetlić ostrzeżenie ale nie rzucić wyjątku
        with patch('sys.stderr', new_callable=StringIO):
            patches = parse_patch_content(content)
        self.assertEqual(len(patches), 0)

    def test_outer_code_block_is_unwrapped(self):
        """Test że zewnętrzny blok kodu jest rozpakowywany."""
        content = """```
src/file.py
```python
content
```
```"""
        patches = parse_patch_content(content)
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0][0], "src/file.py")

    def test_path_normalization_backslashes(self):
        """Test normalizacji ścieżek z backslashami."""
        content = """
src\\windows\\path.py
```python
# content
```
"""
        patches = parse_patch_content(content)
        self.assertEqual(len(patches), 1)
        # Backslashe powinny być zamienione na forwardslashe
        self.assertEqual(patches[0][0], "src/windows/path.py")

    def test_last_path_before_code_block_is_used(self):
        """Test że używana jest ostatnia ścieżka przed blokiem kodu."""
        content = """
Zmień files/old.py oraz files/new.py
```python
# new content
```
"""
        patches = parse_patch_content(content)
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0][0], "files/new.py")


if __name__ == '__main__':
    unittest.main()

