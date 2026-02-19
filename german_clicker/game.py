"""
Herní logika pro Deutsch Klicker – battle RPG verze.

Fáze tahu:
  MENU            – hlavní nabídka
  PLAYER_CHOOSE   – hráč klikne na Útočit nebo Bránit
  PLAYER_TRANSLATE– hráč napíše německý překlad českého slova
  RESOLVE_PLAYER  – krátká pauza po akci hráče
  ENEMY_TURN      – nepřítel jedná automaticky (náhoda)
  RESOLVE_ENEMY   – krátká pauza po akci nepřítele
  VICTORY         – nepřítel poražen → XP
  GAME_OVER       – hráč zemřel
"""

import pygame
import random
from enum import Enum
from dataclasses import dataclass

from words import CATEGORIES
from ui import (
    Button, HealthBar, TextInput, MessageOverlay,
    load_font, draw_rounded_rect, draw_text_centered, draw_text_left,
    WHITE, TEXT_LT, SILVER, CORRECT_COLOR, WRONG_COLOR, GOLD,
    PANEL_BG,
)

# ---------------------------------------------------------------------------
# Rozměry obrazovky
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 900, 600
FPS = 60

RESOLVE_PAUSE_MS = 1400   # ms pauzy po akci
ENEMY_TURN_DELAY = 700    # ms před automatickým tahem nepřítele

# ---------------------------------------------------------------------------
# Paleta barev pro pixel art (jednoznakové kódy)
# ---------------------------------------------------------------------------
_C: dict[str, tuple | None] = {
    # Hráč (žabí rytíř)
    'G': (76,  153,  50),   # zelená (kůže žáby)
    'g': (50,  110,  35),   # tmavá zelená
    'E': (15,   15,  15),   # oko
    'B': (70,  100, 165),   # modrá zbroj
    'b': (45,   70, 120),   # tmavá zbroj
    'W': (180, 185, 200),   # zbraň – stříbro
    'w': (130, 135, 150),   # tmavé stříbro
    'F': (55,  125,  40),   # noha / chodidlo
    # Nepřátelé
    'S': (160, 100,  50),   # skořápka šneka
    's': (110,  68,  32),   # tmavá skořápka
    'K': (50,   50,  60),   # pavouk – tělo
    'k': (28,   28,  36),   # tmavý pavouk
    'R': (180,  60,  60),   # ještěrka – červená
    'r': (120,  35,  35),   # tmavá červená
    'P': (130,  60, 180),   # netopýr – fialová
    'p': (85,   35, 125),   # tmavá fialová
    'Y': (210, 180,  45),   # drak – zlatá
    'y': (155, 125,  25),   # tmavá zlatá
    '.': None,              # průhledné
}

# ---------------------------------------------------------------------------
# Pixel art definice postav (každý řádek = jedna řada pixelů)
# ---------------------------------------------------------------------------
_PLAYER_ART = [
    "....GGGG....",
    "...GGGGGG...",
    "..GGgEGEgGG.",
    "...GGGGGG...",
    "....GGGG....",
    ".W.BBBBBB...",
    "WW.BBBBBB...",
    "WW.BBBBBB...",
    ".W.BBBBBB...",
    "....BBBB....",
    "...FF..FF...",
    "...FF..FF...",
    "...FF..FF...",
    "..FFF..FFF..",
]

_ENEMY_ART: dict[str, list[str]] = {
    "Šnek": [
        "...SSSSSS...",
        "..SSSSSSSs..",
        ".SSSSSSSSss.",
        ".SSSSSSSSss.",
        "..SSSSSSss..",
        "GGGG....GGGGG",
        "GGGGGgGGGGGGG",
        ".GGGgEGGEgGGG",
        ".GGGGGGGGGGG.",
    ],
    "Pavouk": [
        "K...KKKK...K",
        ".KK.KKKK.KK.",
        "..KKkEEkKK..",
        "...EEEEEE...",
        "...EEEEEE...",
        "..KKkEEkKK..",
        ".KK.KKKK.KK.",
        "K...KKKK...K",
    ],
    "Ještěrka": [
        "....RRRR....",
        "...RRRRRR...",
        "..RRrErErRR.",
        "...RRRRRR...",
        "..RRRRRRR...",
        ".RRRRRRRRR..",
        "RR...RR...RR",
        ".R...RR...R.",
        "......R.....",
    ],
    "Netopýr": [
        "P.......P...",
        "PP.PPPP.PP..",
        "PPP.PP.PPP..",
        "PPPpEpPPPP..",
        "PPP.PP.PPP..",
        "PP.PPPP.PP..",
        "P.......P...",
    ],
    "Drak": [
        "...YYYYYYY..",
        "..YYYYYYYYy.",
        "YYYYyEYEyYYY",
        ".YYYYYYYYYY.",
        "..YYYYYY....",
        "...YYYYYY...",
        "....YYYY....",
        "...YY..YY...",
        "..YY....YY..",
    ],
}

