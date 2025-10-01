import argparse
import os
import re
import subprocess
from datetime import datetime
import pyperclip
from .helpers import (log_error, log_info, log_success, format_file_content,
                      get_config, find_project_root, find_git_root, CONFIG_FILENAME)
# Importujemy funkcje pomocnicze z repo.py
from .repo import (normalize_path_pattern, is_directory_pattern, 
                   find_most_specific_match, validate_config_paths, is_binary)

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
    output_dir_abs = os.path.abspath(os.path.join(project_root, config['output_dir']))
    config_file_abs = os.path.abspath(os.path.join(project_root, CONFIG_FILENAME))
    
    filtered_files = []
    
    for file_path in files:
        # Jeśli ścieżka jest już absolutna, użyj jej; w przeciwnym razie zbuduj absolutną
        if os.path.isabs(file_path):
            abs_path = file_path
        else:
            abs_path = os.path.join(project_root, file_path)
        
        # Pomiń pliki binarne, output dir i config file
        if is_binary(abs_path) or abs_path.startswith(output_dir_abs) or abs_path == config_file_abs:
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
    
    # Waliduj konfigurację przed rozpoczęciem pracy
    validate_config_paths(config)

    if not git_root:
        log_error("Nie znajdujesz się w repozytorium Git.")

    parser = argparse.ArgumentParser(description="Tworzy dump zmian w repozytorium Git.")
    parser.add_argument('--staged', action='store_true', help='Dumpuje tylko pliki staged.')
    parser.add_argument('--unstaged', action='store_true', help='Dumpuje pliki unstaged oraz untracked.')
    args = parser.parse_args()

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
    
    # Zliczanie linii kodu
    total_lines = 0
    for file_path in filtered_paths:
        try:
            if not os.path.exists(file_path): 
                continue
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                total_lines += sum(1 for _ in f)
        except IOError:
            continue
    log_info(f"Znaleziono {len(filtered_paths)} zmienionych plików do przetworzenia (łącznie {total_lines} linii kodu).")
    
    output_parts = [
        format_file_content(path, project_root, config.get('extension_lang_map', {})) 
        for path in filtered_paths
    ]

    output_dir_path = os.path.join(project_root, config['output_dir'])
    os.makedirs(output_dir_path, exist_ok=True)

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

    log_success(f"Pomyślnie utworzono dump w pliku: {os.path.relpath(output_path, start_dir)}")
    return 0
