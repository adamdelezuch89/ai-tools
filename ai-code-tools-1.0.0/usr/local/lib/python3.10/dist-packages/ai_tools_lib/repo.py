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

def is_path_match(rel_path, patterns):
    path_to_check = rel_path.replace(os.path.sep, '/')
    for pattern in patterns:
        if pattern.endswith('/'):
            if path_to_check.startswith(pattern) or path_to_check == pattern.rstrip('/'):
                return True
        if fnmatch.fnmatch(path_to_check, pattern):
            return True
    return False

# --- POCZĄTEK OSTATECZNEJ POPRAWKI ---
def get_files_to_dump(paths_to_scan, start_dir, project_root, git_root, config):
    whitelisted_patterns = config.get('whitelisted_paths', [])
    # Dodajemy .gitignore do domyślnej czarnej listy, aby sam plik nie był dumpowany
    blacklisted_patterns = config.get('blacklisted_paths', []) + ['.git/', '.gitignore']
    output_dir_abs = os.path.abspath(os.path.join(project_root, config['output_dir']))
    config_file_abs = os.path.abspath(os.path.join(project_root, CONFIG_FILENAME))

    files_from_git = set()

    # Krok 1: Użyj `git ls-files` jako źródła prawdy o plikach nieignorowanych przez .gitignore
    if git_root:
        try:
            cmd = ['git', '-C', git_root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z']
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True)
            git_files_rel = (p for p in result.stdout.strip('\0').split('\0') if p)
            files_from_git.update(os.path.normpath(os.path.join(git_root, p)) for p in git_files_rel)
        except (subprocess.CalledProcessError, FileNotFoundError):
            log_warning("Polecenie 'git ls-files' zawiodło. Skanowanie ręczne bez uwzględnienia .gitignore.")
            # Fallback: weź wszystkie pliki, jeśli git zawiedzie
            for root, _, files in os.walk(project_root):
                for name in files: files_from_git.add(os.path.join(root, name))
    else:
        # Fallback: weź wszystkie pliki, jeśli nie jesteśmy w repo gita
        for root, _, files in os.walk(project_root):
            for name in files: files_from_git.add(os.path.join(root, name))
    
    # Krok 2: Zastosuj blacklist do plików z Gita
    files_after_blacklist = set()
    for f_path in files_from_git:
        rel_path = os.path.relpath(f_path, project_root)
        if not is_path_match(rel_path, blacklisted_patterns):
            files_after_blacklist.add(f_path)
            
    # Krok 3: Dodaj pliki z whitelist (mają wyższy priorytet niż .gitignore, ale nie niż blacklist)
    if whitelisted_patterns:
        for root, _, files in os.walk(project_root):
            for name in files:
                f_path = os.path.join(root, name)
                rel_path = os.path.relpath(f_path, project_root)
                if is_path_match(rel_path, whitelisted_patterns) and not is_path_match(rel_path, blacklisted_patterns):
                    files_after_blacklist.add(f_path)

    # Krok 4: Ogranicz do ścieżek podanych przez użytkownika (zakres)
    scan_paths_abs = [os.path.abspath(os.path.join(start_dir, p)) for p in paths_to_scan]
    files_in_scope = set()
    for f_path in files_after_blacklist:
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
# --- KONIEC OSTATECZNEJ POPRAWKI ---
