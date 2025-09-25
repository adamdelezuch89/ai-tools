import logging
import os
import sys
import subprocess
import yaml
import re

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
    file_ext = os.path.splitext(rel_path)
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

# --- SEKCJA PARSOWANIA ZMIAN ---

def _find_blocks_with_regex(text):
    """
    Znajduje bloki kodu najwyższego poziomu. Ignoruje wcięcia i elastycznie
    podchodzi do lokalizacji znaczników otwierających i zamykających.
    """
    pattern = re.compile(r"([`~]{3,})([^\s]*)")
    stack = []
    found_blocks = []

    for match in pattern.finditer(text):
        marker, info = match.groups()
        line_number = text.count('\n', 0, match.start()) + 1

        if stack:
            parent_block = stack[-1]
            is_potential_closer = (
                marker[0] == parent_block["marker"][0] and
                len(marker) >= len(parent_block["marker"]) and
                not info
            )

            if is_potential_closer:
                closed_block = stack.pop()
                if not stack:
                    start_offset = closed_block["content_start_offset"]
                    end_offset = match.start()
                    if end_offset > 0 and text[end_offset - 1] == '\n':
                        end_offset -= 1
                    
                    content = text[start_offset:end_offset]
                    # Zwraca 4-elementową krotkę z pozycją otwierającego znacznika
                    found_blocks.append((
                        closed_block["opening_tag_start"], 
                        start_offset, 
                        end_offset, 
                        content
                    ))
                continue

        line_end_pos = text.find('\n', match.end())
        if line_end_pos == -1:
            content_start = len(text)
        else:
            content_start = line_end_pos + 1

        stack.append({
            "marker": marker,
            "info": info,
            "line_number": line_number,
            "content_start_offset": content_start,
            "opening_tag_start": match.start() # Zapisz pozycję otwierającego znacznika
        })

    if stack:
        for open_block in stack:
            log_warning(f"Niezamknięty blok kodu, który został otwarty w linii {open_block['line_number']}")

    found_blocks.sort(key=lambda b: b[0])
    return found_blocks

def parse_patch_content(text):
    """
    Parsuje tekst w poszukiwaniu par [ścieżka pliku, zawartość bloku kodu]
    zgodnie ze ściśle określonymi zasadami.
    """
    if not text or not text.strip():
        return []

    stripped_content = text.strip()
    outer_block_match = re.fullmatch(r"```[a-zA-Z0-9]*\n(.*?)\n```", stripped_content, re.DOTALL)
    if outer_block_match:
        content_to_parse = outer_block_match.group(1)
    else:
        content_to_parse = text

    found_blocks = _find_blocks_with_regex(content_to_parse)
    if not found_blocks:
        return []

    patches = []
    last_block_end = 0
    
    alphanumeric_check = re.compile(r'[a-zA-Z0-9]')

    for opening_tag_start, block_start, block_end, code_content in found_blocks:
        # PRZESTRZEŃ DO PRZESZUKIWANIA KOŃCZY SIĘ TERAZ PRZED ZNACZNIKIEM OTWIERAJĄCYM
        search_space = content_to_parse[last_block_end:opening_tag_start]
        
        word_candidates = list(re.finditer(r'\S+', search_space))
        
        path_candidates = [
            m for m in word_candidates
            if '.' in m.group(0) or '/' in m.group(0) or '\\' in m.group(0)
        ]

        path_found_for_block = False
        if path_candidates:
            last_candidate_match = path_candidates[-1]
            
            gap_start_offset = last_candidate_match.end()
            gap_text = search_space[gap_start_offset:]
            
            # Ten warunek jest teraz bezpieczny, bo `search_space` nie zawiera ` ```python`
            if not alphanumeric_check.search(gap_text):
                path = last_candidate_match.group(0).strip('`\'"').replace('\\', '/')
                stripped_code_content = code_content.strip()
                patches.append((path, stripped_code_content))
                path_found_for_block = True
        
        if not path_found_for_block:
            block_preview = code_content.strip().split('\n', 1)
            log_warning(f"Pominięto blok kodu, bo nie znaleziono dla niego prawidłowej ścieżki: '{block_preview[:70]}...'")

        # Znajdź pozycję końca znacznika zamykającego, aby poprawnie ustawić `last_block_end`
        closing_tag_match = re.search(r'[`~]{3,}', content_to_parse[block_end:])
        if closing_tag_match:
            last_block_end = block_end + closing_tag_match.end()
        else:
            last_block_end = block_end # Fallback
    
    return patches