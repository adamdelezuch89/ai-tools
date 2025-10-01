# Narzędzia AI do Pracy z Kodem

Zestaw narzędzi wiersza poleceń dla systemów Ubuntu/Debian, przeznaczony do tworzenia zrzutów kodu dla modeli AI oraz do implementowania zmian wygenerowanych przez AI.

Narzędzia działają w kontekście **projektu**, który jest automatycznie definiowany przez katalog, w którym wykonujesz polecenia.

## ✨ Główne Zastosowania

Głównym celem narzędzi jest **usprawnienie współpracy z modelami językowymi (AI)** w terminalu, umożliwiając łatwe przygotowanie kontekstu kodu dla AI oraz automatyczne wdrażanie zmian generowanych przez nie.

### 1. Przygotowanie Kontekstu dla AI (`dump-repo`, `dump-git`)

* **Co to robi?** Konsoliduje kod całego Twojego projektu (`dump-repo`) lub tylko **zmienione pliki** z Git (`dump-git`) do jednego, czystego pliku tekstowego, a następnie **kopiuje ten zrzut do schowka systemowego**.
* **Po co?** Dzięki temu możesz **łatwo wkleić kontekst swojego kodu** bezpośrednio do interfejsu webowego dowolnego modelu językowego (np. Gemini, ChatGPT, Claude) i natychmiast zadawać precyzyjne pytania, prosić o refaktoryzację, debugowanie lub implementację nowych funkcji.
* **Bezpieczeństwo i Czystość:** Narzędzie inteligentnie filtruje niepotrzebne pliki (np. `node_modules`), pozwala na **wykluczanie krytycznych ścieżek** z dumpowania oraz **ukrywa wrażliwe dane** (np. wartości zmiennych z plików `.env`) w całym kodzie, chroniąc przed wyciekiem.
* **Przywracanie Wersji:** Możesz również **przywrócić pliki** z poprzednio utworzonych dumpów.

### 2. Implementacja Zmian od AI (`ai-patch`)

* **Co to robi?** Automatycznie wgrywa zmiany w kodzie, które otrzymałeś od modelu AI, wprost ze **schowka systemowego**.
* **Po co?** Kiedy AI wygeneruje dla Ciebie fragmenty kodu lub całe pliki, **zamiast ręcznie kopiować i wklejać**, po prostu kopiujesz całą odpowiedź AI do schowka i uruchamiasz `ai-patch`. Narzędzie samodzielnie rozpoznaje ścieżki plików i wdroży zmiany za Ciebie, oszczędzając czas i redukując ryzyko pomyłki.

## Instalacja

### Instalacja deweloperska (zalecana dla development)

```bash
# Klonuj repozytorium
git clone https://github.com/adamdelezuch89/ai-tools.git
cd ai-tools

# Zainstaluj w trybie edytowalnym
pip install -e .

# Lub z zależnościami deweloperskimi
pip install -e ".[dev]"
```

Po instalacji, polecenia `dump-repo`, `dump-git` i `ai-patch` będą dostępne globalnie.

### Instalacja z paczki .deb

Narzędzia można również zainstalować jako standardową paczkę systemową:

1.  **Zbuduj paczkę:**
    ```bash
    ./scripts/build_deb.sh
    ```

2.  **Zainstaluj paczkę:**
    ```bash
    sudo apt install ./ai-code-tools-1.0.0.deb
    ```

## Szybki start

```bash
# 1. Utwórz plik konfiguracyjny
dump-repo --init

# 2. (Opcjonalnie) Edytuj .ai-tools-config.yaml

# 3. Użyj narzędzi
dump-repo           # Dump całego projektu
dump-git            # Dump tylko zmian

# 4. Przeglądaj i przywracaj
dump-repo --list    # Zobacz ostatnie dumpy (kliknij link lub wpisz numer)
dump-repo --restore # Przywróć z ostatniego dumpu
```

## Konfiguracja Projektu

### Przechowywanie dumpów

Dumpy są automatycznie zapisywane w systemowym temp (`/tmp/ai-tools/<projekt>/<tool>/`) i czyszczone po 7 dniach. Każdy projekt ma osobny katalog identyfikowany przez hash ścieżki.

### Plik konfiguracyjny

