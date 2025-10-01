import argparse
import os
import subprocess
from datetime import datetime
import pyperclip
import tiktoken

# Import from new modular structure
from ai_tools.utils.config import (
    get_config, find_project_root, find_git_root, 
    CONFIG_FILENAME, create_default_config
)
from ai_tools.utils.logger import log_error, log_info, log_success, log_warning
from ai_tools.utils.filesystem import format_file_content
from ai_tools.utils.temp_storage import (
    get_project_temp_dir, cleanup_old_dumps, list_recent_dumps, 
    format_file_size, parse_dump_file, get_dump_by_ref
)
from ai_tools.core.file_filter import (
    is_binary,
    normalize_path_pattern,
    is_directory_pattern,
    find_most_specific_match,
    validate_config_paths
)

# --- POCZĄTEK NOWEJ IMPLEMENTACJI ---
def get_files_to_dump(paths_to_scan, start_dir, project_root, git_root, config):
    whitelisted_patterns = config.get('whitelisted_paths', [])
    # Dodajemy .gitignore do domyślnej czarnej listy, aby sam plik nie był dumpowany
    blacklisted_patterns = config.get('blacklisted_paths', []) + ['.git/', '.gitignore']
    config_file_abs = os.path.abspath(os.path.join(project_root, CONFIG_FILENAME))

    # Krok 1: Pobierz pliki z git (nieignorowane przez .gitignore)
    files_from_git = set()
    if git_root:
        try:
            cmd = ['git', '-C', git_root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z']
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True)
            git_files_rel = (p for p in result.stdout.strip('\0').split('\0') if p)
            files_from_git.update(os.path.normpath(os.path.join(git_root, p)) for p in git_files_rel)
        except (subprocess.CalledProcessError, FileNotFoundError):
            log_warning("Polecenie 'git ls-files' zawiodło. Skanowanie ręczne bez uwzględnienia .gitignore.")

    # Krok 2: Zbierz WSZYSTKIE pliki z systemu (dla whitelist)
    all_files_in_project = set()
    for root, _, files in os.walk(project_root):
        for name in files:
            all_files_in_project.add(os.path.join(root, name))
    
    # Krok 3: Dla każdego pliku zastosuj logikę priorytetyzacji
    final_files = set()
    
    for f_path in all_files_in_project:
        rel_path = os.path.relpath(f_path, project_root)
        
        # Znajdź najbardziej specyficzne dopasowania w obu listach
        whitelist_match, whitelist_spec = find_most_specific_match(rel_path, whitelisted_patterns)
        blacklist_match, blacklist_spec = find_most_specific_match(rel_path, blacklisted_patterns)
        
        # Logika decyzyjna:
        should_include = False
        
        if whitelist_spec > 0 and blacklist_spec > 0:
            # Oba pasują - bardziej specyficzny wygrywa
            if whitelist_spec > blacklist_spec:
                should_include = True
            elif blacklist_spec > whitelist_spec:
                should_include = False
            else:
                # Ta sama specyficzność - blacklist wygrywa (ale to nie powinno się zdarzyć po walidacji)
                should_include = False
        elif whitelist_spec > 0:
            # Tylko whitelist - załącz (nawet jeśli gitignored)
            should_include = True
        elif blacklist_spec > 0:
            # Tylko blacklist - wyklucz
            should_include = False
        else:
            # Brak reguł - użyj wyniku git (czy plik był w git ls-files?)
            should_include = f_path in files_from_git
        
        if should_include:
            final_files.add(f_path)
    
    # Krok 4: Ogranicz do ścieżek podanych przez użytkownika (zakres)
    scan_paths_abs = [os.path.abspath(os.path.join(start_dir, p)) for p in paths_to_scan]
    files_in_scope = set()
    for f_path in final_files:
        for scan_path in scan_paths_abs:
            if f_path == scan_path or f_path.startswith(os.path.normpath(scan_path) + os.sep):
                files_in_scope.add(f_path)
                break

    # Krok 5: Ostateczne czyszczenie
    final_files_cleaned = {
        f_path for f_path in files_in_scope
        if not (f_path == config_file_abs or is_binary(f_path))
    }

    return sorted(list(final_files_cleaned))

