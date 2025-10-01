"""
Configuration management for ai-tools.

Handles loading and parsing of .ai-tools-config.yaml files and finding project roots.
"""

import os
import subprocess
import tempfile
import yaml


CONFIG_FILENAME = ".ai-tools-config.yaml"


def get_default_output_dir():
    """
    Get default output directory in system temp.
    
    Returns path suitable for legacy config, but new code should use
    get_project_temp_dir() from temp_storage module instead.
    
    Returns:
        Path to system temp directory
    """
    return os.path.join(tempfile.gettempdir(), 'ai-tools-dumps')

# Default configuration template with comments
DEFAULT_CONFIG_TEMPLATE = """# Konfiguracja ai-tools
# Dokumentacja: https://github.com/adamdelezuch89/ai-tools

# Nota: Dumpy są automatycznie zapisywane w /tmp/ai-tools/<projekt>/<tool>/
# i czyszczone po 7 dniach. Nie musisz konfigurować output_dir.

# [OPCJONALNE] Ukrywanie wrażliwych wartości z plików .env
# Automatycznie maskuje API keys, hasła, tokeny z .env jako [HIDDEN_ENV_VALUE]
# Skanowane pliki: .env, .env.local, .env.development, .env.production
# Zalecane: true (domyślnie)
hide_env: true

# [OPCJONALNE] Dodatkowe mapowanie rozszerzeń plików
# System ma wbudowane 40+ popularnych rozszerzeń (.js, .py, .ts, etc.)
# Dodaj tutaj tylko niestandardowe rozszerzenia
extension_lang_map:
  # .custom: customlang

# [OPCJONALNE] Ścieżki do wykluczenia (blacklist)
# Obsługuje katalogi (z/bez ukośnika) i wzorce wildcard (*.lock)
blacklisted_paths:
  - "node_modules"
  - ".venv/"
  - "dist/"
  - "build/"
  - "*.lock"
  # - "*.log"

# [OPCJONALNE] Ścieżki do ZAWSZE dołączenia (whitelist)
# Ma wyższy priorytet niż .gitignore
# Bardziej specyficzna reguła wygrywa (np. vendor/libs/ > vendor/)
whitelisted_paths:
  # - ".github/workflows/"

# Przykłady zaawansowane:
# 
# Wykluczenie całego katalogu ale załączenie podkatalogu:
#   blacklisted_paths:
#     - "build/"
#   whitelisted_paths:
#     - "build/config/"
#
# Wykluczenie podkatalogu w załączonym katalogu:
#   whitelisted_paths:
#     - "docs/"
#   blacklisted_paths:
#     - "docs/internal/"
"""


def create_default_config(project_root):
    """
    Create default .ai-tools-config.yaml file.
    
    Args:
        project_root: Directory where config file should be created
        
    Returns:
        Path to created config file
        
    Raises:
        FileExistsError: If config file already exists
        IOError: If unable to write file
    """
    config_path = os.path.join(project_root, CONFIG_FILENAME)
    
    if os.path.exists(config_path):
        raise FileExistsError(f"Plik konfiguracyjny już istnieje: {config_path}")
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_CONFIG_TEMPLATE)
        return config_path
    except IOError as e:
        raise IOError(f"Nie można utworzyć pliku konfiguracyjnego: {e}")


def find_project_root(start_path):
    """
    Search up the directory tree for the configuration file.
    
    If found, returns the directory containing it.
    If not found, returns the original start path (cwd).
    
    Args:
        start_path: Directory to start searching from
        
    Returns:
        Path to project root directory
    """
    current_path = os.path.abspath(start_path)
    
    while True:
        if os.path.exists(os.path.join(current_path, CONFIG_FILENAME)):
            return current_path
        
        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:
            # Reached root - not found, use start path as default
            from ai_tools.utils.logger import log_info
            log_info(f"Nie znaleziono pliku '{CONFIG_FILENAME}'. Używam wartości domyślnych.")
            return os.path.abspath(start_path)
        
        current_path = parent_path


def find_git_root(start_path):
    """
    Find the root directory of a Git repository.
    
    Args:
        start_path: Directory to start searching from
        
    Returns:
        Path to git root, or None if not in a git repository
    """
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


def get_config(project_root):
    """
    Load configuration from .ai-tools-config.yaml file.
    
    Returns default configuration if file doesn't exist or can't be read.
    
    Args:
        project_root: Root directory containing the config file
        
    Returns:
        Dictionary with configuration values
    """
    # Default extension to language mapping (most popular languages)
    DEFAULT_EXTENSION_MAP = {
        # Web
        '.js': 'javascript',
        '.jsx': 'jsx',
        '.ts': 'typescript',
        '.tsx': 'tsx',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.vue': 'vue',
        
        # Backend
        '.py': 'python',
        '.rb': 'ruby',
        '.php': 'php',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cs': 'csharp',
        '.swift': 'swift',
        '.kt': 'kotlin',
        
        # Data & Config
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.xml': 'xml',
        '.sql': 'sql',
        '.graphql': 'graphql',
        
        # Shell & Scripts
        '.sh': 'bash',
        '.bash': 'bash',
        '.zsh': 'zsh',
        '.fish': 'fish',
        '.ps1': 'powershell',
        
        # Documentation
        '.md': 'markdown',
        '.mdx': 'mdx',
        '.rst': 'rst',
        '.txt': 'text',
        
        # Other
        '.r': 'r',
        '.lua': 'lua',
        '.dart': 'dart',
        '.elm': 'elm',
    }
    
    DEFAULT_CONFIG = {
        'output_dir': None,  # Will be set to temp dir by tools
        'blacklisted_paths': [],
        'whitelisted_paths': [],
        'extension_lang_map': DEFAULT_EXTENSION_MAP.copy(),
        'hide_env': True  # Hide sensitive values from .env files by default
    }
    
    config_path = os.path.join(project_root, CONFIG_FILENAME)
    
    if not os.path.exists(config_path):
        return DEFAULT_CONFIG
    
    from ai_tools.utils.logger import log_info, log_error
    log_info(f"Znaleziono plik konfiguracyjny: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError) as e:
        log_error(f"Nie można odczytać lub przetworzyć pliku '{config_path}': {e}")
    
    final_config = DEFAULT_CONFIG.copy()
    
    # Merge extension_lang_map specially - user config extends defaults
    if 'extension_lang_map' in user_config and user_config['extension_lang_map']:
        final_config['extension_lang_map'] = DEFAULT_EXTENSION_MAP.copy()
        final_config['extension_lang_map'].update(user_config['extension_lang_map'])
    
    # Update other config values
    for key, value in user_config.items():
        if key != 'extension_lang_map':  # Already handled
            final_config[key] = value
    
    # output_dir is now optional - tools will use temp dir if not specified
    
    if final_config.get('whitelisted_paths') is None:
        final_config['whitelisted_paths'] = []
    if final_config.get('blacklisted_paths') is None:
        final_config['blacklisted_paths'] = []
    
    return final_config