Plik `.ai-tools-config.yaml` w głównym katalogu projektu kontroluje zachowanie narzędzi.

**Automatyczne tworzenie:**
```bash
dump-repo --init   # lub
dump-git --init
```

**Lokalizacja:** `.ai-tools-config.yaml` (w głównym katalogu projektu)

**Przykładowa zawartość:**
```yaml
# [Wymagane] Katalog na wygenerowane pliki zrzutów.
output_dir: .dump-outputs

# [Opcjonalne] Ukrywanie wrażliwych wartości z plików .env
# Domyślnie: true (zalecane dla bezpieczeństwa)
hide_env: true

# [Opcjonalne] Dodatkowe mapowanie rozszerzeń (rozszerza domyślne)
# System ma wbudowane mapowanie dla 40+ popularnych rozszerzeń
# Tutaj możesz dodać tylko niestandardowe rozszerzenia
extension_lang_map:
  .custom: customlang
  .special: special

# [Opcjonalne] Ścieżki do wykluczenia (blacklist).
# Może zawierać katalogi (z/bez ukośnika) i wzorce wildcard.
blacklisted_paths:
  - "node_modules"      # Katalog bez ukośnika
  - ".venv/"            # Katalog z ukośnikiem
  - "dist/"
  - "*.lock"            # Wzorzec wildcard

# [Opcjonalne] Ścieżki do ZAWSZE dołączenia (whitelist).
# Ma wyższy priorytet niż .gitignore, ale niższy niż blacklist (chyba że bardziej specyficzna).
whitelisted_paths:
  - ".github/workflows/"
```

**Nota:** System ma wbudowane mapowanie dla najpopularniejszych rozszerzeń (`.js`, `.py`, `.ts`, `.html`, `.css`, `.go`, `.rs`, `.java`, `.php`, i 30+ innych). Dodawaj do `extension_lang_map` tylko niestandardowe rozszerzenia.

### 🔒 Bezpieczeństwo - Ukrywanie wrażliwych danych

**Domyślnie włączone!** Narzędzia automatycznie ukrywają wartości z plików `.env` przed utworzeniem dumpu.

#### Jak to działa?

1. System szuka plików `.env`, `.env.local`, `.env.development` w głównym katalogu projektu
2. Wyodrębnia **wszystkie wartości** (nie klucze) z tych plików
3. Podmienia każde wystąpienie tych wartości na `[HIDDEN_ENV_VALUE]` w dumpie

#### Przykład:

**Twój plik `.env`:**
```env
API_KEY=sk_test_1234567890abcdef
DATABASE_URL=postgres://user:password@localhost:5432/mydb
SECRET_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
```

**Twój kod `src/config.js`:**
```javascript
const apiKey = 'sk_test_1234567890abcdef';
const dbUrl = "postgres://user:password@localhost:5432/mydb";
```

**W dumpie zobaczysz:**
```javascript
const apiKey = '[HIDDEN_ENV_VALUE]';
const dbUrl = "[HIDDEN_ENV_VALUE]";
```

#### Wyłączanie ukrywania (NIE ZALECANE)

Jeśli z jakiegoś powodu musisz wyłączyć tę funkcję:

```yaml
hide_env: false  # ⚠️ Uwaga: wrażliwe dane będą widoczne w dumpie!
```

**⚠️ OSTRZEŻENIE:** Wyłączanie tej opcji może spowodować wyciek kluczy API, haseł i innych wrażliwych danych do AI lub do schowka systemowego!

---

### 🎯 Zaawansowane filtrowanie

#### Priorytetyzacja reguł

System stosuje inteligentną priorytetyzację opartą na **specyficzności** ścieżek:

1. **Bardziej zagnieżdżona reguła wygrywa** - `vendor/libs/` ma wyższy priorytet niż `vendor/`
2. **Przy tej samej specyficzności** - blacklist ma pierwszeństwo
3. **Wykrywanie konfliktów** - system automatycznie wykrywa konflikty (ta sama ścieżka w obu listach)

#### Przykłady

