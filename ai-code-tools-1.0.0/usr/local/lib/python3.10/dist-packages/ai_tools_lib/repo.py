import argparse
import fnmatch
import os
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

def load_gitignore_patterns(git_root):
    if not git_root: return []
    gitignore_path = os.path.join(git_root, '.gitignore')
    if not os.path.exists(gitignore_path): return []
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def is_path_match(rel_path, patterns):
    path_to_check = rel_path.replace(os.path.sep, '/')
    for pattern in patterns:
        if pattern.endswith('/'):
            if path_to_check.startswith(pattern) or path_to_check == pattern.rstrip('/'):
                return True
        if fnmatch.fnmatch(path_to_check, pattern):
            return True
    return False

def get_files_to_dump(paths_to_scan, start_dir, project_root, git_root, config):
    DEFAULT_BLACKLIST = ['.git/']
    
    whitelisted_patterns = config['whitelisted_paths']
    blacklisted_patterns_config = config['blacklisted_paths']
    gitignore_patterns = load_gitignore_patterns(git_root)
    
    files_to_include = set()

    # --- POPRAWIONA, NIEZAWODNA LOGIKA WYKLUCZANIA ---
    output_dir_abs = os.path.abspath(os.path.join(project_root, config['output_dir']))
    config_file_abs = os.path.abspath(os.path.join(project_root, CONFIG_FILENAME))
    # --- KONIEC POPRAWKI ---

    for path_arg in paths_to_scan:
        abs_path_arg = os.path.abspath(os.path.join(start_dir, path_arg))
        
        if not os.path.exists(abs_path_arg):
            log_warning(f"Podana ścieżka nie istnieje i została pominięta: {path_arg}")
            continue
        
        if os.path.isfile(abs_path_arg):
             if not is_binary(abs_path_arg):
                files_to_include.add(abs_path_arg)
             continue

        for root, dirs, files in os.walk(abs_path_arg, topdown=True):
            for filename in files:
                file_abs_path = os.path.join(root, filename)
                rel_path_from_project = os.path.relpath(file_abs_path, project_root)

                # --- POPRAWIONA, NIEZAWODNA LOGIKA WYKLUCZANIA ---
                if file_abs_path.startswith(output_dir_abs) or file_abs_path == config_file_abs:
                    continue
                # --- KONIEC POPRAWKI ---
                
                if is_path_match(rel_path_from_project, whitelisted_patterns):
                    if not is_binary(file_abs_path):
                        files_to_include.add(file_abs_path)
                    continue
                
                # Łączymy twardą listę z konfiguracyjną
                if is_path_match(rel_path_from_project, DEFAULT_BLACKLIST + blacklisted_patterns_config):
                    continue

                if git_root:
                    rel_path_from_git = os.path.relpath(file_abs_path, git_root)
                    if is_path_match(rel_path_from_git, gitignore_patterns):
                        continue
                
                if not is_binary(file_abs_path):
                    files_to_include.add(file_abs_path)
    
    return sorted(list(files_to_include))

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

    log_info(f"Znaleziono {len(files_to_process)} plików do przetworzenia.")

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