ENEMY_SEQUENCE = ["Šnek", "Pavouk", "Ještěrka", "Netopýr", "Drak"]


def _build_sprite(rows: list[str], scale: int = 5,
                  flip: bool = False) -> pygame.Surface:
    """Sestaví pygame.Surface z ASCII pixel art definice."""
    h = len(rows)
    w = max(len(r) for r in rows)
    surf = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            color = _C.get(ch)
            if color:
                pygame.draw.rect(surf, color,
                                 (x * scale, y * scale, scale, scale))
    if flip:
        surf = pygame.transform.flip(surf, True, False)
    return surf


# ---------------------------------------------------------------------------
# Normalizace překladu (přijímá ae/oe/ue/ss místo přehlásky / ß)
# ---------------------------------------------------------------------------
def _normalize(text: str) -> str:
    t = text.lower().strip()
    for article in ("der ", "die ", "das ", "ein ", "eine "):
        if t.startswith(article):
            t = t[len(article):]
            break
    return (t.replace("ae", "ä").replace("oe", "ö")
             .replace("ue", "ü").replace("ss", "ß"))


def check_translation(user_input: str, correct_de: str) -> bool:
    return _normalize(user_input) == _normalize(correct_de)


# ---------------------------------------------------------------------------
# Datové třídy postav
# ---------------------------------------------------------------------------
@dataclass
class Player:
    hp:        int  = 100
    max_hp:    int  = 100
    attack:    int  = 28
    xp:        int  = 0
    level:     int  = 1
    defending: bool = False

    @property
    def xp_to_next(self) -> int:
        return self.level * 80

    def try_level_up(self) -> bool:
        if self.xp >= self.xp_to_next:
            self.xp     -= self.xp_to_next
            self.level  += 1
            self.max_hp += 15
            self.hp      = self.max_hp
            self.attack  += 5
            return True
        return False


@dataclass
class Enemy:
    name:      str
    hp:        int
    max_hp:    int
    attack:    int
    xp_reward: int
    defending: bool = False


def _make_enemy(name: str, player_level: int) -> Enemy:
    base_hp  = 50 + (player_level - 1) * 20
    base_atk = 18 + (player_level - 1) * 5
    return Enemy(
        name=name,
        hp=base_hp,
        max_hp=base_hp,
        attack=base_atk,
        xp_reward=30 + (player_level - 1) * 15,
    )


# ---------------------------------------------------------------------------
# Fáze tahu
# ---------------------------------------------------------------------------
class Phase(Enum):
    MENU             = "menu"
    PLAYER_CHOOSE    = "player_choose"
    PLAYER_TRANSLATE = "player_translate"
    RESOLVE_PLAYER   = "resolve_player"
    ENEMY_TURN       = "enemy_turn"
    RESOLVE_ENEMY    = "resolve_enemy"
    VICTORY          = "victory"
    GAME_OVER        = "game_over"


