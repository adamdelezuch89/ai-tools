import argparse
import fnmatch
import os
import subprocess
from datetime import datetime
import pyperclip
from .helpers import (log_error, log_info, log_success, log_warning,
                      format_file_content, get_config, find_project_root,
                      find_git_root, CONFIG_FILENAME)

def is_binary(filepath, chunk_size=1024):
    try:
        with open(filepath, 'rb') as f:
            return b'\0' in f.read(chunk_size)
    except IOError: return True

def normalize_path_pattern(pattern):
    """
    Normalizuje wzorzec ścieżki:
    - Zamienia backslashe na forwardslashe
    - Usuwa końcowy ukośnik (będzie dodany przy porównaniach katalogów)
    """
    normalized = pattern.replace(os.path.sep, '/').rstrip('/')
    return normalized

def is_directory_pattern(pattern):
    """
    Sprawdza czy wzorzec reprezentuje katalog (nie zawiera wildcardów).
    """
    return '*' not in pattern and '?' not in pattern and '[' not in pattern

def is_path_match(rel_path, patterns):
    """
    Sprawdza czy ścieżka pasuje do któregoś z wzorców.
    Obsługuje katalogi z ukośnikiem i bez, oraz wildcardy.
    """
    path_to_check = rel_path.replace(os.path.sep, '/')
    
    for pattern in patterns:
        normalized_pattern = normalize_path_pattern(pattern)
        
        # Jeśli to wzorzec katalogu (bez wildcardów)
        if is_directory_pattern(pattern):
            # Sprawdź czy ścieżka jest w tym katalogu lub jest tym katalogiem
            if path_to_check.startswith(normalized_pattern + '/') or path_to_check == normalized_pattern:
                return True
        
        # Wildcardy - użyj fnmatch
        if fnmatch.fnmatch(path_to_check, normalized_pattern):
            return True
            
    return False

def find_most_specific_match(rel_path, patterns):
    """
    Znajduje najbardziej specyficzny (najdłuższy) wzorzec pasujący do ścieżki.
    Zwraca krotkę (pattern, specificity) lub (None, 0) jeśli brak dopasowania.
    """
    path_to_check = rel_path.replace(os.path.sep, '/')
    best_match = None
    best_specificity = 0
    
    for pattern in patterns:
        normalized_pattern = normalize_path_pattern(pattern)
        
        # Sprawdź czy pasuje
        matches = False
        specificity = 0
        
        if is_directory_pattern(pattern):
            # Dla katalogów: sprawdź prefix
            if path_to_check.startswith(normalized_pattern + '/') or path_to_check == normalized_pattern:
                matches = True
                # Specyficzność = długość ścieżki (więcej segmentów = bardziej specyficzne)
                specificity = normalized_pattern.count('/') + 1
        elif fnmatch.fnmatch(path_to_check, normalized_pattern):
            # Dla wildcardów: również pasuje, ale z niższą specyficznością
            matches = True
            specificity = normalized_pattern.count('/') + 0.5  # Wildcardy mają niższą specyficzność
        
        if matches and specificity > best_specificity:
            best_match = normalized_pattern
            best_specificity = specificity
    
    return (best_match, best_specificity)

def validate_config_paths(config):
    """
    Waliduje konfigurację sprawdzając konflikty między whitelist i blacklist.
    Rzuca ostrzeżeniem jeśli ta sama ścieżka jest w obu listach.
    """
    whitelisted = config.get('whitelisted_paths', [])
    blacklisted = config.get('blacklisted_paths', [])
    
    # Normalizuj wszystkie ścieżki dla porównania
    normalized_whitelist = {normalize_path_pattern(p) for p in whitelisted}
    normalized_blacklist = {normalize_path_pattern(p) for p in blacklisted}
    
    # Znajdź konflikty
    conflicts = normalized_whitelist & normalized_blacklist
    
    if conflicts:
        conflicts_list = ', '.join(f'"{c}"' for c in sorted(conflicts))
        log_error(f"NIEPRAWIDŁOWA KONFIGURACJA: Następujące ścieżki występują zarówno w whitelisted_paths jak i blacklisted_paths: {conflicts_list}. "
                  f"Usuń konflikty z pliku konfiguracyjnego '{CONFIG_FILENAME}'.")

# --- POCZĄTEK NOWEJ IMPLEMENTACJI ---
def get_files_to_dump(paths_to_scan, start_dir, project_root, git_root, config):
    whitelisted_patterns = config.get('whitelisted_paths', [])
    # Dodajemy .gitignore do domyślnej czarnej listy, aby sam plik nie był dumpowany
    blacklisted_patterns = config.get('blacklisted_paths', []) + ['.git/', '.gitignore']
    output_dir_abs = os.path.abspath(os.path.join(project_root, config['output_dir']))
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
        if not (f_path.startswith(output_dir_abs) or f_path == config_file_abs or is_binary(f_path))
    }

    return sorted(list(final_files_cleaned))

def main():
    start_dir = os.getcwd()
    project_root = find_project_root(start_dir)
    git_root = find_git_root(start_dir)
    config = get_config(project_root)
    
    # Waliduj konfigurację przed rozpoczęciem pracy
    validate_config_paths(config)

    parser = argparse.ArgumentParser(description="Tworzy dump zawartości plików z projektu.")
    parser.add_argument('paths', nargs='*', default=['.'], help="Lista ścieżek do przetworzenia (względem bieżącego katalogu).")
    args = parser.parse_args()

    files_to_process = get_files_to_dump(args.paths, start_dir, project_root, git_root, config)
    
    if not files_to_process:
        log_info("Nie znaleziono żadnych plików pasujących do kryteriów.")
        return 0

    total_lines = 0
    for file_path in files_to_process:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                total_lines += sum(1 for _ in f)
        except IOError: continue
    log_info(f"Znaleziono {len(files_to_process)} plików do przetworzenia (łącznie {total_lines} linii kodu).")

    output_parts = [format_file_content(f, project_root, config['extension_lang_map']) for f in files_to_process]
    
    output_dir_path = os.path.join(project_root, config['output_dir'])
    os.makedirs(output_dir_path, exist_ok=True)
    
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
        
    log_success(f"Pomyślnie utworzono dump w pliku: {os.path.relpath(output_filepath, start_dir)}")
    return 0
# --- KONIEC NOWEJ IMPLEMENTACJI ---
