# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-01

### Added
- **🔒 Security: Environment variable hiding** - NEW CRITICAL FEATURE
  - Automatically hides sensitive values from `.env` files in dumps
  - Scans `.env`, `.env.local`, `.env.development`, `.env.production`
  - Replaces all occurrences with `[HIDDEN_ENV_VALUE]`
  - **Enabled by default** (`hide_env: true` in config)
  - Prevents API keys, passwords, and tokens from leaking
  - 20 comprehensive tests for env parsing and masking
  - 91.67% test coverage for security module
  - New module: `utils/security.py`
  
- **Advanced file filtering** - Blacklist/whitelist with priority system
  - Directories without trailing slashes now work correctly
  - Nested path prioritization (more specific rules win)
  - Conflict detection between blacklist and whitelist
  - Smart pattern matching with wildcards
  
- **Comprehensive testing** - 92 unit tests (+20 from v0.1.0)
  - 12 tests for `dump-repo` command
  - 8 tests for `dump-git` command
  - 20 tests for security (env hiding) 🆕
  - 52 tests for helpers and patcher modules
  - **80.79% overall code coverage** ⬆️ from 79.27%
  
- **Default extension mapping** - Built-in support for 40+ file extensions 🆕
  - Web: `.js`, `.jsx`, `.ts`, `.tsx`, `.html`, `.css`, `.scss`, `.vue`
  - Backend: `.py`, `.rb`, `.php`, `.java`, `.go`, `.rs`, `.c`, `.cpp`, `.cs`, `.swift`, `.kt`
  - Data: `.json`, `.yaml`, `.toml`, `.xml`, `.sql`, `.graphql`
  - Shell: `.sh`, `.bash`, `.zsh`, `.fish`, `.ps1`
  - Docs: `.md`, `.mdx`, `.rst`, `.txt`
  - User config only needs to add custom extensions (extends defaults)
  
- **Dynamic help messages** - Context-aware --help for all commands 🆕
  - Shows current configuration status (if config file exists)
  - Displays example config (if no config file)
  - Lists what will be dumped based on current settings
  - Real-time stats: blacklist/whitelist count, hide_env status
  
- **Configuration management** - Easy setup and maintenance 🆕
  - `--init` flag to create default config file with helpful comments
  - `--list` flag to browse recent dumps (clickable links + restore option)
  - `--restore` flag to restore files from dump (supports HEAD, HEAD~N, filename, index)
  - Config file has detailed comments explaining all options
  - Quick start: `dump-repo --init` → edit config → `dump-repo`
  
- **Token Counting** - Know your context size  TOKEN 
  - Added token counting for `dump-repo` and `dump-git` using `tiktoken`
  - Summary now shows file count, line count, and estimated tokens
  - `tiktoken` is now vendored with the `.deb` package for seamless installation
- **Smart temp storage** - No more `.dump-outputs` clutter  TEMP 
  - Dumps are now stored in system's temporary directory (e.g., `/tmp`)
  - Each project gets separate directory (identified by path hash)
  - Automatic cleanup of dumps older than 7 days
  - No manual cleanup needed - system handles it
  - Survives between sessions until auto-cleaned
  
- **Restore functionality** - Travel back in time 🆕
  - `dump-repo --restore` restores files from latest dump
  - Simple numbering: `1` (latest), `2` (second latest), `3` (third latest), etc.
  - Empty or no number defaults to latest (1)
  - Can restore by exact filename or number
  - Interactive mode via `--list` (clickable file links + restore prompt)
  - Separate dump history for repo vs git commands
  - Tested with comprehensive unit tests
  
- **Modular architecture** - Complete code refactoring
  - `core/file_filter.py` - File filtering logic (83 lines)
  - `core/patch_ops.py` - Patch parsing and application (82 lines)
  - `utils/config.py` - Configuration management (255 lines)
  - `utils/logger.py` - Logging utilities (19 lines)
  - `utils/filesystem.py` - File operations (23 lines)
  - `utils/security.py` - Security functions (173 lines) 🆕
  - `utils/temp_storage.py` - Temp directory management (121 lines) 🆕
  - `utils/helpers.py` - Legacy wrapper for backward compatibility (5 lines)
  
- **Code coverage reporting**
  - Pytest integration with pytest-cov
  - HTML coverage reports
  - `scripts/run_tests.sh` for easy testing with coverage
  - `scripts/clean.sh` for cleaning temporary files 🆕
  
- **Professional structure** - Ready for PyPI
  - Proper Python package structure with `setup.py`
  - Development mode installation support (`pip install -e .`)
  - Comprehensive documentation
  - pytest.ini and .coveragerc configuration files

### Changed
- **Storage location** - Moved from project-local to system temp
  - Dumps now in `/tmp/ai-tools/` instead of project directory
  - Each project has unique subdirectory (hash-based)
  - Prevents cluttering project directories
  - Works across all projects in the system
  
- **Refactored codebase** - From monolithic to modular
  - Extracted common filtering logic from `dump_repo.py` and `dump_git.py`
  - Separated 278-line `helpers.py` into 8 focused modules
  - **Zero code duplication** between CLI commands
  
- **Enhanced security** - format_file_content() now accepts `hide_env` parameter
  - Both `dump-repo` and `dump-git` use env hiding by default
  - Can be controlled via config file
  
- **Simplified configuration** - output_dir no longer required
  - System automatically handles temp directory
  - Config file focuses on filtering and security
  
- Updated configuration validation to detect conflicts
- Improved README with comprehensive documentation
- Test files moved to main project directory
- All imports updated to use new modular structure

### Fixed
- Blacklisted directories without trailing slash now work correctly
- Whitelisted files in blacklisted directories are now properly included
- Conflict detection between normalized paths (e.g., "src" vs "src/")
- Empty .env values are now correctly ignored

### Security
- **IMPORTANT:** Enable `hide_env: true` (default) to prevent leaking:
  - API keys
  - Database passwords
  - Secret tokens
  - OAuth credentials
  - Any sensitive configuration values

## [0.9.0] - 2024 (Previous version)

### Added
- Initial release with basic functionality
- `dump-repo` command for repository dumps
- `dump-git` command for changed files
- `ai-patch` command for applying AI-generated changes
- Basic blacklist/whitelist support
- .gitignore integration
