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

def run_git_command(command, cwd):
    """Uruchamia polecenie git i zwraca jego wyjście."""
    try:
        return subprocess.check_output(command, text=True, encoding='utf-8', cwd=cwd).strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        log_error(f"Błąd wykonania polecenia git: {e}")
        return ""

def get_files_by_status(command, cwd):
    """Pobiera listę plików dla danego statusu git."""
    output = run_git_command(command, cwd)
    return [line.split('\t')[-1] for line in output.split('\n') if line]

def filter_files_by_config(files, project_root, config):
    """
    Filtruje pliki według blacklist/whitelist z konfiguracji.
    Używa tej samej logiki co w repo.py - bardziej specyficzna reguła wygrywa.
    """
    whitelisted_patterns = config.get('whitelisted_paths', [])
    blacklisted_patterns = config.get('blacklisted_paths', []) + ['.git/', '.gitignore']
    config_file_abs = os.path.abspath(os.path.join(project_root, CONFIG_FILENAME))
    
    filtered_files = []
    
    for file_path in files:
        # Jeśli ścieżka jest już absolutna, użyj jej; w przeciwnym razie zbuduj absolutną
        if os.path.isabs(file_path):
            abs_path = file_path
        else:
            abs_path = os.path.join(project_root, file_path)
        
        # Pomiń pliki binarne i config file
        if is_binary(abs_path) or abs_path == config_file_abs:
            continue
        
        rel_path = os.path.relpath(abs_path, project_root)
        
        # Znajdź najbardziej specyficzne dopasowania
        whitelist_match, whitelist_spec = find_most_specific_match(rel_path, whitelisted_patterns)
        blacklist_match, blacklist_spec = find_most_specific_match(rel_path, blacklisted_patterns)
        
        # Logika decyzyjna (taka sama jak w repo.py)
        should_include = False
        
        if whitelist_spec > 0 and blacklist_spec > 0:
            # Oba pasują - bardziej specyficzny wygrywa
            if whitelist_spec > blacklist_spec:
                should_include = True
            elif blacklist_spec > whitelist_spec:
                should_include = False
            else:
                # Ta sama specyficzność - blacklist wygrywa
                should_include = False
        elif whitelist_spec > 0:
            # Tylko whitelist - załącz
            should_include = True
        elif blacklist_spec > 0:
            # Tylko blacklist - wyklucz
            should_include = False
        else:
            # Brak reguł - domyślnie załącz (plik był zwrócony przez git)
            should_include = True
        
        if should_include:
            filtered_files.append(abs_path)
    
    return filtered_files

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

Co będzie dumpowane:
  ✓ Pliki zmienione w Git (staged/unstaged/untracked)
  ✓ Pliki z whitelist (jeśli zmienione)
  ✗ Pliki z blacklist (nawet jeśli zmienione)
  ✗ Pliki binarne
  ✗ Wrażliwe wartości z .env (jeśli hide_env=true)
        '''
    else:
        epilog_text = '''
Nie znaleziono pliku konfiguracyjnego.

Utwórz plik konfiguracyjny:
  dump-git --init

Co będzie dumpowane (domyślnie):
  ✓ Wszystkie pliki zmienione w Git
  ✗ Pliki binarne
  ✗ Wrażliwe wartości z .env (automatycznie ukryte)
        '''
    
    parser = argparse.ArgumentParser(
        description="Tworzy dump zmian w repozytorium Git",
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--init', action='store_true',
                       help='Utwórz plik konfiguracyjny .ai-tools-config.yaml')
    parser.add_argument('--list', action='store_true',
                       help='Pokaż ostatnie dumpy (interaktywne przywracanie)')
    parser.add_argument('--restore', nargs='?', const='', metavar='N',
                       help='Przywróć pliki z dumpu (1=ostatni, 2=przedostatni, puste=ostatni)')
    parser.add_argument('--staged', action='store_true', 
                       help='Tylko pliki staged (git add)')
    parser.add_argument('--unstaged', action='store_true', 
                       help='Tylko pliki unstaged i untracked')
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
    output_dir_path = get_project_temp_dir(project_root, 'dump-git')
    
    # Handle --list flag
    if args.list:
        dumps = list_recent_dumps(output_dir_path, limit=20)
        
        if not dumps:
            log_info("Brak dumpów git dla tego projektu.")
            return 0
        
        log_info(f"Ostatnie dumpy git dla projektu ({len(dumps)}):\n")
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

    if not git_root:
        log_error("Nie znajdujesz się w repozytorium Git.")

    files_to_process = set()
    dump_type = "git-all"

    staged_files = get_files_by_status(['git', 'diff', '--name-only', '--cached'], git_root)
    unstaged_files = get_files_by_status(['git', 'diff', '--name-only'], git_root)
    untracked_files = get_files_by_status(['git', 'ls-files', '--others', '--exclude-standard'], git_root)

    if args.staged:
        files_to_process.update(staged_files)
        dump_type = "git-staged"
    elif args.unstaged:
        files_to_process.update(unstaged_files)
        files_to_process.update(untracked_files)
        dump_type = "git-unstaged"
    else:
        files_to_process.update(staged_files)
        files_to_process.update(unstaged_files)
        files_to_process.update(untracked_files)
    
    if not files_to_process:
        log_info("Brak zmian do zdumpowania.")
        return 0

    # Ścieżki z git są względne do git_root, więc tworzymy ścieżki absolutne
    absolute_paths = [os.path.join(git_root, path) for path in sorted(list(files_to_process))]
    
    # Filtruj pliki według blacklist/whitelist
    filtered_paths = filter_files_by_config(absolute_paths, project_root, config)
    
    if not filtered_paths:
        log_info("Brak plików do zdumpowania po zastosowaniu filtrów.")
        return 0
    
    # Zliczanie linii kodu i tokenów
    total_lines = 0
    all_content = []
    for file_path in filtered_paths:
        try:
            if not os.path.exists(file_path): 
                continue
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

    log_info(f"Znaleziono {len(filtered_paths)} zmienionych plików do przetworzenia (łącznie {total_lines:,} linii kodu{token_count_info}).".replace(',', ' '))
    
    hide_env = config.get('hide_env', True)
    output_parts = [
        format_file_content(path, project_root, config.get('extension_lang_map', {}), hide_env=hide_env) 
        for path in filtered_paths
    ]

    # Cleanup old dumps (>7 days)
    removed = cleanup_old_dumps(output_dir_path, max_age_days=7)
    if removed > 0:
        log_info(f"Automatycznie usunięto {removed} starych dumpów (>7 dni).")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}-{dump_type}.txt"
    output_path = os.path.join(output_dir_path, filename)
    
    try:
        dump_text = "\n\n".join(output_parts)
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write(dump_text)
        pyperclip.copy(dump_text)
    except IOError as e:
        log_error(f"Nie można zapisać do pliku '{output_path}': {e}")

    log_success(f"Pomyślnie utworzono dump w pliku: {output_path}")
    log_info(f"Użyj 'dump-git --list' aby przeglądać dumpy.")
    return 0
