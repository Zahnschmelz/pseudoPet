# -*- coding: utf-8 -*-
"""
clock.py – Minimalistische Schwarz/Weiss Analog-Uhr fuer pygame

Nutzung in deinem Spiel:
    from clock import PixelClock

    uhr = PixelClock(x=166, y=26, scale=2)   # x/y = linke obere Ecke

    while running:
        uhr.draw(screen)                     # zeigt echte Systemzeit

Optionen:
    uhr = PixelClock(x=100, y=100, scale=3)  # groesser/kleiner
    uhr.draw(screen, time=(10, 10))          # feste Zeit (h, m) statt echte Zeit
"""

import math
from datetime import datetime, timedelta
import pygame


# =====================================================================
#  PIXEL-HELFER
# =====================================================================
def _dot(surf, x, y, color, thick=1):
    w, h = surf.get_size()
    o = (thick - 1) // 2
    for dy in range(thick):
        for dx in range(thick):
            px, py = int(x) + dx - o, int(y) + dy - o
            if 0 <= px < w and 0 <= py < h:
                surf.set_at((px, py), color)


def _line(surf, x0, y0, x1, y1, color, thick=1):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        _dot(surf, x0, y0, color, thick)
        if x0 == x1 and y0 == y1:
            break
        e2 = err * 2
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy


# =====================================================================
#  DIE UHR
# =====================================================================
class PixelClock:
    """Minimalistische Schwarz/Weiss Analog-Uhr."""

    # feste Palette
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)

    def __init__(self, x=0, y=0, scale=2, radius=13, time_offset=0.0):
        if not pygame.get_init():
            pygame.init()

        self.x = int(x)
        self.y = int(y)
        self.scale = max(1, int(scale))
        self.R = max(7, int(radius))
        self.time_offset = float(time_offset)

        self._cache_key = None
        self._cache_img = None

    def _build_face(self, fg, bg):
        R = self.R
        self.size = 2 * R + 1
        face = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        cx = cy = R
        for y in range(self.size):
            for x in range(self.size):
                dx, dy = x - cx, y - cy
                d = math.hypot(dx, dy)
                if d <= R - 1.0:
                    face.set_at((x, y), bg)
                elif d <= R - 0.1:
                    face.set_at((x, y), fg)
        for i in range(12):
            a = i * math.tau / 12.0
            major = (i % 3 == 0)
            r1 = R - 2.0
            r2 = r1 - (2.0 if major else 1.0)
            sx, sy = math.sin(a), -math.cos(a)
            thick = 2 if major else 1
            _line(face,
                  round(cx + sx * r1), round(cy + sy * r1),
                  round(cx + sx * r2), round(cy + sy * r2),
                  fg, thick)
        if not hasattr(self, 'len_hour'):
            self.len_hour = (R - 2.0) * 0.55
            self.len_min = (R - 2.0) * 0.82
            self.th_hour = 2
            self.th_min = 1
        return face

    # -------------------------------------------------- Zeit
    def current_time(self):
        now = datetime.now()
        if self.time_offset:
            now = now + timedelta(seconds=self.time_offset)
        return now.hour, now.minute

    # -------------------------------------------------- Zeichnen
    def _hand(self, surf, cx, cy, angle, length, thick, color):
        sx, sy = math.sin(angle), -math.cos(angle)
        _line(surf, cx, cy,
              round(cx + sx * length), round(cy + sy * length),
              color, thick)

    def _render(self, h, m, fg, bg):
        img = self._build_face(fg, bg)
        cx = cy = self.R
        a_h = math.tau * (((h % 12) + m / 60.0) / 12.0)
        a_m = math.tau * (m / 60.0)
        self._hand(img, cx, cy, a_m, self.len_min, self.th_min, fg)
        self._hand(img, cx, cy, a_h, self.len_hour, self.th_hour, fg)
        _dot(img, cx, cy, fg, 3)
        _dot(img, cx, cy, bg, 1)
        big = self.size * self.scale
        return pygame.transform.scale(img, (big, big))

    # -------------------------------------------------- API
    def set_scale(self, scale):
        self.scale = max(1, int(scale))
        self._cache_key = None

    def set_position(self, x, y):
        self.x, self.y = int(x), int(y)

    @property
    def rect(self):
        b = self.size * self.scale
        return pygame.Rect(self.x, self.y, b, b)

    def draw(self, surface, time=None, fg=None, bg=None):
        h, m = time if time is not None else self.current_time()
        if fg is None: fg = self.BLACK
        if bg is None: bg = self.WHITE

        key = (int(h), int(m), self.scale, fg, bg)
        if key == self._cache_key and self._cache_img is not None:
            img = self._cache_img
        else:
            img = self._render(h, m, fg, bg)
            self._cache_key, self._cache_img = key, img
        surface.blit(img, (self.x, self.y))
        return img.get_rect(topleft=(self.x, self.y))


# =====================================================================
#  MINIMAL-DEMO (nur zum Testen – einfach loeschbar)
# =====================================================================
if __name__ == "__main__":
    pygame.init()
    W, H = 240, 320
    ZOOM = 2
    screen = pygame.display.set_mode((W * ZOOM, H * ZOOM))
    pygame.display.set_caption("Pixel-Uhr S/W")
    ticker = pygame.time.Clock()
    font = pygame.font.SysFont("consolas,monospace", 14)

    scene = pygame.Surface((W, H))
    scene.fill((180, 180, 180))               # neutraler Grauton, damit man die Uhr sieht

    uhr = PixelClock(x=W // 2 - 27, y=H // 2 - 27, scale=2)   # mittig, 54x54 px

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif e.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    uhr.set_scale(uhr.scale + 1)
                elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    uhr.set_scale(uhr.scale - 1)

        scene.fill((180, 180, 180))
        uhr.draw(scene)

        screen.blit(pygame.transform.scale(scene, (W * ZOOM, H * ZOOM)), (0, 0))

        now = datetime.now()
        label = now.strftime("%H:%M  |  +/- Skalierung | ESC Ende")
        screen.blit(font.render(label, True, (30, 30, 30)), (6, 6))

        pygame.display.flip()
        ticker.tick(10)   # 10 FPS reicht voellig, Zeiger bewegen sich nur pro Minute

    pygame.quit()
