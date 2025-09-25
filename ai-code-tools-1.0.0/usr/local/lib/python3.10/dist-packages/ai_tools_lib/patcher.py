import os
import re
import sys
import pyperclip

def main():
    base_dir = os.getcwd()
    try:
        patch_content = pyperclip.paste().strip()
        if not patch_content:
            print("INFO: Schowek jest pusty.", file=sys.stderr)
            return 0
    except Exception as e:
        print(f"❌ Błąd odczytu schowka: {e}", file=sys.stderr)
        return 1

    print("🔎 Przetwarzanie zawartości ze schowka w trybie autonomicznym...")

    outer_block_match = re.fullmatch(r"```[a-zA-Z0-9]*\n(.*?)\n```", patch_content, re.DOTALL)
    if outer_block_match:
        print("ℹ️ Wykryto, że cała zawartość schowka jest blokiem kodu. Rozpakowuję...")
        patch_content = outer_block_match.group(1)

    code_block_regex = re.compile(r"```(?:[a-zA-Z0-9]*)?\n(.*?)\n```", re.DOTALL)
    all_blocks = list(re.finditer(code_block_regex, patch_content))

    top_level_blocks = []
    for i, current_block in enumerate(all_blocks):
        is_nested = any(
            other.start() < current_block.start() and other.end() > current_block.end()
            for j, other in enumerate(all_blocks) if i != j
        )
        if not is_nested:
            top_level_blocks.append(current_block)

    if not top_level_blocks:
        print("ℹ️ Nie znaleziono żadnych bloków kodu najwyższego poziomu w schowku.", file=sys.stderr)
        return 0
    
    path_regex = re.compile(
        r'[`\'"]?'
        r'('
        r'(?:(?:\.\.?\/)+)?[\w\-\./]+\.[\w\-]+'
        r'|'
        r'(?:(?:\.\.?\/)+)?[\w\-\.]+(?:\/[\w\-\.]+)+'
        r')'
        r'[`\'"]?'
    )

    patches = []
    last_match_end = 0

    for block in top_level_blocks:
        search_space = patch_content[last_match_end:block.start()]
        path_candidates = list(re.finditer(path_regex, search_space))

        path_found_for_block = False
        for candidate in reversed(path_candidates):
            gap_text = search_space[candidate.end():]

            if not re.search(r'\w{2,}', gap_text):
                path = candidate.group(1).strip().replace('\\', '/')
                
                code_content = block.group(1).strip()

                patches.append((path, code_content))
                path_found_for_block = True
                break

        if not path_found_for_block:
            block_preview = block.group(1).strip().split('\n', 1)[0]
            print(f"ℹ️ Informacja: Nie znaleziono ścieżki w bezpośrednim sąsiedztwie bloku kodu: '{block_preview[:70]}...'. Pomijam.")

        last_match_end = block.end()


    if not patches:
        print("ℹ️ Nie udało się dopasować żadnej pary [prawidłowa ścieżka] -> [kod].", file=sys.stderr)
        return 0

    print(f"\n✨ Znaleziono {len(patches)} plików do aktualizacji.")
    error_count = 0
    for path, content in patches:
        try:
            target_path = os.path.normpath(os.path.join(base_dir, path))
            if not os.path.abspath(target_path).startswith(os.path.abspath(base_dir)):
                 print(f"❌ Błąd bezpieczeństwa: Ścieżka '{path}' próbuje zapisać plik poza katalogiem projektu. Pomijam.")
                 error_count += 1
                 continue

            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            # Zapisujemy już "oczyszczoną" zawartość
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