**Przykład 1: Whitelisted katalog z blacklisted podkatalogiem**
```yaml
blacklisted_paths:
  - "docs/internal/"     # Wykluczamy poufne dokumenty
whitelisted_paths:
  - "docs/"              # Ale reszta docs jest OK
```
Rezultat:
- ✅ `docs/README.md` - załączone
- ✅ `docs/api/guide.md` - załączone  
- ❌ `docs/internal/secret.md` - wykluczone (bardziej specyficzna reguła)

**Przykład 2: Blacklisted katalog z whitelisted podkatalogiem**
```yaml
blacklisted_paths:
  - "build/"             # Wykluczamy outputy kompilacji
whitelisted_paths:
  - "build/config/"      # Ale config jest ważny
```
Rezultat:
- ❌ `build/output.js` - wykluczone
- ✅ `build/config/settings.json` - załączone (bardziej specyficzna reguła)
- ❌ `build/cache/temp.js` - wykluczone

**Przykład 3: Wielopoziomowe zagnieżdżenie**
```yaml
blacklisted_paths:
  - "vendor/"                      # Poziom 1: wszystko wykluczone
  - "vendor/libs/node_modules/"    # Poziom 3: bardziej specyficzne wykluczenie
whitelisted_paths:
  - "vendor/libs/"                 # Poziom 2: częściowe załączenie
```
Rezultat:
- ❌ `vendor/readme.txt` - wykluczone (poziom 1)
- ✅ `vendor/libs/important.js` - załączone (poziom 2)
- ❌ `vendor/libs/node_modules/dep.js` - wykluczone (poziom 3 - najbardziej specyficzny)

---

## Dostępne Polecenia

Każde polecenie ma zwięzły help dostępny przez `--help`, pokazujący aktualną konfigurację i co będzie dumpowane.

### `dump-repo`
Tworzy zrzut tekstowy całego projektu lub jego wybranych części.

**Użycie:**
```bash
# Pierwsza konfiguracja projektu
dump-repo --init

# Zrzut całego projektu
dump-repo

# Zrzut tylko katalogu 'src'
dump-repo src

# Przeglądaj ostatnie dumpy (kliknij link lub przywróć)
dump-repo --list

# Przywróć z ostatniego dumpu
dump-repo --restore

# Przywróć z przedostatniego dumpu
dump-repo --restore 2

# Przywróć z trzeciego od końca
dump-repo --restore 3

# Zobacz konfigurację
dump-repo --help
```

### `dump-git`
Tworzy zrzut tekstowy tylko **zmienionych** plików w Git.

**Użycie:**
```bash
# Pierwsza konfiguracja projektu (jeśli nie istnieje)
dump-git --init

# Wszystkie zmiany
dump-git

# Tylko staged
dump-git --staged

# Tylko unstaged i untracked
dump-git --unstaged

# Przeglądaj ostatnie dumpy (kliknij link lub przywróć)
dump-git --list

# Przywróć z ostatniego dumpu
dump-git --restore

# Przywróć z przedostatniego dumpu  
dump-git --restore 2

# Zobacz konfigurację
dump-git --help
```

### `ai-patch`
Aplikuje zmiany z schowka do plików.

**Użycie:**
```bash
# 1. Skopiuj zmiany do schowka (Ctrl+C)
# 2. Uruchom:
ai-patch

# Zobacz format wymagany
ai-patch --help
```

**Format tekstu w schowku:**
```
---
File: src/components/Button.js
---
```javascript
import React from 'react';

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
```

---

## Testowanie

```bash
# Uruchomienie testów
python -m unittest discover tests -v

# Lub z pytest
pytest tests/ -v

