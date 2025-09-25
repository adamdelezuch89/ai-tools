import os
import sys
import pyperclip
from .helpers import log_error, log_info, log_success, parse_patch_content

def main():
    base_dir = os.getcwd()
    try:
        patch_content = pyperclip.paste()
        if not patch_content.strip():
            log_info("Schowek jest pusty.")
            return 0
    except Exception as e:
        log_error(f"Nie można odczytać zawartości schowka: {e}")
        return 1

    log_info("Przetwarzanie zawartości ze schowka...")

    patches = parse_patch_content(patch_content)

    if not patches:
        log_info("Nie znaleziono żadnych prawidłowych bloków [ścieżka -> kod] do zastosowania.")
        return 0

    log_info(f"Znaleziono {len(patches)} plików do aktualizacji.")
    error_count = 0

    for path, content in patches:
        try:
            # Zapewnienie, że ścieżka jest względna i bezpieczna
            target_path = os.path.normpath(os.path.join(base_dir, path))
            if not os.path.abspath(target_path).startswith(os.path.abspath(base_dir)):
                log_error(f"Błąd bezpieczeństwa: Ścieżka '{path}' próbuje zapisać plik poza katalogiem projektu. Pomijam.")
                error_count += 1
                continue

            # Utworzenie katalogów, jeśli nie istnieją
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            with open(target_path, 'w', encoding='utf-8') as f:
                # Zapewnienie, że niepusty plik kończy się nową linią.
                if content and not content.endswith('\n'):
                    content += '\n'
                f.write(content)

            log_success(f"Zaktualizowano: {path}")

        except Exception as e:
            log_error(f"Błąd zapisu pliku '{path}': {e}")
            error_count += 1
            
    if error_count == 0:
        log_success("\nWszystkie zmiany zastosowane pomyślnie.")
        return 0
    else:
        log_error(f"\nUkończono z {error_count} błędami.")
        return 1
