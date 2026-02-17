"""
UI komponenty pro Deutsch Klicker.
"""

import pygame
from dataclasses import dataclass, field
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Barvy
# ---------------------------------------------------------------------------
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0)
DARK_BG    = (30,  30,  50)
PANEL_BG   = (45,  45,  70)

CORRECT_COLOR  = (80,  200, 120)   # zelená
WRONG_COLOR    = (220,  60,  60)   # červená
NEUTRAL_COLOR  = (100, 120, 200)   # modrá (výchozí tlačítko)
HOVER_COLOR    = (130, 150, 230)
DISABLED_COLOR = (80,  80, 100)

GOLD    = (255, 215,   0)
SILVER  = (192, 192, 192)
TEXT_LT = (230, 230, 255)
TEXT_DK = (40,   40,  60)


# ---------------------------------------------------------------------------
# Pomocné funkce
# ---------------------------------------------------------------------------
def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Načte systémový font; fallback na pygame výchozí."""
    try:
        return pygame.font.SysFont("dejavu sans", size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


def draw_rounded_rect(surface: pygame.Surface, color, rect: pygame.Rect,
                      radius: int = 14) -> None:
    pygame.draw.rect(surface, color, rect, border_radius=radius)


def draw_text_centered(surface: pygame.Surface, text: str, font: pygame.font.Font,
                       color, cx: int, cy: int) -> pygame.Rect:
    """Vykreslí text vycentrovaný kolem bodu (cx, cy)."""
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=(cx, cy))
    surface.blit(rendered, rect)
    return rect


# ---------------------------------------------------------------------------
# Třída Button
# ---------------------------------------------------------------------------
class Button:
    """
    Klikatelné tlačítko s animací při najetí myší a barevnou odezvou.
    """

    def __init__(self, rect: pygame.Rect, text: str,
                 font: pygame.font.Font,
                 base_color=NEUTRAL_COLOR,
                 hover_color=HOVER_COLOR,
                 text_color=WHITE,
                 radius: int = 14):
        self.rect        = rect
        self.text        = text
        self.font        = font
        self.base_color  = base_color
        self.hover_color = hover_color
        self.text_color  = text_color
        self.radius      = radius

        self.current_color = base_color
        self.feedback_color: Optional[tuple] = None  # přechodná barva (správně/špatně)
        self.feedback_timer: int = 0                 # ms zbývající pro feedback
        self.enabled: bool = True

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Vrátí True, pokud bylo tlačítko kliknuto."""
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def set_feedback(self, correct: bool, duration_ms: int = 600) -> None:
        """Zobrazí zelenou/červenou barvu jako odezvu na klik."""
        self.feedback_color = CORRECT_COLOR if correct else WRONG_COLOR
        self.feedback_timer = duration_ms
        self.enabled = False

    def reset(self) -> None:
        self.feedback_color = None
        self.feedback_timer = 0
        self.enabled = True
        self.current_color = self.base_color

    def update(self, dt: int, mouse_pos: tuple) -> None:
        """Aktualizuje animace; dt je čas od posledního snímku v ms."""
        if self.feedback_timer > 0:
            self.feedback_timer = max(0, self.feedback_timer - dt)
            if self.feedback_timer == 0:
                self.feedback_color = None
        if not self.enabled:
            self.current_color = self.feedback_color or DISABLED_COLOR
        elif self.rect.collidepoint(mouse_pos):
            self.current_color = self.hover_color
        else:
            self.current_color = self.base_color

    def draw(self, surface: pygame.Surface) -> None:
        color = self.feedback_color if self.feedback_color else self.current_color
        draw_rounded_rect(surface, color, self.rect, self.radius)
        # Ohraničení
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=self.radius)
        draw_text_centered(surface, self.text, self.font,
                           self.text_color,
                           self.rect.centerx, self.rect.centery)


