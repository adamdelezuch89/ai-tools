import sys
import re
import pyperclip

def parse_and_annotate_blocks(text):
    """
    Analizuje tekst w poszukiwaniu bloków kodu, dodając adnotacje dotyczące
    zagnieżdżenia, otwarcia, zamknięcia i błędów. Zwraca tylko poprawnie
    zamknięte bloki najwyższego poziomu.
    """
    lines = text.splitlines()
    # Wzorzec do wyszukiwania znaczników bloków kodu (``` lub ~~~)
    pattern = re.compile(r"^([ \t]*)([`~]{3,})([^\s]*)([^\n]*)", re.MULTILINE)

    stack = []
    found_blocks = []
    unclosed_blocks_found = False

    pos = 0
    while pos < len(text):
        match = pattern.search(text, pos)
        if not match:
            break

        indent, marker, info, rest_of_line = match.groups()
        line_number = text.count('\n', 0, match.start()) + 1
        line_index = line_number - 1

        if line_index >= len(lines):
            pos = match.end()
            continue

        annotation = ""

        # Sprawdź, czy bieżący znacznik może zamykać blok na stosie
        if stack:
            parent_block = stack[-1]
            is_potential_closer = (
                marker[0] == parent_block["marker"][0] and
                indent == parent_block["indent"] and
                len(marker) >= len(parent_block["marker"]) and
                not info # Znacznik zamykający nie powinien mieć języka
            )

            if is_potential_closer:
                # Sprawdź, czy po znaczniku zamykającym nie ma dodatkowego tekstu
                if rest_of_line.strip():
                    annotation = (
                        f"BŁĄD: Wygląda jak zamykający, ale ma tekst po sobie. "
                        f"Traktowany jako OTWIERAJĄCY nowy blok na poziomie {len(stack) + 1}."
                    )
                else:
                    # Poprawne zamknięcie bloku
                    closed_block = stack.pop()
                    annotation = (
                        f"ZAMYKAJĄCY: Zamyka blok otwarty w linii {closed_block['line_number']}. "
                        f"Nowy poziom zagnieżdżenia: {len(stack)}."
                    )
                    if line_index < len(lines):
                        lines[line_index] += f" # <<< {annotation}"

                    # Zapisz blok jako wynik TYLKO jeśli po jego zamknięciu stos jest pusty (jest to blok najwyższego poziomu)
                    if not stack:
                        start_offset = closed_block["content_start_offset"]
                        end_offset = match.start()
                        if end_offset > 0 and text[end_offset - 1] == '\n':
                            end_offset -= 1
                        
                        content = text[start_offset:end_offset]
                        found_blocks.append((start_offset, end_offset, content, closed_block["info"]))
                    
                    pos = match.end()
                    continue
        
        # Jeśli nie jest to znacznik zamykający, traktuj go jako otwierający
        if not annotation:
            new_level = len(stack) + 1
            annotation = f"OTWIERAJĄCY: Nowy blok na poziomie {new_level}."
        
        if line_index < len(lines):
            lines[line_index] += f" # <<< {annotation}"
        
        stack.append({
            "marker": marker,
            "indent": indent,
            "info": info,
            "line_number": line_number,
            "content_start_offset": match.end() + (1 if match.end() < len(text) and text[match.end()] == '\n' else 0)
        })
        
        pos = match.end()

    # Sprawdź, czy na końcu parsowania zostały jakieś niezamknięte bloki
    if stack:
        unclosed_blocks_found = True
        print(f"\nBŁĄD: Znaleziono {len(stack)} niezamkniętych bloków.", file=sys.stderr)
        for open_block in stack:
            line_idx = open_block['line_number'] - 1
            error_annotation = " # <<< BŁĄD: Ten blok nigdy nie został zamknięty."
            if line_idx < len(lines):
                 lines[line_idx] += error_annotation
            
            print(
                f"  - Blok otwarty w linii {open_block['line_number']} (znacznik: '{open_block['marker']}') nie został zamknięty.",
                file=sys.stderr,
            )

    return found_blocks, "\n".join(lines), unclosed_blocks_found


def main():
    """
    Główna funkcja skryptu. Pobiera tekst ze schowka, analizuje go,
    wypisuje wyniki i tworzy plik z adnotacjami.
    """
    try:
        content = pyperclip.paste()
        if not content or not content.strip():
            print("INFO: Schowek jest pusty. Nie ma nic do przeanalizowania.", file=sys.stderr)
            sys.exit(0)
    except Exception as e:
        print(f"BŁĄD: Nie można odczytać zawartości schowka: {e}", file=sys.stderr)
        sys.exit(1)

    blocks, annotated_content, had_errors = parse_and_annotate_blocks(content)
    
    output_filename = 'output.annotated.txt'
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(annotated_content)
        print(f"INFO: Utworzono plik z adnotacjami do analizy: {output_filename}")
    except IOError as e:
        print(f"BŁĄD: Nie można zapisać pliku z adnotacjami: {e}", file=sys.stderr)

    print(f"\n--- WYNIKI PARSOWANIA ---")
    print(f"Znaleziono {len(blocks)} poprawnie zamkniętych bloków kodu najwyższego poziomu.")
    
    # Sortowanie bloków na podstawie ich pozycji w tekście
    blocks.sort(key=lambda b: b[0])

    for i, (start, end, content, info) in enumerate(blocks, 1):
        content_to_print = content.removesuffix('\n')
        print(f"\n--- Blok #{i} (znaki {start}-{end}, język='{info}') ---")
        print(content_to_print)
        print("--- Koniec Bloku ---")

    if had_errors:
        print("\nAnaliza zakończona z błędami (sprawdź plik .annotated.txt i komunikaty powyżej).")
        sys.exit(1)
    else:
        print("\nAnaliza zakończona pomyślnie. Wszystkie bloki wydają się być poprawnie zagnieżdżone i zamknięte.")


if __name__ == "__main__":
    main()