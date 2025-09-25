import os
import re
import sys
import pyperclip
from markdown_it import MarkdownIt

# ... funkcja find_top_level_blocks_with_parser pozostaje bez zmian ...
def find_top_level_blocks_with_parser(text):
    md = MarkdownIt()
    tokens = md.parse(text)
    blocks = []
    lines = text.splitlines(True)
    line_starts = [0]
    for line in lines:
        line_starts.append(line_starts[-1] + len(line))
    for token in tokens:
        if token.type == 'fence' and token.map:
            start_line, end_line = token.map
            block_start_char = line_starts[start_line]
            block_end_char = line_starts[end_line]
            content = token.content
            blocks.append((block_start_char, block_end_char, content))
    return blocks


def main():
    base_dir = os.getcwd()
    try:
        patch_content = pyperclip.paste()
        if not patch_content.strip():
            print("INFO: Schowek jest pusty.", file=sys.stderr)
            return 0
    except Exception as e:
        print(f"❌ Błąd odczytu schowka: {e}", file=sys.stderr)
        return 1

    print("🔎 Przetwarzanie zawartości ze schowka przy użyciu parsera Markdown...")

    stripped_content = patch_content.strip()
    outer_block_match = re.fullmatch(r"```[a-zA-Z0-9]*\n(.*?)\n```", stripped_content, re.DOTALL)
    if outer_block_match:
        print("ℹ️ Wykryto, że cała zawartość schowka jest blokiem kodu. Rozpakowuję...")
        content_to_parse = outer_block_match.group(1)
    else:
        content_to_parse = patch_content

    top_level_blocks_info = find_top_level_blocks_with_parser(content_to_parse)

    if not top_level_blocks_info:
        print("ℹ️ Nie znaleziono żadnych bloków kodu w schowku.", file=sys.stderr)
        return 0
    
    # --- POCZĄTEK KLUCZOWEJ ZMIANY ---
    
    # STARY, DWUZNACZNY REGEX został usunięty.
    # NOWY, JEDNOZNACZNY REGEX:
    # Definiuje ścieżkę jako ciąg segmentów oddzielonych ukośnikami.
    # Używa "negatywnego spojrzenia w przód" (?!\s), aby upewnić się, że ścieżka
    # nie jest tylko częścią dłuższego słowa.
    # Kluczowy warunek: (?=.*[./]) - wymaga, aby w całym dopasowaniu znalazł się
    # przynajmniej jeden ukośnik LUB jedna kropka, co eliminuje pojedyncze słowa.
    path_regex = re.compile(
        r'[`\'"]?'
        r'('
        # Pozytywne spojrzenie w przód: upewnij się, że ciąg zawiera '/' lub '.'
        r'(?=.*[./])'
        # Główny wzorzec: segmenty oddzielone ukośnikami
        r'(?:[\w\-\.]+(?:\/[\w\-\.]+)*)'
        r')'
        r'[`\'"]?'
    )

    # --- KONIEC KLUCZOWEJ ZMIANY ---

    patches = []
    last_match_end = 0

    for block_start, block_end, code_content in top_level_blocks_info:
        search_space = content_to_parse[last_match_end:block_start]
        path_candidates = list(re.finditer(path_regex, search_space))

        path_found_for_block = False
        for candidate in reversed(path_candidates):
            gap_text = search_space[candidate.end():]
            if not re.search(r'\w{2,}', gap_text):
                path = candidate.group(1).strip().replace('\\', '/')
                patches.append((path, code_content.strip()))
                path_found_for_block = True
                break

        if not path_found_for_block:
            block_preview = code_content.strip().split('\n', 1)[0]
            print(f"ℹ️ Informacja: Nie znaleziono ścieżki w bezpośrednim sąsiedztwie bloku kodu: '{block_preview[:70]}...'. Pomijam.")

        last_match_end = block_end

    if not patches:
        print("ℹ️ Nie udało się dopasować żadnej pary [prawidłowa ścieżka] -> [kod].", file=sys.stderr)
        return 0

    print(f"\n✨ Znaleziono {len(patches)} plików do aktualizacji.")
    # Reszta kodu do zapisu plików pozostaje bez zmian...
    error_count = 0
    for path, content in patches:
        try:
            target_path = os.path.normpath(os.path.join(base_dir, path))
            if not os.path.abspath(target_path).startswith(os.path.abspath(base_dir)):
                 print(f"❌ Błąd bezpieczeństwa: Ścieżka '{path}' próbuje zapisać plik poza katalogiem projektu. Pomijam.")
                 error_count += 1
                 continue

            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Zaktualizowano: {path}")
        except Exception as e:
            print(f"❌ Błąd zapisu '{path}': {e}", file=sys.stderr)
            error_count += 1
            
    if error_count == 0:
        print("\n🎉 Wszystkie zmiany zastosowane.")
        return 0
    else:
        print(f"\n- Ukończono z {error_count} błędami.", file=sys.stderr)
        return 1