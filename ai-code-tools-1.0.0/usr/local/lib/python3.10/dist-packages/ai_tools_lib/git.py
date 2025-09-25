import argparse
import os
import re
import subprocess
from datetime import datetime
import pyperclip
from .helpers import (log_error, log_info, log_success, format_file_content,
                      get_config, find_project_root, find_git_root)

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

def main():
    start_dir = os.getcwd()
    project_root = find_project_root(start_dir)
    git_root = find_git_root(start_dir)
    config = get_config(project_root)

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

    log_info(f"Znaleziono {len(files_to_process)} zmienionych plików do przetworzenia.")
    
    # Ścieżki z git są względne do git_root, więc tworzymy ścieżki absolutne
    absolute_paths = [os.path.join(git_root, path) for path in sorted(list(files_to_process))]
    
    output_parts = [
        format_file_content(path, project_root, config.get('extension_lang_map', {})) 
        for path in absolute_paths
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