# ---------------------------------------------------------------------------
# Hlavní třída Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.screen  = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Deutsch Klicker – Battle")
        self.clock   = pygame.time.Clock()

        # Fonty
        self.f_xl = load_font(52, bold=True)
        self.f_lg = load_font(36, bold=True)
        self.f_md = load_font(26, bold=True)
        self.f_sm = load_font(20)
        self.f_xs = load_font(15)

        # Načti sprites
        self.sprites: dict[str, pygame.Surface] = {}
        self._preload_sprites()

        # Herní objekty
        self.player: Player = Player()
        self.enemy_index: int = 0
        self.enemy: Enemy = _make_enemy(ENEMY_SEQUENCE[0], 1)

        # Word pool (všechna slova ze všech kategorií)
        self._word_pool: list[dict] = []
        for cat_words in CATEGORIES.values():
            self._word_pool.extend(cat_words)

        # Stav
        self.phase   = Phase.MENU
        self.running = True

        # Přechodné proměnné boje
        self.player_action:  str       = ""   # "attack" / "defend"
        self.current_word:   dict      = {}   # {"de": ..., "cz": ...}
        self.battle_log:     list[str] = []
        self._pause_timer:   int       = 0
        self._enemy_delay:   int       = 0
        self._level_up_flag: bool      = False

        # Sestavení UI
        self._build_ui()

    # ------------------------------------------------------------------
    # Sprite cache
    # ------------------------------------------------------------------
    def _preload_sprites(self) -> None:
        self.sprites["player"] = _build_sprite(_PLAYER_ART, scale=5)
        for name, art in _ENEMY_ART.items():
            self.sprites[name] = _build_sprite(art, scale=5, flip=True)

    # ------------------------------------------------------------------
    # Sestavení UI prvků
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        cx = SCREEN_W // 2

        # ---- Menu ----
        self.btn_start = Button(
            pygame.Rect(cx - 140, 310, 280, 58), "Hrát", self.f_md)
        self.btn_quit  = Button(
            pygame.Rect(cx - 140, 390, 280, 58), "Ukončit", self.f_md)

        # ---- Healthbary ----
        self.hp_player = HealthBar(
            pygame.Rect(30, 52, 240, 22), self.f_xs, label="Hráč")
        self.hp_enemy  = HealthBar(
            pygame.Rect(SCREEN_W - 270, 52, 240, 22), self.f_xs,
            label="Nepřítel", align="right")

        # ---- Akční tlačítka (Phase 1) ----
        self.btn_attack = Button(
            pygame.Rect(cx - 210, 463, 185, 54),
            "⚔  Útočit", self.f_md,
            base_color=(145, 55, 55), hover_color=(185, 75, 75))
        self.btn_defend = Button(
            pygame.Rect(cx + 25,  463, 185, 54),
            "🛡  Bránit", self.f_md,
            base_color=(50, 95, 148), hover_color=(70, 125, 188))

        # ---- Textový vstup (Phase 2) ----
        self.text_input = TextInput(
            pygame.Rect(cx - 210, 483, 420, 42),
            self.f_md,
            placeholder="Napiš německy a stiskni Enter…")

        # ---- Překryvná zpráva ----
        self.message = MessageOverlay(self.f_lg)

    # ------------------------------------------------------------------
    # Nová hra
    # ------------------------------------------------------------------
    def _new_game(self) -> None:
        self.player      = Player()
        self.enemy_index = 0
        self.enemy       = _make_enemy(ENEMY_SEQUENCE[0], 1)
        self.battle_log  = []
        self._level_up_flag = False
        self._sync_hp_bars()
        self._pick_word()
        self.phase = Phase.PLAYER_CHOOSE

    def _sync_hp_bars(self) -> None:
        self.hp_player.set_hp(self.player.hp, self.player.max_hp)
        self.hp_enemy.set_hp(self.enemy.hp,   self.enemy.max_hp)

    def _pick_word(self) -> None:
        self.current_word = random.choice(self._word_pool)
        self.text_input.clear()

    def _add_log(self, msg: str) -> None:
        self.battle_log.append(msg)
        if len(self.battle_log) > 4:
            self.battle_log.pop(0)

    # ------------------------------------------------------------------
    # Hlavní smyčka
    # ------------------------------------------------------------------
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS)
            self._process_events()
            self._update(dt)
            self._draw()
        pygame.quit()

    # ------------------------------------------------------------------
    # Zpracování událostí
    # ------------------------------------------------------------------
    def _process_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif self.phase == Phase.MENU:
                if self.btn_start.handle_event(event):
                    self._new_game()
                if self.btn_quit.handle_event(event):
                    self.running = False

            elif self.phase == Phase.PLAYER_CHOOSE:
                if self.btn_attack.handle_event(event):
                    self.player_action = "attack"
                    self.phase = Phase.PLAYER_TRANSLATE
                elif self.btn_defend.handle_event(event):
                    self.player_action = "defend"
                    self.phase = Phase.PLAYER_TRANSLATE

            elif self.phase == Phase.PLAYER_TRANSLATE:
                if self.text_input.handle_event(event):
                    self._submit_translation()

            elif self.phase in (Phase.VICTORY, Phase.GAME_OVER):
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    if self.phase == Phase.VICTORY:
                        self._next_enemy()
                    else:
                        self.phase = Phase.MENU

    # ------------------------------------------------------------------
    # Aktualizace
    # ------------------------------------------------------------------
    def _update(self, dt: int) -> None:
        self.message.update(dt)
        self.text_input.update(dt)

        if self.phase == Phase.RESOLVE_PLAYER:
            self._pause_timer -= dt
            if self._pause_timer <= 0:
                self._check_enemy_dead()

        elif self.phase == Phase.ENEMY_TURN:
            self._enemy_delay -= dt
            if self._enemy_delay <= 0:
                self._resolve_enemy_turn()

        elif self.phase == Phase.RESOLVE_ENEMY:
            self._pause_timer -= dt
            if self._pause_timer <= 0:
                self._check_player_dead()

    # ------------------------------------------------------------------
    # Herní logika: tah hráče
    # ------------------------------------------------------------------
    def _submit_translation(self) -> None:
        user_text = self.text_input.text.strip()
        correct   = check_translation(user_text, self.current_word["de"])

        if correct:
            if self.player_action == "attack":
                dmg = self.player.attack
                if self.enemy.defending:
                    dmg = dmg // 2
                    self._add_log(f"Správně! Nepřítel se bránil – {dmg} poškození.")
                else:
                    self._add_log(f"Správně! Útok za {dmg} poškození.")
                self.enemy.hp = max(0, self.enemy.hp - dmg)
                self.message.show(f"⚔  Útok!  −{dmg} HP", CORRECT_COLOR)
            else:
                self.player.defending = True
                self._add_log("Správně! Zaujímáš obranný postoj.")
                self.message.show("🛡  Obrana aktivní!", (100, 160, 220))
        else:
            self._add_log(
                f"Špatně! Správně: „{self.current_word['de']}". Akce selhala.")
            self.message.show("✗  Špatný překlad – akce selhala!", WRONG_COLOR)

        self._sync_hp_bars()
        self._pick_word()
        self.phase        = Phase.RESOLVE_PLAYER
        self._pause_timer = RESOLVE_PAUSE_MS

    def _check_enemy_dead(self) -> None:
        if self.enemy.hp <= 0:
            xp_gain = self.enemy.xp_reward
            self.player.xp += xp_gain
            self._level_up_flag = self.player.try_level_up()
            self._add_log(f"Nepřítel {self.enemy.name} poražen! +{xp_gain} XP.")
            self.message.show(f"Vítězství!  +{xp_gain} XP", GOLD)
            self.phase = Phase.VICTORY
        else:
            self.phase        = Phase.ENEMY_TURN
            self._enemy_delay = ENEMY_TURN_DELAY

    # ------------------------------------------------------------------
    # Herní logika: tah nepřítele
    # ------------------------------------------------------------------
    def _resolve_enemy_turn(self) -> None:
        # 60 % útok, 40 % obrana
        self.enemy.defending = False
        if random.random() < 0.60:
            dmg = self.enemy.attack
            if self.player.defending:
                dmg = dmg // 2
                self._add_log(
                    f"{self.enemy.name} útočí – tvá obrana snižuje na {dmg} dmg!")
            else:
                self._add_log(f"{self.enemy.name} útočí za {dmg} poškození!")
            self.player.hp = max(0, self.player.hp - dmg)
            self.message.show(f"💀  {self.enemy.name} útočí!  −{dmg} HP",
                              WRONG_COLOR)
        else:
            self.enemy.defending = True
            self._add_log(f"{self.enemy.name} se brání – příští útok bude slabší.")
            self.message.show(f"🛡  {self.enemy.name} se brání!", SILVER)

        self.player.defending = False
        self._sync_hp_bars()
        self.phase        = Phase.RESOLVE_ENEMY
        self._pause_timer = RESOLVE_PAUSE_MS

    def _check_player_dead(self) -> None:
        if self.player.hp <= 0:
            self._add_log("Byl jsi poražen…")
            self.phase = Phase.GAME_OVER
        else:
            self.phase = Phase.PLAYER_CHOOSE

    # ------------------------------------------------------------------
    # Přechod na dalšího nepřítele
    # ------------------------------------------------------------------
    def _next_enemy(self) -> None:
        self.enemy_index = (self.enemy_index + 1) % len(ENEMY_SEQUENCE)
        name = ENEMY_SEQUENCE[self.enemy_index]
        self.enemy = _make_enemy(name, self.player.level)
        self._sync_hp_bars()
        self._level_up_flag = False
        self.phase = Phase.PLAYER_CHOOSE

    # ------------------------------------------------------------------
    # Kreslení
    # ------------------------------------------------------------------
    def run_draw(self) -> None:
        """Jeden snímek – volá se z run()."""
        self.screen.fill((28, 20, 38))
        self._draw_cave_bg()
        if self.phase == Phase.MENU:
            self._draw_menu()
        else:
            self._draw_battle()
        pygame.display.flip()

    def _draw(self) -> None:
        self.screen.fill((28, 20, 38))
        self._draw_cave_bg()
        if self.phase == Phase.MENU:
            self._draw_menu()
        else:
            self._draw_battle()
        pygame.display.flip()

    # ------------------------------------------------------------------
    # Pozadí: jeskyně
    # ------------------------------------------------------------------
    def _draw_cave_bg(self) -> None:
        w, h = SCREEN_W, SCREEN_H
        # Strop
        pygame.draw.rect(self.screen, (38, 28, 50), (0, 0, w, 88))
        # Podlaha
        pygame.draw.rect(self.screen, (65, 50, 42), (0, h - 118, w, 118))
        # Mřížka podlahy
        tile = (72, 57, 48)
        for tx in range(0, w, 65):
            pygame.draw.line(self.screen, tile, (tx, h - 118), (tx, h), 1)
        for ty in range(h - 118, h, 32):
            pygame.draw.line(self.screen, tile, (0, ty), (w, ty), 1)
        # Stalaktity (shora)
        for sx in [90, 240, 400, 560, 720, 850]:
            pts = [(sx - 13, 0), (sx + 13, 0), (sx, 40)]
            pygame.draw.polygon(self.screen, (50, 38, 65), pts)
        # Stalagmity (zdola)
        for sx in [50, 200, 370, 530, 690, 820]:
            pts = [(sx - 11, h), (sx + 11, h), (sx, h - 35)]
            pygame.draw.polygon(self.screen, (58, 44, 36), pts)
        # Oddělovač arény od UI panelu
        pygame.draw.rect(self.screen, (60, 45, 75),
                         (0, h - 120, w, 2))

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------
    def _draw_menu(self) -> None:
        cx = SCREEN_W // 2
        draw_text_centered(self.screen, "Deutsch Klicker",
                           self.f_xl, GOLD, cx, 140)
        draw_text_centered(self.screen, "Battle Edition",
                           self.f_md, SILVER, cx, 200)
        draw_text_centered(self.screen,
                           "Útočíš nebo se bráníš? Přelož správně a bojuj!",
                           self.f_sm, TEXT_LT, cx, 252)

        mouse = pygame.mouse.get_pos()
        self.btn_start.draw(self.screen, mouse)
        self.btn_quit.draw(self.screen,  mouse)

        draw_text_centered(self.screen, "v2.0  |  Python + Pygame",
                           self.f_xs, (85, 75, 100), cx, SCREEN_H - 18)

    # ------------------------------------------------------------------
    # Battle obrazovka
    # ------------------------------------------------------------------
    def _draw_battle(self) -> None:
        self._draw_characters()
        self._draw_hud()
        self._draw_battle_panel()
        self._draw_battle_log()
        self.message.draw(self.screen)
        if self.phase == Phase.VICTORY:
            self._draw_victory_overlay()
        elif self.phase == Phase.GAME_OVER:
            self._draw_gameover_overlay()

    def _draw_characters(self) -> None:
        floor_y = SCREEN_H - 118

        # Hráč – vlevo
        psurf = self.sprites.get("player")
        if psurf:
            px = 80
            py = floor_y - psurf.get_height()
            self.screen.blit(psurf, (px, py))

        # Nepřítel – vpravo
        esurf = self.sprites.get(self.enemy.name)
        if esurf:
            ex = SCREEN_W - 80 - esurf.get_width()
            ey = floor_y - esurf.get_height()
            self.screen.blit(esurf, (ex, ey))

        # VS text uprostřed
        draw_text_centered(self.screen, "VS", self.f_md,
                           (90, 70, 110), SCREEN_W // 2,
                           floor_y - 55)

    def _draw_hud(self) -> None:
        """Jména, XP bar a healthbary nahoře."""
        # Jméno + level hráče
        draw_text_left(self.screen,
                       f"Hráč  Lv.{self.player.level}",
                       self.f_xs, GOLD, 30, 28)
        # XP bar
        xp_ratio = self.player.xp / max(1, self.player.xp_to_next)
        xp_rect  = pygame.Rect(30, 40, 240, 8)
        pygame.draw.rect(self.screen, (38, 30, 50), xp_rect, border_radius=4)
        if xp_ratio > 0:
            xp_fill = pygame.Rect(30, 40, int(240 * xp_ratio), 8)
            pygame.draw.rect(self.screen, GOLD, xp_fill, border_radius=4)
        pygame.draw.rect(self.screen, SILVER, xp_rect, 1, border_radius=4)

        self.hp_player.draw(self.screen)

        # Jméno nepřítele
        name_surf = self.f_xs.render(self.enemy.name, True, (220, 100, 100))
        self.screen.blit(name_surf,
                         (SCREEN_W - 30 - name_surf.get_width(), 28))
        self.hp_enemy.draw(self.screen)

    def _draw_battle_panel(self) -> None:
        """Spodní UI panel – akce hráče."""
        panel = pygame.Rect(0, SCREEN_H - 118, SCREEN_W, 118)
        pygame.draw.rect(self.screen, (33, 23, 43), panel)
        pygame.draw.line(self.screen, (65, 48, 82),
                         (0, SCREEN_H - 118), (SCREEN_W, SCREEN_H - 118), 2)

        cx    = SCREEN_W // 2
        mouse = pygame.mouse.get_pos()

        if self.phase == Phase.PLAYER_CHOOSE:
            draw_text_centered(self.screen, "Vyber akci:",
                               self.f_sm, TEXT_LT, cx, SCREEN_H - 100)
            self.btn_attack.draw(self.screen, mouse)
            self.btn_defend.draw(self.screen, mouse)

        elif self.phase == Phase.PLAYER_TRANSLATE:
            label = "⚔  Útok" if self.player_action == "attack" else "🛡  Obrana"
            draw_text_centered(self.screen,
                               f"{label}  –  Přelož do němčiny:",
                               self.f_sm, GOLD, cx, SCREEN_H - 105)
            draw_text_centered(self.screen,
                               f'„{self.current_word.get("cz", "?")}"',
                               self.f_md, WHITE, cx, SCREEN_H - 80)
            self.text_input.draw(self.screen)
            draw_text_centered(self.screen,
                               "Tip: ä=ae  ö=oe  ü=ue  ß=ss",
                               self.f_xs, (95, 85, 115), cx, SCREEN_H - 12)

        elif self.phase in (Phase.RESOLVE_PLAYER, Phase.ENEMY_TURN,
                            Phase.RESOLVE_ENEMY):
            draw_text_centered(self.screen, "…",
                               self.f_md, (90, 80, 110), cx, SCREEN_H - 65)

    def _draw_battle_log(self) -> None:
        """Malý log bojových zpráv – pod HP bary vlevo."""
        y = 85
        for msg in self.battle_log[-3:]:
            draw_text_left(self.screen, msg, self.f_xs,
                           (135, 125, 155), 30, y)
            y += 18

    def _draw_victory_overlay(self) -> None:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))
        cx, cy = SCREEN_W // 2, SCREEN_H // 2 - 90

        draw_text_centered(self.screen, "Vítězství!", self.f_xl, GOLD, cx, cy)
        draw_text_centered(self.screen, f"+{self.enemy.xp_reward} XP",
                           self.f_lg, CORRECT_COLOR, cx, cy + 72)
        if self._level_up_flag:
            draw_text_centered(self.screen,
                               f"⬆  LEVEL UP!  Nyní Lv.{self.player.level}",
                               self.f_md, GOLD, cx, cy + 128)
        draw_text_centered(self.screen,
                           "Stiskni klávesu nebo klikni pro pokračování",
                           self.f_xs, TEXT_LT, cx, cy + 185)

    def _draw_gameover_overlay(self) -> None:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        self.screen.blit(overlay, (0, 0))
        cx, cy = SCREEN_W // 2, SCREEN_H // 2 - 90

        draw_text_centered(self.screen, "Konec hry",
                           self.f_xl, WRONG_COLOR, cx, cy)
        draw_text_centered(self.screen,
                           f"Dosáhl jsi úrovně {self.player.level}"
                           f"  •  XP: {self.player.xp}",
                           self.f_md, SILVER, cx, cy + 78)
        draw_text_centered(self.screen,
                           "Stiskni klávesu nebo klikni pro návrat do menu",
                           self.f_xs, TEXT_LT, cx, cy + 148)
