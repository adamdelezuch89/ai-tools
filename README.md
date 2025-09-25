# Narzędzia AI do Pracy z Kodem

Zestaw narzędzi wiersza poleceń dla systemów Ubuntu/Debian, przeznaczony do tworzenia zrzutów kodu dla modeli AI oraz do implementowania zmian wygenerowanych przez AI.

Narzędzia działają w kontekście "projektu", który jest definiowany przez obecność pliku `.ai-tools-config.yaml`. Wyszukiwanie projektu odbywa się od bieżącego katalogu roboczego w górę.

## Instalacja (jako paczka .deb)

Narzędzia są dystrybuowane jako standardowa paczka systemowa, co zapewnia globalną dostępność poleceń i automatyczne zarządzanie zależnościami.

1.  **Zbuduj paczkę:**
    Przejdź do katalogu `ai-code-tools-builder` i uruchom polecenie:
    ```bash
    dpkg-deb --build ai-code-tools-1.0.0
    ```
    W katalogu `ai-code-tools-builder` zostanie utworzony plik `ai-code-tools-1.0.0.deb`.

2.  **Zainstaluj paczkę:**
    Użyj `apt` do instalacji, co automatycznie pobierze wymagane zależności (np. `python3-yaml`).
    ```bash
    sudo apt install ./ai-code-tools-1.0.0.deb
    ```

Po instalacji, polecenia `dump-repo`, `dump-git` i `ai-patch` będą dostępne w całym systemie.

## Konfiguracja Projektu

Przed użyciem narzędzi, w głównym katalogu swojego projektu stwórz plik o nazwie `.ai-tools-config.yaml`.

**Lokalizacja:** `.ai-tools-config.yaml` (w głównym katalogu projektu)

**Przykładowa zawartość:**
```yaml
# [Wymagane] Katalog na wygenerowane pliki zrzutów.
# Ścieżka jest względna do głównego katalogu projektu.
output_dir: .dump-outputs

# [Opcjonalne] Mapowanie rozszerzeń na języki w blokach markdown.
extension_lang_map:
  .py: python
  .js: javascript
  .ts: typescript
  .md: markdown
  .yaml: yaml

# [Opcjonalne - dla dump-repo] Ścieżki, które mają być ZAWSZE ignorowane.
# Ma najwyższy priorytet, nawet nad .gitignore i whitelists.
blacklisted_paths:
  - "node_modules/"
  - ".venv/"
  - "dist/"
  - "*.lock"

# [Opcjonalne - dla dump-repo] Ścieżki, które mają być ZAWSZE dołączone,
# nawet jeśli znajdują się w .gitignore.
whitelisted_paths:
  - ".github/workflows/main.yaml"
```

---

## Dostępne Polecenia

### `dump-repo`
Tworzy zrzut tekstowy całego projektu lub jego wybranych części, respektując pliki `.gitignore` oraz konfigurację `blacklisted_paths` i `whitelisted_paths`.

**Użycie:**
```bash
# Zrzut całego projektu (od miejsca, gdzie znaleziono .ai-tools-config.yaml)
dump-repo

# Zrzut tylko katalogu 'src' i pliku 'package.json'
# Ścieżki są względne do głównego katalogu projektu.
dump-repo src package.json
```

### `dump-git`
Tworzy zrzut tekstowy tylko tych plików, w których wykryto niezatwierdzone zmiany w repozytorium Git.

| Opcja | Opis |
| :----------- | :--------------------------------------------------------- |
| *(brak)* | Wszystkie zmiany (`staged` + `unstaged` + `untracked`). |
| `--staged` | Tylko zmiany dodane do poczekalni (`staged`). |
| `--unstaged` | Tylko zmiany nieśledzone (`untracked`) i nie w poczekalni (`unstaged`). |

**Użycie:**
```bash
# Zrzut wszystkich niezatwierdzonych zmian
dump-git

# Zrzut tylko plików po wykonaniu 'git add'
dump-git --staged
```

### `ai-patch`
Aplikuje zmiany w kodzie na podstawie sformatowanego tekstu skopiowanego do schowka systemowego.

**Użycie:**
1.  Skopiuj do schowka cały tekst ze zmianami wygenerowany przez AI.
2.  W terminalu, będąc w katalogu, w którym chcesz zastosować zmiany (zazwyczaj główny katalog projektu), uruchom polecenie:
    ```bash
    ai-patch
    ```
Narzędzie wczyta zawartość schowka, a następnie zaktualizuje lub utworzy odpowiednie pliki.

**Format tekstu w schowku:**
Tekst musi zawierać bloki z nagłówkami `File: <ścieżka>`, po których następuje blok kodu z nową zawartością pliku.

---
File: src/components/Button.js
---
```javascript
import React from 'react';

// Nowa, poprawiona wersja komponentu
const Button = ({ onClick, children }) => {
  return (
    <button className="modern-button" onClick={onClick}>
      {children}
    </button>
  );
};

export default Button;
```

---
File: styles/buttons.css
---
```css
.modern-button {
  background-color: #007bff;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 5px;
}
```

## Testowanie

Projekt zawiera zestaw testów jednostkowych, które weryfikują poprawność działania kluczowych funkcjonalności, w tym logikę ignorowania plików i aplikowania zmian. Testy są napisane przy użyciu wbudowanego modułu `unittest` w Pythonie.

Aby uruchomić testy:

1.  **Przejdź do katalogu z kodem źródłowym i testami:**
    Z głównego katalogu `ai-code-tools-builder` wykonaj polecenie:
    ```bash
    cd ai-code-tools-1.0.0/usr/local/lib/python3.10/dist-packages/
    ```

2.  **Uruchom automatyczne wykrywanie i wykonanie testów:**
    ```bash
    python3 -m unittest discover
    ```

Pomyślne wykonanie wszystkich testów zakończy się komunikatem podobnym do poniższego, informującym o liczbie uruchomionych testów i statusie `OK`.

```bash
.......
----------------------------------------------------------------------
Ran 7 tests in X.XXXs

OK
```