# Z coverage
./scripts/run_tests.sh
```

---

## Development

### Struktura projektu

```
ai-tools/
├── src/ai_tools/              # Kod źródłowy
│   ├── cli/                   # Polecenia CLI
│   │   ├── dump_repo.py       # dump-repo command
│   │   ├── dump_git.py        # dump-git command  
│   │   └── ai_patch.py        # ai-patch command
│   ├── core/                  # Logika biznesowa
│   │   ├── file_filter.py     # Filtrowanie plików (blacklist/whitelist)
│   │   └── patch_ops.py       # Operacje patchowania
│   └── utils/                 # Narzędzia pomocnicze
│       ├── config.py          # Zarządzanie konfiguracją
│       ├── logger.py          # Funkcje logowania
│       ├── filesystem.py      # Operacje na plikach
│       └── helpers.py         # Wrapper dla kompatybilności
├── tests/                     # Testy jednostkowe
├── debian/                    # Pliki dla paczki .deb
├── scripts/                   # Skrypty pomocnicze
│   ├── build_deb.sh          # Budowanie paczki .deb
│   ├── run_tests.sh          # Uruchomienie testów z coverage
│   └── cli_wrappers/         # Entry points dla poleceń
├── setup.py                   # Konfiguracja pakietu Python
├── pytest.ini                 # Konfiguracja pytest
├── .coveragerc               # Konfiguracja coverage
└── requirements.txt           # Zależności
```

### Instalacja deweloperska

```bash
# Klonuj repozytorium
git clone https://github.com/yourusername/ai-tools.git
cd ai-tools

# Instaluj w trybie edytowalnym z zależnościami deweloperskimi
pip install -e ".[dev]"

# Uruchom testy
python -m unittest discover tests -v

# Lub z pytest i coverage
./scripts/run_tests.sh

# Lub manualnie
pytest tests/ --cov=ai_tools --cov-report=html -v

# Formatowanie kodu
black src/ tests/

# Linting
flake8 src/ tests/
```

### Dodawanie nowych funkcji

1. Dodaj kod w odpowiednim module (`src/ai_tools/`)
2. Napisz testy w `tests/`
3. Zaktualizuj `CHANGELOG.md`
4. Uruchom wszystkie testy przed commit

---

## FAQ

**Q: Czy moje klucze API i hasła są bezpieczne?**  
A: Tak! **Domyślnie wszystkie wartości z plików `.env` są automatycznie ukrywane** przed utworzeniem dumpu. Możesz bezpiecznie udostępniać dumpy AI bez ryzyka wycieku wrażliwych danych.

**Q: Które pliki .env są skanowane?**  
A: System automatycznie skanuje: `.env`, `.env.local`, `.env.development`, `.env.production` w głównym katalogu projektu.

**Q: Co się stanie gdy ta sama ścieżka jest w blacklist i whitelist?**  
A: System wykryje konflikt i **wyświetli błąd** podczas uruchamiania. Musisz poprawić konfigurację.

**Q: Czy mogę wykluczyć cały katalog ale załączyć jego podkatalog?**  
A: Tak! Użyj bardziej specyficznej reguły whitelist. Zobacz przykłady w sekcji "Zaawansowane filtrowanie".

**Q: Czy katalogi muszą kończyć się ukośnikiem?**  
A: Nie. System rozpoznaje `"src"` i `"src/"` jako ten sam katalog.

**Q: Co z plikami binarnymi?**  
A: Pliki binarne są automatycznie wykluczane z dumpu.

**Q: Czy mogę wyłączyć ukrywanie .env?**  
A: Tak, ale **NIE jest to zalecane**. Ustaw `hide_env: false` w konfiguracji. Używaj tylko jeśli masz pewność, że nie ma wrażliwych danych.

**Q: Gdzie są zapisywane dumpy?**  
A: W `/tmp/ai-tools/<projekt>/<tool>/`. Każdy projekt ma osobny katalog, dumpy są automatycznie czyszczone po 7 dniach.

**Q: Jak przeglądać ostatnie dumpy?**  
A: Użyj `dump-repo --list` lub `dump-git --list`. Możesz interaktywnie wybrać i otworzyć plik.

**Q: Jak szybko skonfigurować nowy projekt?**  
A: Uruchom `dump-repo --init`, edytuj utworzony `.ai-tools-config.yaml` i gotowe!

**Q: Jak przywrócić pliki z poprzedniego dumpu?**  
A: Użyj `dump-repo --restore` lub `dump-repo --restore 1` (ostatni), `dump-repo --restore 2` (przedostatni), itd.

**Q: Jak przeglądać i przywracać dumpy?**  
A: `dump-repo --list` pokazuje listę z klikalnymi linkami. Możesz też wpisać numer aby przywrócić pliki.

---

## Licencja

MIT License - zobacz plik [LICENSE](LICENSE).

## Changelog

Zobacz plik [CHANGELOG.md](CHANGELOG.md) dla historii zmian.
