"""
Herní logika pro Deutsch Klicker.

Stavy hry:
  MENU      – hlavní nabídka
  PLAYING   – aktivní kolo
  LEVEL_UP  – přechod na vyšší úroveň
  GAME_OVER – konec hry
"""

import random
import pygame

from words import get_unlocked_words, get_wrong_answers, LEVEL_UNLOCK, POINTS_PER_LEVEL
from ui import (
    Button, TimerBar, ScoreDisplay, LivesDisplay, MessageOverlay,
    load_font, draw_rounded_rect, draw_text_centered,
    DARK_BG, PANEL_BG, WHITE, BLACK, TEXT_LT, TEXT_DK,
    CORRECT_COLOR, WRONG_COLOR, GOLD, SILVER, NEUTRAL_COLOR, HOVER_COLOR,
)

# ---------------------------------------------------------------------------
# Konstanty
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 800, 600
FPS                = 60
MAX_LIVES          = 3
ANSWER_COUNT       = 4     # počet odpovědí na obrazovce
BASE_TIME_MS       = 8000  # základní čas na otázku (ms)
MIN_TIME_MS        = 3000  # minimální čas na otázku
TIME_DECREASE_PER_LEVEL = 500  # o kolik ms se zkrátí čas každou úrovní


def question_time(level: int) -> int:
    """Vrátí délku časovače pro danou úroveň v ms."""
    return max(MIN_TIME_MS, BASE_TIME_MS - (level - 1) * TIME_DECREASE_PER_LEVEL)


# ---------------------------------------------------------------------------
# GameState – enum-like konstanty
# ---------------------------------------------------------------------------
class State:
    MENU      = "menu"
    PLAYING   = "playing"
    LEVEL_UP  = "level_up"
    GAME_OVER = "game_over"


# ---------------------------------------------------------------------------
# Question – jedna otázka
# ---------------------------------------------------------------------------
class Question:
    def __init__(self, level: int):
        pool   = get_unlocked_words(level)
        self.correct  = random.choice(pool)
        wrongs         = get_wrong_answers(self.correct, level, ANSWER_COUNT - 1)
        options        = [self.correct["cz"]] + wrongs
        random.shuffle(options)
        self.options   = options   # seznam českých překladů (1 správný, 3 špatné)


