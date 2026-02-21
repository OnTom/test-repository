# CLAUDE.md – Deutsch Klicker (Battle Edition)

Projektový průvodce pro AI asistenty a vývojáře.

## Spuštění

```bash
pip install -r requirements.txt   # pygame>=2.5
python german_clicker/main.py
```

## Tech stack

| Vrstva | Technologie |
|---|---|
| Jazyk | Python 3.11+ |
| Grafika | Pygame 2.5+ |
| Architektura | Finite State Machine (FSM) |
| Datový model | `dataclass`, `Enum` (stdlib) |

## Struktura projektu

```
german_clicker/
├── main.py     # Vstupní bod; inicializuje pygame a spustí Game loop
├── game.py     # Veškerá herní logika – stavový automat, sprite renderer, NPC
├── words.py    # Slovní databáze: dict CATEGORIES {název: [(de, cs), …]}
└── ui.py       # Reusable UI komponenty a barevná paleta
```

## Stavový automat (game.py)

```
MENU
 └─► CAMP ◄────────────────────────────────────────┐
      ├─► CAMP_NPC (merchant | blacksmith | mayor)  │
      └─► MAP                                       │
           └─► PLAYER_CHOOSE                        │
                └─► …battle stavy…                  │
                     ├─► VICTORY ──────────────────►┘
                     └─► GAME_OVER ──► MENU
```

Každý stav má dvojici metod `_draw_<stav>()` a `_handle_<stav>()` v třídě `Game`.

## Klíčové konstanty (game.py)

```python
SCREEN_W, SCREEN_H = 900, 600
FPS               = 60
RESOLVE_PAUSE_MS  = 1400   # pauza po výsledku kola
ENEMY_TURN_DELAY  = 700    # ms před akcí nepřítele
FIRE_FRAME_MS     = 380    # rychlost animace ohniště
```

## Pixel-art sprite renderer

Sprity jsou definovány jako seznamy ASCII řetězců + paleta `_C: dict[str, tuple | None]`.
Každý znak mapy na RGB tuple; `.` = průhledný pixel.

```python
_C = { 'G': (76,153,50), 'E': (15,15,15), … , '.': None }
_PLAYER_ART = ["....GGGG....", …]          # hráč
_ENEMY_ART  = {"Šnek": […], "Pavouk": […]} # nepřátelé podle jména
```

## UI (ui.py)

Komponenty: `Button`, `HealthBar`, `TextInput`, `MessageOverlay`
Pomocné funkce: `load_font(size, bold)`, `draw_rounded_rect`, `draw_text_centered`, `draw_text_left`

Paleta vychází z tmavého cave tématu (`DARK_BG = (28,20,38)`). Barvy jsou exportovány a importovány v `game.py`.

## Slovní databáze (words.py)

```python
CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "Čísla":   [("eins", "jedna"), …],
    "Barvy":   [("rot", "červená"), …],
    "Zvířata": […],
    "Jídlo":   […],
    "Dny":     […],
    "Fráze":   […],
    "Rodina":  […],
}
```

Přidání kategorie = nový klíč v tomto slovníku; hra ho automaticky zahrne.

## NPC systém

NPC mají podtyp: `merchant` | `blacksmith` | `mayor`.
Každý podtyp má vlastní dialog a nabídku akcí vykreslovanou ve stavu `CAMP_NPC`.

## Vývojové konvence

- Komentáře a texty v kódu jsou **česky** (cílový hráč je česky mluvící).
- Herní texty zobrazované hráči jsou **česky**, německá slova pochází ze slovníku.
- Sekce v `game.py` jsou odděleny řádkovými komentáři `# ---…--- Název ---…---`.
- Nové stavy FSM se přidávají do `Enum` třídy `State` a obsluhují metodami `_draw_X` / `_handle_X`.
- Žádné globální proměnné – veškerý stav je v instanci třídy `Game`.

## Git workflow

Aktivní vývojová větev: `claude/german-learning-clicker-game-vP2vy`

```bash
git push -u origin claude/german-learning-clicker-game-vP2vy
```
