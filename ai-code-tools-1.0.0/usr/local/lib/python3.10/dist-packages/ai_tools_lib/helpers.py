import logging
import os
import sys
import subprocess
import yaml

# --- Stałe ---
CONFIG_FILENAME = ".ai-tools-config.yaml"

# --- Konfiguracja Logowania ---
logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stdout)
logger = logging.getLogger('ai_tools')
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def log_info(message): logger.info(message)
def log_success(message): logger.info(f"{GREEN}✔ {message}{RESET}")
def log_warning(message): logger.warning(f"{YELLOW}⚠ {message}{RESET}")
def log_error(message):
    logger.error(f"{RED}✖ BŁĄD: {message}{RESET}")
    sys.exit(1)

# --- Wyszukiwanie Katalogów Głównych (Z POPRAWKĄ) ---
def find_project_root(start_path):
    """
    Przeszukuje drzewo katalogów w górę w poszukiwaniu pliku konfiguracyjnego.
    Jeśli plik zostanie znaleziony, zwraca ścieżkę do jego katalogu.
    Jeśli nie, zwraca oryginalną ścieżkę startową (cwd).
    """
    current_path = os.path.abspath(start_path)
    while True:
        if os.path.exists(os.path.join(current_path, CONFIG_FILENAME)):
            return current_path
        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:
            # Nie znaleziono pliku, użyj katalogu startowego jako domyślnego root'a
            log_info(f"Nie znaleziono pliku '{CONFIG_FILENAME}'. Używam wartości domyślnych.")
            return os.path.abspath(start_path)
        current_path = parent_path

def find_git_root(start_path):
    """Znajduje główny katalog repozytorium Git."""
    try:
        git_root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            text=True,
            encoding='utf-8',
            cwd=start_path,
            stderr=subprocess.PIPE
        ).strip()
        return git_root
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

# --- Obsługa Konfiguracji ---
def get_config(project_root):
    DEFAULT_CONFIG = {
        'output_dir': '.ai-tools-output',
        'blacklisted_paths': [],
        'whitelisted_paths': [],
        'extension_lang_map': {}
    }

    config_path = os.path.join(project_root, CONFIG_FILENAME)

    if not os.path.exists(config_path):
        return DEFAULT_CONFIG

    log_info(f"Znaleziono plik konfiguracyjny: {config_path}")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError) as e:
        log_error(f"Nie można odczytać lub przetworzyć pliku '{config_path}': {e}")

    final_config = DEFAULT_CONFIG.copy()
    final_config.update(user_config)

    if 'output_dir' not in final_config or not final_config['output_dir']:
        log_error("Klucz 'output_dir' w pliku konfiguracyjnym nie może być pusty.")

    if final_config.get('whitelisted_paths') is None:
        final_config['whitelisted_paths'] = []
    if final_config.get('blacklisted_paths') is None:
        final_config['blacklisted_paths'] = []

    return final_config

# --- Operacje na Plikach (bez zmian) ---
def format_file_content(file_path, project_root, extension_map):
    rel_path = os.path.relpath(file_path, project_root).replace(os.path.sep, '/')
    file_ext = os.path.splitext(rel_path)[1]
    lang = extension_map.get(file_ext, '')
    
    header = f"---\nFile: {rel_path}\n---\n"
    code_block_start = f"```{lang}\n"
    code_block_end = "\n```"
    
    content = ""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except FileNotFoundError:
        log_warning(f"Plik '{rel_path}' nie został znaleziony. Zostanie oznaczony w dumpie.")
        content = f"[BŁĄD: Plik nie został znaleziony na dysku.]"
    except Exception as e:
        log_warning(f"Nie można odczytać pliku '{rel_path}'. Powód: {e}")
        content = f"[BŁĄD: Nie można odczytać pliku. Powód: {e}]"
        
    return f"{header}{code_block_start}{content}{code_block_end}"