# ---------------------------------------------------------------------------
# Hlavní třída Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.screen  = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Deutsch Klicker 🇩🇪")
        self.clock   = pygame.time.Clock()

        # Fonty
        self.font_xl  = load_font(64, bold=True)
        self.font_lg  = load_font(44, bold=True)
        self.font_md  = load_font(30, bold=True)
        self.font_sm  = load_font(22)
        self.font_xs  = load_font(18)

        self._build_menu()
        self.state = State.MENU
        self.running = True

        # Herní proměnné (inicializovány v reset())
        self.score    = 0
        self.level    = 1
        self.lives    = MAX_LIVES
        self.question: Question | None = None
        self.answer_buttons: list[Button] = []

        # UI prvky
        self.score_display = ScoreDisplay(SCREEN_W // 2, 30, self.font_md)
        self.lives_display = LivesDisplay(SCREEN_W - 100, 30, self.font_md, MAX_LIVES)
        self.timer_bar     = TimerBar(
            pygame.Rect(50, 60, SCREEN_W - 100, 18),
            BASE_TIME_MS,
        )
        self.message       = MessageOverlay(self.font_lg)

        self._waiting_next = False   # čekáme na přechod po feedbacku
        self._wait_timer   = 0

    # ------------------------------------------------------------------
    # Sestavení menu
    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        cx = SCREEN_W // 2
        self.menu_start_btn = Button(
            pygame.Rect(cx - 150, 300, 300, 60),
            "Hrát",
            load_font(32, bold=True),
        )
        self.menu_quit_btn = Button(
            pygame.Rect(cx - 150, 390, 300, 60),
            "Ukončit",
            load_font(32, bold=True),
        )

    # ------------------------------------------------------------------
    # Sestavení tlačítek odpovědí
    # ------------------------------------------------------------------
    def _build_answer_buttons(self) -> None:
        if self.question is None:
            return
        self.answer_buttons = []
        cx     = SCREEN_W // 2
        btn_w  = 340
        btn_h  = 62
        gap    = 16
        top    = 360

        positions = [
            (cx - btn_w - gap // 2, top),
            (cx + gap // 2,         top),
            (cx - btn_w - gap // 2, top + btn_h + gap),
            (cx + gap // 2,         top + btn_h + gap),
        ]

        for i, option in enumerate(self.question.options):
            x, y = positions[i]
            btn = Button(
                pygame.Rect(x, y, btn_w, btn_h),
                option,
                self.font_sm,
            )
            self.answer_buttons.append(btn)

    # ------------------------------------------------------------------
    # Reset / nová hra
    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.score   = 0
        self.level   = 1
        self.lives   = MAX_LIVES
        self.lives_display.lives = MAX_LIVES
        self.score_display.set_score(0)
        self._waiting_next = False
        self._wait_timer   = 0
        self._next_question()

    def _next_question(self) -> None:
        self.question = Question(self.level)
        self._build_answer_buttons()
        self.timer_bar.reset(question_time(self.level))
        self._waiting_next = False

    # ------------------------------------------------------------------
    # Zpracování odpovědi
    # ------------------------------------------------------------------
    def _handle_answer(self, chosen_cz: str) -> None:
        """Zavolá se po kliknutí na odpověď."""
        correct_cz = self.question.correct["cz"]
        is_correct = (chosen_cz == correct_cz)

        # Feedback na tlačítkách
        for btn in self.answer_buttons:
            btn.enabled = False
            if btn.text == correct_cz:
                btn.set_feedback(correct=True, duration_ms=700)
            elif btn.text == chosen_cz and not is_correct:
                btn.set_feedback(correct=False, duration_ms=700)

        if is_correct:
            bonus = max(1, int(self.timer_bar.remaining_ms / 500))
            self.score += 10 + bonus
            self.score_display.set_score(self.score)
            self.message.show("Správně! ✓", CORRECT_COLOR)
        else:
            self.lives -= 1
            self.lives_display.lives = self.lives
            self.message.show("Špatně! ✗", WRONG_COLOR)

        # Zkontroluj konec hry
        if self.lives <= 0:
            self._wait_timer   = 900
            self._waiting_next = False
            self._goto_gameover_after_delay = True
        else:
            # Zkontroluj level-up
            if self.score >= self.level * POINTS_PER_LEVEL:
                self._wait_timer              = 900
                self._waiting_next            = True
                self._goto_gameover_after_delay = False
            else:
                self._wait_timer              = 900
                self._waiting_next            = True
                self._goto_gameover_after_delay = False

        self._goto_gameover_after_delay = self.lives <= 0

    def _handle_timeout(self) -> None:
        """Zavolá se při vypršení časovače."""
        self.lives -= 1
        self.lives_display.lives = self.lives
        self.message.show("Čas vypršel!", WRONG_COLOR)

        for btn in self.answer_buttons:
            btn.enabled = False
            if btn.text == self.question.correct["cz"]:
                btn.set_feedback(correct=True, duration_ms=900)

        self._goto_gameover_after_delay = self.lives <= 0
        self._waiting_next              = not self._goto_gameover_after_delay
        self._wait_timer                = 1000

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

    def _process_events(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif self.state == State.MENU:
                if self.menu_start_btn.handle_event(event):
                    self.reset()
                    self.state = State.PLAYING
                if self.menu_quit_btn.handle_event(event):
                    self.running = False

            elif self.state == State.PLAYING:
                if not self._waiting_next and self._wait_timer == 0:
                    for i, btn in enumerate(self.answer_buttons):
                        if btn.handle_event(event):
                            self._handle_answer(btn.text)

            elif self.state == State.LEVEL_UP:
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    self._next_question()
                    self.state = State.PLAYING

            elif self.state == State.GAME_OVER:
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    self.state = State.MENU

    def _update(self, dt: int) -> None:
        mouse_pos = pygame.mouse.get_pos()

        if self.state == State.MENU:
            self.menu_start_btn.update(dt, mouse_pos)
            self.menu_quit_btn.update(dt, mouse_pos)

        elif self.state == State.PLAYING:
            self.score_display.update(dt)
            self.message.update(dt)

            for btn in self.answer_buttons:
                btn.update(dt, mouse_pos)

            # Čekáme na přechod?
            if self._wait_timer > 0:
                self._wait_timer = max(0, self._wait_timer - dt)
                if self._wait_timer == 0:
                    if self._goto_gameover_after_delay:
                        self.state = State.GAME_OVER
                    elif self.score >= self.level * POINTS_PER_LEVEL:
                        self.level += 1
                        self.state = State.LEVEL_UP
                    else:
                        self._next_question()
                return  # Nezajímá nás timer při čekání

            # Aktualizace časovače
            timed_out = self.timer_bar.update(dt)
            if timed_out:
                self._handle_timeout()

    def _draw(self) -> None:
        self.screen.fill(DARK_BG)

        if self.state == State.MENU:
            self._draw_menu()
        elif self.state == State.PLAYING:
            self._draw_playing()
        elif self.state == State.LEVEL_UP:
            self._draw_level_up()
        elif self.state == State.GAME_OVER:
            self._draw_game_over()

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Kreslení jednotlivých obrazovek
    # ------------------------------------------------------------------
    def _draw_menu(self) -> None:
        cx = SCREEN_W // 2

        draw_text_centered(self.screen, "🇩🇪 Deutsch Klicker", self.font_xl,
                           GOLD, cx, 130)
        draw_text_centered(self.screen, "Naučte se německá slova hraním!",
                           self.font_sm, TEXT_LT, cx, 210)
        draw_text_centered(self.screen, "Klikni na správný překlad a sbírej body.",
                           self.font_sm, SILVER, cx, 250)

        self.menu_start_btn.draw(self.screen)
        self.menu_quit_btn.draw(self.screen)

        draw_text_centered(self.screen, "v1.0  |  Python + Pygame",
                           self.font_xs, (100, 100, 130), cx, SCREEN_H - 30)

    def _draw_playing(self) -> None:
        cx = SCREEN_W // 2

        # HUD
        self.score_display.draw(self.screen)
        self.lives_display.draw(self.screen)
        draw_text_centered(self.screen, f"Úroveň {self.level}",
                           self.font_sm, TEXT_LT, 80, 30)

        # Časovač
        self.timer_bar.draw(self.screen)

        # Panel s německým slovem
        panel = pygame.Rect(cx - 300, 100, 600, 120)
        draw_rounded_rect(self.screen, PANEL_BG, panel, 16)
        pygame.draw.rect(self.screen, GOLD, panel, 2, border_radius=16)

        draw_text_centered(self.screen, "Jak se řekne česky:",
                           self.font_xs, SILVER, cx, 120)
        if self.question:
            draw_text_centered(self.screen, self.question.correct["de"],
                               self.font_lg, WHITE, cx, 165)

        # Tlačítka odpovědí
        draw_text_centered(self.screen, "Vyber správný překlad:",
                           self.font_xs, SILVER, cx, 340)
        for btn in self.answer_buttons:
            btn.draw(self.screen)

        # Zpráva (správně / špatně / čas)
        self.message.draw(self.screen)

    def _draw_level_up(self) -> None:
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        draw_text_centered(self.screen, f"Úroveň {self.level}!", self.font_xl,
                           GOLD, cx, cy - 80)
        draw_text_centered(self.screen, "Skvělá práce! Pokračuješ dál.",
                           self.font_md, CORRECT_COLOR, cx, cy)

        # Zjisti, co se odemklo
        new_cats = LEVEL_UNLOCK.get(self.level, [])
        if new_cats:
            unlock_text = "Nová kategorie: " + ", ".join(new_cats)
            draw_text_centered(self.screen, unlock_text,
                               self.font_sm, SILVER, cx, cy + 70)

        draw_text_centered(self.screen, "Klikni nebo stiskni klávesu pro pokračování",
                           self.font_xs, TEXT_LT, cx, cy + 140)

    def _draw_game_over(self) -> None:
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        draw_text_centered(self.screen, "Konec hry", self.font_xl,
                           WRONG_COLOR, cx, cy - 100)
        draw_text_centered(self.screen, f"Dosažené skóre: {self.score}",
                           self.font_lg, GOLD, cx, cy)
        draw_text_centered(self.screen, f"Dosažená úroveň: {self.level}",
                           self.font_md, SILVER, cx, cy + 70)
        draw_text_centered(self.screen, "Klikni nebo stiskni klávesu pro návrat do menu",
                           self.font_xs, TEXT_LT, cx, cy + 150)