def main():
    start_dir = os.getcwd()
    project_root = find_project_root(start_dir)
    git_root = find_git_root(start_dir)
    config = get_config(project_root)
    
    # Przygotuj dynamiczny help message
    config_file_path = os.path.join(project_root, CONFIG_FILENAME)
    has_config = os.path.exists(config_file_path)
    
    if has_config:
        hide_env_status = "✓ włączone" if config.get('hide_env', True) else "✗ wyłączone"
        blacklist_count = len(config.get('blacklisted_paths', []))
        whitelist_count = len(config.get('whitelisted_paths', []))
        
        epilog_text = f'''
Konfiguracja z {CONFIG_FILENAME}:
  Output:      {config['output_dir']}
  Hide .env:   {hide_env_status}
  Blacklist:   {blacklist_count} ścieżek
  Whitelist:   {whitelist_count} ścieżek
  Rozszerzenia: {len(config.get('extension_lang_map', {}))} języków

Co będzie dumpowane:
  ✓ Pliki śledzone przez Git (.gitignore respektowany)
  ✓ Pliki z whitelist (nawet jeśli .gitignore)
  ✗ Pliki z blacklist
  ✗ Pliki binarne
  ✗ Wrażliwe wartości z .env (jeśli hide_env=true)
        '''
    else:
        epilog_text = '''
Nie znaleziono pliku konfiguracyjnego.

Utwórz plik konfiguracyjny:
  dump-repo --init

Co będzie dumpowane (domyślnie):
  ✓ Wszystkie pliki śledzone przez Git
  ✗ Pliki binarne
  ✗ Wrażliwe wartości z .env (automatycznie ukryte)
        '''
    
    parser = argparse.ArgumentParser(
        description="Tworzy dump zawartości plików z projektu",
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--init', action='store_true',
                       help='Utwórz plik konfiguracyjny .ai-tools-config.yaml')
    parser.add_argument('--list', action='store_true',
                       help='Pokaż ostatnie dumpy (interaktywne przywracanie)')
    parser.add_argument('--restore', nargs='?', const='', metavar='N',
                       help='Przywróć pliki z dumpu (1=ostatni, 2=przedostatni, puste=ostatni)')
    parser.add_argument('paths', nargs='*', default=['.'], 
                       help="Lista ścieżek do przetworzenia (względem bieżącego katalogu)")
    args = parser.parse_args()
    
    # Handle --init flag
    if args.init:
        try:
            created_path = create_default_config(project_root)
            log_success(f"Utworzono plik konfiguracyjny: {os.path.relpath(created_path, start_dir)}")
            log_info("Edytuj plik aby dostosować ustawienia do swojego projektu.")
            return 0
        except FileExistsError:
            log_warning(f"Plik {CONFIG_FILENAME} już istnieje. Użyj go lub usuń przed ponownym --init.")
            return 1
        except IOError as e:
            log_error(f"Błąd tworzenia pliku konfiguracyjnego: {e}")
            return 1
    
    # Get output directory (temp dir per project)
    output_dir_path = get_project_temp_dir(project_root, 'dump-repo')
    
    # Handle --list flag
    if args.list:
        dumps = list_recent_dumps(output_dir_path, limit=20)
        
        if not dumps:
            log_info("Brak dumpów dla tego projektu.")
            return 0
        
        log_info(f"Ostatnie dumpy dla projektu ({len(dumps)}):\n")
        for i, (filename, timestamp, size) in enumerate(dumps):
            # Ścieżka jest klikalnym linkiem w większości terminali
            filepath = os.path.join(output_dir_path, filename)
            print(f"  {i}. [{timestamp}] {filepath} ({format_file_size(size)})")
        
        print("\nWpisz numer aby PRZYWRÓCIĆ (Enter aby anulować): ", end='', flush=True)
        try:
            choice = input().strip()
            if choice and choice.isdigit():
                idx = int(choice)
                if 0 <= idx < len(dumps):
                    # Przywróć z wybranego dumpu
                    dump_path = os.path.join(output_dir_path, dumps[idx][0])
                    files = parse_dump_file(dump_path)
                    
                    if not files:
                        log_warning("Nie znaleziono plików w dumpie do przywrócenia.")
                        return 1
                    
                    log_info(f"Przywracanie {len(files)} plików z {dumps[idx][0]}...")
                    restored = 0
                    for file_path, content in files:
                        try:
                            full_path = os.path.join(project_root, file_path)
                            os.makedirs(os.path.dirname(full_path), exist_ok=True)
                            with open(full_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            restored += 1
                        except IOError as e:
                            log_warning(f"Nie można przywrócić {file_path}: {e}")
                    
                    log_success(f"Przywrócono {restored}/{len(files)} plików.")
                    return 0
        except (KeyboardInterrupt, EOFError):
            print()
            return 0
        
        return 0
    
    # Handle --restore flag
    if args.restore is not None:
        dump_path = get_dump_by_ref(output_dir_path, args.restore)
        
        if not dump_path:
            log_error(f"Nie znaleziono dumpu: {args.restore}. Użyj --list aby zobaczyć dostępne dumpy.")
            return 1
        
        files = parse_dump_file(dump_path)
        
        if not files:
            log_warning("Nie znaleziono plików w dumpie do przywrócenia.")
            return 1
        
        dump_name = os.path.basename(dump_path)
        log_info(f"Przywracanie {len(files)} plików z {dump_name}...")
        
        restored = 0
        for file_path, content in files:
            try:
                full_path = os.path.join(project_root, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                log_info(f"  ✓ {file_path}")
                restored += 1
            except IOError as e:
                log_warning(f"  ✗ {file_path}: {e}")
        
        log_success(f"Przywrócono {restored}/{len(files)} plików.")
        return 0
    
    # Waliduj konfigurację przed rozpoczęciem pracy
    validate_config_paths(config)

    files_to_process = get_files_to_dump(args.paths, start_dir, project_root, git_root, config)
    
    if not files_to_process:
        log_info("Nie znaleziono żadnych plików pasujących do kryteriów.")
        return 0

    total_lines = 0
    all_content = []
    for file_path in files_to_process:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                total_lines += content.count('\n') + 1
                all_content.append(content)
        except IOError:
            continue

    text_for_tokens = "\n\n".join(all_content)
    token_count_info = ""
    try:
        encoding = tiktoken.encoding_for_model("gpt-4")
        num_tokens = len(encoding.encode(text_for_tokens))
        token_count_info = f", {num_tokens:,} tokenów".replace(',', ' ')
    except Exception:
        pass  # tiktoken not installed or other issue

    log_info(f"Znaleziono {len(files_to_process)} plików do przetworzenia (łącznie {total_lines:,} linii kodu{token_count_info}).".replace(',', ' '))


    hide_env = config.get('hide_env', True)
    output_parts = [
        format_file_content(f, project_root, config['extension_lang_map'], hide_env=hide_env) 
        for f in files_to_process
    ]
    
    # Cleanup old dumps (>7 days)
    removed = cleanup_old_dumps(output_dir_path, max_age_days=7)
    if removed > 0:
        log_info(f"Automatycznie usunięto {removed} starych dumpów (>7 dni).")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f"{timestamp}-repo-dump.txt"
    output_filepath = os.path.join(output_dir_path, output_filename)

    try:
        dump_text = "\n\n".join(output_parts)
        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(dump_text)
        pyperclip.copy(dump_text)
    except IOError as e:
        log_error(f"Nie można zapisać do pliku '{output_filepath}': {e}")
    
    log_success(f"Pomyślnie utworzono dump w pliku: {output_filepath}")
    log_info(f"Użyj 'dump-repo --list' aby przeglądać dumpy.")
    return 0
# --- KONIEC NOWEJ IMPLEMENTACJI ---