# ---------------------------------------------------------------------------
# Třída TimerBar
# ---------------------------------------------------------------------------
class TimerBar:
    """
    Vodorovný ukazatel zbývajícího času.
    Barva plynule přechází zelená → žlutá → červená.
    """

    def __init__(self, rect: pygame.Rect, max_ms: int):
        self.rect   = rect
        self.max_ms = max_ms
        self.remaining_ms = max_ms

    def reset(self, max_ms: Optional[int] = None) -> None:
        if max_ms is not None:
            self.max_ms = max_ms
        self.remaining_ms = self.max_ms

    def update(self, dt: int) -> bool:
        """
        Odečte dt ms. Vrátí True, pokud čas vypršel.
        """
        self.remaining_ms = max(0, self.remaining_ms - dt)
        return self.remaining_ms == 0

    def draw(self, surface: pygame.Surface) -> None:
        ratio = self.remaining_ms / self.max_ms if self.max_ms > 0 else 0

        # Pozadí
        draw_rounded_rect(surface, PANEL_BG, self.rect, 8)

        # Zbývající část
        if ratio > 0:
            filled = self.rect.copy()
            filled.width = int(self.rect.width * ratio)
            # Barva: zelená → žlutá → červená
            if ratio > 0.5:
                r = int(255 * (1 - ratio) * 2)
                g = 200
            else:
                r = 220
                g = int(200 * ratio * 2)
            bar_color = (r, g, 40)
            draw_rounded_rect(surface, bar_color, filled, 8)

        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=8)


# ---------------------------------------------------------------------------
# Třída ScoreDisplay
# ---------------------------------------------------------------------------
class ScoreDisplay:
    """Animované zobrazení skóre s vizuálním pulzem při změně."""

    def __init__(self, x: int, y: int, font: pygame.font.Font):
        self.x     = x
        self.y     = y
        self.font  = font
        self.score = 0
        self._pulse_timer = 0
        self._pulse_scale = 1.0

    def set_score(self, score: int) -> None:
        if score != self.score:
            self.score = score
            self._pulse_timer = 300  # ms

    def update(self, dt: int) -> None:
        if self._pulse_timer > 0:
            self._pulse_timer = max(0, self._pulse_timer - dt)
            t = self._pulse_timer / 300
            self._pulse_scale = 1.0 + 0.25 * t
        else:
            self._pulse_scale = 1.0

    def draw(self, surface: pygame.Surface) -> None:
        text = f"Skóre: {self.score}"
        rendered = self.font.render(text, True, GOLD)
        if self._pulse_scale != 1.0:
            w = int(rendered.get_width() * self._pulse_scale)
            h = int(rendered.get_height() * self._pulse_scale)
            rendered = pygame.transform.smoothscale(rendered, (w, h))
        rect = rendered.get_rect(center=(self.x, self.y))
        surface.blit(rendered, rect)


# ---------------------------------------------------------------------------
# Třída LivesDisplay
# ---------------------------------------------------------------------------
class LivesDisplay:
    """Zobrazení životů jako srdíčka."""

    HEART_FULL  = "♥"
    HEART_EMPTY = "♡"

    def __init__(self, x: int, y: int, font: pygame.font.Font, max_lives: int = 3):
        self.x         = x
        self.y         = y
        self.font      = font
        self.max_lives = max_lives
        self.lives     = max_lives

    def draw(self, surface: pygame.Surface) -> None:
        hearts = (self.HEART_FULL * self.lives +
                  self.HEART_EMPTY * (self.max_lives - self.lives))
        color = CORRECT_COLOR if self.lives > 1 else WRONG_COLOR
        draw_text_centered(surface, hearts, self.font, color, self.x, self.y)


# ---------------------------------------------------------------------------
# Třída MessageOverlay
# ---------------------------------------------------------------------------
class MessageOverlay:
    """
    Přechodná zpráva uprostřed obrazovky (např. „Správně!", „Špatně!").
    """

    def __init__(self, font: pygame.font.Font):
        self.font    = font
        self.text    = ""
        self.color   = WHITE
        self.timer   = 0
        self.visible = False

    def show(self, text: str, color=WHITE, duration_ms: int = 900) -> None:
        self.text    = text
        self.color   = color
        self.timer   = duration_ms
        self.visible = True

    def update(self, dt: int) -> None:
        if self.visible:
            self.timer = max(0, self.timer - dt)
            if self.timer == 0:
                self.visible = False

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        alpha = min(255, int(255 * self.timer / 900))
        rendered = self.font.render(self.text, True, self.color)
        rendered.set_alpha(alpha)
        cx = surface.get_width() // 2
        cy = surface.get_height() // 2 - 60
        rect = rendered.get_rect(center=(cx, cy))
        surface.blit(rendered, rect)
