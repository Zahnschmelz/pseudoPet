# -*- coding: utf-8 -*-
"""
PIXEL ANGLER - Stardew-Angel-Mechanik als 1-Bit-Minigame,
integriert in PseudoPet (Menue: PLAY -> FISHING).

Interface wie MiniGameSnack / MiniGameDefense:
    MiniGameFish(pet) -> update(dt) / handle(btn) / draw(game)
                         finished / blocked_reason

Steuerung (PseudoPet-Buttons):
    B tippen  = Wurf / anbeissen (JETZT!) / weiter
    B HALTEN  = Fangfenster heben (Leertaste / Touch geht ebenfalls)

Layout: 240x320 virtuelle Pixel (= PseudoPet), wird am Ende pixelgenau
auf die echte Surface hochskaliert. Farben aus Game.get_colors().
Solo-Test ohne PseudoPet:  python fish.py
"""
import math
import random
import sys
from dataclasses import dataclass

import pygame

# ------------------------------------------------ zentrale Einstellungen
VW, VH = 240, 320            # virtuelle Pixel (= PseudoPet-Layout)
INK   = (26, 27, 22)         # Solo-Palette "Tinte"
PAPER = (236, 233, 222)      # Solo-Palette "Papier"
FPS = 30

# Szene
WATER_Y = 216
BOBBER_X, BOBBER_Y = 150, 220
ROD_BASE, ROD_TIP = (16, 270), (90, 224)

# Fangbalken links + Fortschrittsbalken daneben
TX, TY, TW, TH = 20, 30, 26, 180
PRX, PW = 50, 9

CASTS_MAX = 5                # Wuerfe pro Session
WAIT_MIN, WAIT_MAX = 1.2, 5.5
SHOW_CAUGHT, SHOW_ESCAPED = 2.8, 1.9

# Physik (normiert 0..1 ueber die Balkenhoehe)
GRAVITY, LIFT = 1.75, 3.65
MAX_SPEED, BOUNCE = 1.2, 0.57
FISH_VIS = 8.0 / TH                     # sichtbare Hoehe des Fisch-Sprites
FILL_EASY, FILL_HARD = 0.147, 0.107       # Fortschritt pro Sek. (leicht/schwer)
DRAIN_BASE, DRAIN_DIFF = 0.147, 0.107     # Fortschrittsverlust pro Sek.
BITE_WINDOW = 0.80                      # Reaktionszeit beim Biss

def lerp(a, b, f):    return a + (b - a) * f
def clamp(v, lo, hi): return max(lo, min(hi, v))

# ------------------------------------------------ 3x5-Bitmap-Font (Caps)
FONT = {
    "A": (0b010, 0b101, 0b111, 0b101, 0b101), "B": (0b110, 0b101, 0b110, 0b101, 0b110),
    "C": (0b011, 0b100, 0b100, 0b100, 0b011), "D": (0b110, 0b101, 0b101, 0b101, 0b110),
    "E": (0b111, 0b100, 0b110, 0b100, 0b111), "F": (0b111, 0b100, 0b110, 0b100, 0b100),
    "G": (0b111, 0b100, 0b101, 0b101, 0b111), "H": (0b101, 0b101, 0b111, 0b101, 0b101),
    "I": (0b111, 0b010, 0b010, 0b010, 0b111), "J": (0b001, 0b001, 0b001, 0b101, 0b010),
    "K": (0b101, 0b101, 0b110, 0b101, 0b101), "L": (0b100, 0b100, 0b100, 0b100, 0b111),
    "M": (0b101, 0b111, 0b111, 0b101, 0b101), "N": (0b110, 0b101, 0b101, 0b101, 0b101),
    "O": (0b010, 0b101, 0b101, 0b101, 0b010), "P": (0b110, 0b101, 0b110, 0b100, 0b100),
    "Q": (0b010, 0b101, 0b101, 0b010, 0b001), "R": (0b110, 0b101, 0b110, 0b101, 0b101),
    "S": (0b011, 0b100, 0b010, 0b001, 0b110), "T": (0b111, 0b010, 0b010, 0b010, 0b010),
    "U": (0b101, 0b101, 0b101, 0b101, 0b111), "V": (0b101, 0b101, 0b101, 0b101, 0b010),
    "W": (0b101, 0b101, 0b111, 0b111, 0b101), "X": (0b101, 0b101, 0b010, 0b101, 0b101),
    "Y": (0b101, 0b101, 0b010, 0b010, 0b010), "Z": (0b111, 0b001, 0b010, 0b100, 0b111),
    "0": (0b111, 0b101, 0b101, 0b101, 0b111), "1": (0b010, 0b110, 0b010, 0b010, 0b111),
    "2": (0b110, 0b001, 0b010, 0b100, 0b111), "3": (0b110, 0b001, 0b010, 0b001, 0b110),
    "4": (0b101, 0b101, 0b111, 0b001, 0b001), "5": (0b111, 0b100, 0b110, 0b001, 0b110),
    "6": (0b111, 0b100, 0b110, 0b101, 0b111), "7": (0b111, 0b001, 0b001, 0b010, 0b010),
    "8": (0b111, 0b101, 0b111, 0b101, 0b111), "9": (0b111, 0b101, 0b111, 0b001, 0b110),
    " ": (    0,     0,     0,     0,     0), ".": (    0,     0,     0,     0, 0b010),
    "!": (0b010, 0b010, 0b010,     0, 0b010), ":": (    0, 0b010,     0, 0b010,     0),
    "=": (    0, 0b111,     0, 0b111,     0), "-": (    0,     0, 0b111,     0,     0),
    "+": (    0, 0b010, 0b111, 0b010,     0), "*": (0b101, 0b010, 0b101,     0,     0),
    "/": (0b001, 0b001, 0b010, 0b100, 0b100),
}

def draw_text(surf, txt, x, y, color):
    x, y = int(x), int(y)
    for ch in txt:
        for r, bits in enumerate(FONT.get(ch, FONT[" "])):
            for c in range(3):
                if bits & (4 >> c):
                    surf.fill(color, (x + c, y + r, 1, 1))
        x += 4

def text_w(txt):  return 4 * len(txt) - 1
def draw_textc(surf, txt, cx, y, color):
    draw_text(surf, txt, cx - text_w(txt) // 2, y, color)

# ------------------------------------------------ 1-Bit-Sprites
FISH_A = ("..XXX...",
          "X.XXX..X",
          ".XXXXXXX",
          "..XX....")

FISH_B = ("..XXX...",
          "X.XXX...",
          ".XXXXXX.",
          "..XX..X.")

BOBBER = (".XXX.",
          "X.X.X",
          "XX.XX",
          "X...X",
          ".XXX.")

CLOUD  = ("....XXXX...",
          "..XXXXXXXX.",
          "XXXXXXXXXXX")

def sprite(rows, color, scale=1):
    h, w = len(rows), len(rows[0])
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for yy, row in enumerate(rows):
        for xx, ch in enumerate(row):
            if ch == "X":
                s.fill(color, (xx, yy, 1, 1))
    if scale > 1:
        s = pygame.transform.scale(s, (w * scale, h * scale))
    return s

# ------------------------------------------------ Fische
@dataclass
class FishType:
    name: str
    difficulty: float
    min_len: float
    max_len: float
    price: int
    weight: int

FISH_TYPES = [
    FishType("SARDINE", 0.15, 8, 25, 1, 10),
    FishType("BARSCH", 0.28, 12, 40, 2, 12),
    FishType("FORELLE", 0.32, 20, 60, 3, 10),
    FishType("WELS", 0.36, 30, 100, 4, 9),
    FishType("SCHNAPPSCHWANZ", 0.40, 80, 120, 5, 10),
    FishType("SPRINGSCHNAPPER", 0.42, 40, 80, 6, 8),
    FishType("NEMOFISCH", 0.44, 8, 25, 7, 5),
    FishType("ANGLERFISCH", 0.46, 25, 100, 8, 10),
    FishType("DICKER HERING", 0.52, 20, 99, 9, 9),
    FishType("PIMMLER", 0.54, 29, 85, 10, 6),
    FishType("PUMMELQUALLE", 0.56, 32, 64, 11, 7),
]

class Fish:
    """SDV-'mixed'-Bewegung: gemuetliches Treiben + zufaellige Darts."""
    def __init__(self, diff):
        self.d = diff
        self.y, self.vy, self.target = 0.5, 0.0, 0.5
        self.timer = random.uniform(0.5, 1.4)
        self.dart = False

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            if random.random() < 0.12 + 0.55 * self.d:      # Dart!
                self.dart, self.timer = True, random.uniform(0.25, 0.7)
                self.vy = (random.uniform(0.45, 0.85) + 0.9 * self.d) \
                          * random.choice((-1, 1))
            else:                                           # treiben
                self.dart, self.timer = False, \
                    random.uniform(0.7, 1.7) * (1.1 - 0.5 * self.d)
                self.target = clamp(self.y + random.uniform(-0.35, 0.35), 0.15, 0.85)
        if self.dart:
            self.vy *= (1 - 0.8 * dt)
        else:
            self.vy += (self.target - self.y) * 6.0 * dt
            self.vy -= self.vy * 3.0 * dt
        self.y += self.vy * dt
        if self.y < 0:   self.y, self.vy = 0.0, abs(self.vy) * 0.5
        elif self.y > 1: self.y, self.vy = 1.0, -abs(self.vy) * 0.5

class HookBar:
    """Das schwarze Fangfenster: Halten = Auftrieb, sonst Gravitation."""
    def __init__(self, size):
        self.size, self.y, self.vy = size, 0.5, 0.0

    def update(self, dt, held):
        if held: self.vy -= LIFT * dt
        self.vy += GRAVITY * dt
        self.vy = clamp(self.vy, -MAX_SPEED, MAX_SPEED)
        self.y += self.vy * dt
        lo, hi = self.size / 2, 1 - self.size / 2
        if self.y < lo:   self.y, self.vy = lo, abs(self.vy) * BOUNCE
        elif self.y > hi: self.y, self.vy = hi, -abs(self.vy) * BOUNCE

class MiniGame:
    def __init__(self, ftype):
        self.ftype = ftype
        self.fish = Fish(ftype.difficulty)
        self.bar = HookBar(lerp(0.30, 0.13, ftype.difficulty))
        self.progress, self.perfect = 0.25, True
        self.done, self.result = False, None

    def update(self, dt, held):
        self.fish.update(dt)
        self.bar.update(dt, held)
        half = (self.bar.size + FISH_VIS) / 2
        d = abs(self.fish.y - self.bar.y)
        if d < half:
            bonus = 1.0 + 0.5 * (1.0 - d / half)
            self.progress += lerp(FILL_EASY, FILL_HARD, self.ftype.difficulty) * bonus * dt
        else:
            self.perfect = False
            self.progress -= (DRAIN_BASE + DRAIN_DIFF * self.ftype.difficulty) * dt
        if self.progress >= 1.0: self.progress, self.done, self.result = 1.0, True, "caught"
        elif self.progress <= 0.0: self.progress, self.done, self.result = 0.0, True, "escaped"

# ============================================================
#  ADAPTER: PIXEL ANGLER als PseudoPet-Minigame
# ============================================================
class MiniGameFish:

    def __init__(self, pet=None):
        self.pet = pet
        self.finished = False
        self.blocked_reason = None

        # Cooldown/Schlafen wie bei den anderen Minigames
        m = sys.modules.get("__main__")
        _cd = getattr(m, "LIMITS", {}).get("minigame", 30.0)
        if pet is not None:
            if getattr(pet, "sleeping", False):
                self.blocked_reason = "sleep"
            elif pet.age - getattr(pet, "_last_minigame", -1e9) < _cd:
                self.blocked_reason = "cooldown"
        if self.blocked_reason:
            self.finished = True

        # optionale Sounds (von main.py zugewiesen)
        self.bite_sound = None
        self.catch_sound = None

        self.vp = pygame.Surface((VW, VH))
        self._ink = self._paper = None      # erzwingt Sprite-Rebuild im 1. Draw

        self.state, self.state_t = "idle", 0.0
        self.t = 0.0
        self.ftype, self.mg, self.catch = None, None, None
        self.note = ""
        self.wait_time = 0.0
        self.casts_left = CASTS_MAX
        self.catch_count, self.gold, self.perfect_count = 0, 0, 0
        self.ripples, self.ripple_timer = [], 0.0
        self.held = False
        self._c_hold = 0.0
        self._game = None
        self.clouds = [[30, 20, 3], [130, 44, 2]]

    # ---- Eingabe: B tippen (Event) + B halten (Status) ----
    def _btn_zones(self):
        """Virtuelle Hitbox-Zonen der PseudoPet-Tasten A/B/C."""
        y = 238
        h = VH - y
        return [pygame.Rect(0, y, 81, h),
                pygame.Rect(81, y, 77, h),
                pygame.Rect(158, y, VW - 158, h)]

    def _held_buttons(self):
        """Welche PseudoPet-Tasten (0=A, 1=B, 2=C) werden gerade gehalten?"""
        held = set()
        kp = pygame.key.get_pressed()
        if kp[pygame.K_a] or kp[pygame.K_LEFT]:
            held.add(0)
        if kp[pygame.K_s] or kp[pygame.K_RETURN] or kp[pygame.K_SPACE]:
            held.add(1)
        if kp[pygame.K_d] or kp[pygame.K_BACKSPACE]:
            held.add(2)
        if any(pygame.mouse.get_pressed()):
            g = self._game
            if g is not None:
                pos = pygame.mouse.get_pos()
                if hasattr(g, "to_virtual"):
                    mx, my = g.to_virtual(pos)
                else:
                    s = max(1, g.surface.get_width() // VW)
                    mx, my = pos[0] // s, pos[1] // s
                for i, r in enumerate(self._btn_zones()):
                    if r.collidepoint(mx, my):
                        held.add(i)
        return held

    def _held(self):
        """Haelt der Spieler B? (nur noch Taste/Zone B, nicht mehr ueberall)"""
        return 1 in self._held_buttons()

    def handle(self, btn):
        if self.finished:
            return
        if btn == 1:                          # B ist die Angel
            self._press()

    def _press(self):
        if self.state == "idle" and self.casts_left > 0:
            self.casts_left -= 1
            self.state, self.state_t = "cast", 0.0
            self.ftype = random.choices(
                FISH_TYPES, weights=[f.weight for f in FISH_TYPES])[0]
        elif self.state == "bite":
            self.mg = MiniGame(self.ftype)
            self.state, self.state_t, self.ripple_timer = "play", 0.0, 0.0
            self._snd("bite_sound")
        elif self.state in ("caught", "escaped"):
            if self.casts_left > 0:
                self.state, self.state_t = "idle", 0.0
            else:
                self.finish()

    def _snd(self, attr):
        s = getattr(self, attr, None)
        if s is not None:
            try:
                s.play()
            except Exception:
                pass

    # ---- Logik ----
    def update(self, dt):
        if self.finished:
            return
        dt = min(dt, 0.1)
        self.t += dt; self.state_t += dt
        hb = self._held_buttons()
        self.held = 1 in hb
        if 2 in hb:
            self._c_hold += dt
            if self._c_hold >= 3.0:
                self.finish()
                return
        else:
            self._c_hold = 0.0
        self.ripples = [r for r in self.ripples if r[2] < 0.9]
        for r in self.ripples: r[2] += dt
        for c in self.clouds:
            c[0] += c[2] * dt
            if c[0] > VW: c[0] = -13

        if self.state == "cast":
            if self.state_t >= 0.45:
                self.state, self.state_t = "wait", 0.0
                self.wait_time = random.uniform(WAIT_MIN, WAIT_MAX)
                self._rings(3)
        elif self.state == "wait":
            if self.state_t >= self.wait_time:
                self.state, self.state_t = "bite", 0.0
                self._rings(2)
        elif self.state == "bite":
            if self.state_t > BITE_WINDOW:
                self.state, self.state_t, self.note = "escaped", 0.0, "ZU LANGSAM!"
        elif self.state == "play":
            self.mg.update(dt, self.held)
            self.ripple_timer -= dt
            if self.ripple_timer <= 0:      # zappelnder Schwimmer
                self._rings(1); self.ripple_timer = 0.5
            if self.mg.done:
                if self.mg.result == "caught":
                    self._on_caught()
                else:
                    self.state, self.state_t, self.note = "escaped", 0.0, "ENTKOMMT!"
                self.mg = None
        elif self.state == "caught":
            if self.state_t > SHOW_CAUGHT:
                if self.casts_left > 0: self.state, self.state_t = "idle", 0.0
                else: self.finish()
        elif self.state == "escaped":
            if self.state_t > SHOW_ESCAPED:
                if self.casts_left > 0: self.state, self.state_t = "idle", 0.0
                else: self.finish()

    def _rings(self, n):
        for i in range(n):
            self.ripples.append([BOBBER_X, BOBBER_Y, -0.18 * i])

    def _on_caught(self):
        ft, perfect = self.ftype, self.mg.perfect
        norm = random.random()
        size = lerp(ft.min_len, ft.max_len, norm)
        value = round(ft.price * (0.7 + 0.6 * norm)) * (2 if perfect else 1)
        self.catch = (ft.name, size, value, perfect)
        self.catch_count += 1; self.gold += value
        if perfect: self.perfect_count += 1
        self.state, self.state_t = "caught", 0.0
        self._snd("catch_sound")

    def finish(self):
        if self.finished:
            return
        self.finished = True
        p = self.pet
        if p is None:
            return
        p._last_minigame = p.age
        bonus = max(0, min(30, self.gold // 4))
        p.happiness = min(100.0, p.happiness + bonus)
        if self.catch_count:
            p.hunger = max(0.0, p.hunger - min(30.0, 4.0 * self.catch_count))
        p.energy = max(0.0, p.energy - 10)
        p.play_count += 1
        p.state = getattr(sys.modules.get("__main__"),
                          "STATE_PLAYING", "playing")
        p.state_timer = 0.0
        p.calling = False

    # ---- Schwimmer-Position je Zustand ----
    def _bobber(self):
        if self.state == "cast":
            f = min(1.0, self.state_t / 0.45)
            x = lerp(ROD_TIP[0] + 2, BOBBER_X, f)
            y = lerp(ROD_TIP[1] + 6, BOBBER_Y, f) - math.sin(f * math.pi) * 55
            return x, y
        if self.state == "idle":
            return ROD_TIP[0] + 2, ROD_TIP[1] + 6
        y = BOBBER_Y + math.sin(self.t * 2.0) * 1.5
        if self.state == "bite": y = BOBBER_Y + 3 + math.sin(self.t * 30) * 2
        if self.state == "play": y = BOBBER_Y + 2 + math.sin(self.t * 16) * 3
        if self.state in ("caught", "escaped"):
            f = min(1.0, self.state_t * 2)
            return lerp(BOBBER_X, ROD_TIP[0] + 2, f), lerp(BOBBER_Y, ROD_TIP[1] + 6, f)
        return BOBBER_X, y

    # ---- Farben / Sprites (bei Tag/Nacht-Wechsel neu bauen) ----
    def _set_colors(self, c):
        ink, paper = c["fg"], c["bg"]
        if (ink, paper) == (self._ink, self._paper):
            return
        self._ink, self._paper = ink, paper
        self.fish = [sprite(FISH_A, ink, 2), sprite(FISH_B, ink, 2)]
        self.fish_inv = [sprite(FISH_A, paper, 2), sprite(FISH_B, paper, 2)]
        self.bob = sprite(BOBBER, ink)
        self.cloud = sprite(CLOUD, ink)
        self.fish_big = sprite(FISH_A, ink, 4)
        self.bg = self._build_bg(ink, paper)

    def _build_bg(self, ink, paper):
        bg = pygame.Surface((VW, VH))
        bg.fill(paper)
        cx, cy = 205, 56                 # Sonne: Ring + Strahlen
        pygame.draw.circle(bg, ink, (cx, cy), 7, 1)
        for a in range(0, 360, 45):
            bg.fill(ink, (int(cx + math.cos(math.radians(a)) * 10),
                          int(cy + math.sin(math.radians(a)) * 10), 1, 1))
        bg.fill(ink, (0, WATER_Y, VW, 1))        # Wasserlinie + Punkt-Raster
        for yy in range(WATER_Y + 5, 264, 6):
            off = (yy // 6 % 3) * 3
            for xx in range(2 + off, VW, 7):
                bg.fill(ink, (xx, yy, 1, 1))
        for i in range(0, 101, 5):               # Angelrute + Rolle + Griff
            f = i / 100.0
            x = int(lerp(ROD_BASE[0], ROD_TIP[0], f))
            y = int(lerp(ROD_BASE[1], ROD_TIP[1], f))
            w = 3 if f < 0.35 else (2 if f < 0.75 else 1)
            bg.fill(ink, (x, y, w, w))
        bg.fill(ink, (18, 258, 5, 4)); bg.fill(paper, (19, 259, 3, 2))
        bg.fill(ink, (11, 268, 7, 10))
        return bg

    # ---- Rendering ----
    def draw(self, game):
        self._game = game
        c = game.get_colors()
        self._set_colors(c)
        if self.blocked_reason:
            self._draw_end(game)
            return
        self._render(game)
        if self.finished:
            self._draw_end(game)

    def _render(self, game):
        vp = self.vp
        ink, paper = self._ink, self._paper
        vp.blit(self.bg, (0, 0))
        for cl in self.clouds:
            vp.blit(self.cloud, (int(cl[0]), cl[1]))
        for k, y0 in enumerate((WATER_Y + 12, WATER_Y + 28)):   # Wellen
            for x in range(0, VW, 3):
                y = y0 + int(math.sin((x + self.t * (22 + k * 12)) * 0.045
                                      + k * 2.1) * 2)
                vp.fill(ink, (x, y, 2, 1))
        bx, by = self._bobber()                                 # Schnur + Schwimmer
        dx, dy = ROD_TIP[0] - bx, ROD_TIP[1] - by
        n = max(1, int(math.hypot(dx, dy)))
        for i in range(0, n + 1, 2):
            f = i / n
            vp.fill(ink, (int(bx + dx * f), int(by + dy * f), 1, 1))
        vp.blit(self.bob, (int(bx) - 2, int(by) - 2))
        for x, y, age in self.ripples:                          # Wasser-Ringe
            if age < 0 or age > 0.8: continue
            r = 2 + int(age * 26)
            if r < 16:
                pygame.draw.ellipse(vp, ink, (x - r, y - r // 2, 2 * r, r), 1)

        self._draw_track(vp, ink, paper)
        self._draw_hud(vp, ink)
        blink = int(self.t * 5) % 2 == 0

        if self.state == "idle":
            self._draw_title(vp, ink, blink)
        elif self.state == "wait":
            draw_textc(vp, "WARTEN...", VW // 2, 276, ink)
        elif self.state == "bite":
            self._draw_alert(vp, ink, paper, bx, by)
            if blink: draw_textc(vp, "JETZT!", VW // 2, 276, ink)
        elif self.state == "play":
            draw_textc(vp, "B HALTEN = FISCHEN", VW // 2, 276, ink)
        elif self.state == "caught":
            self._draw_caught(vp, ink, paper, blink)
        elif self.state == "escaped":
            w = text_w(self.note)
            rx, ry = VW // 2 - w // 2 - 4, 196
            vp.fill(paper, (rx, ry, w + 8, 15))
            pygame.draw.rect(vp, ink, (rx, ry, w + 8, 15), 1)
            draw_textc(vp, self.note, VW // 2, ry + 5, ink)

        # >>> zentrales Upscaling auf die PseudoPet-Flaeche <<<
        pygame.transform.scale(vp, game.surface.get_size(), game.surface)

    def _draw_hud(self, vp, ink):
        draw_text(vp, "FISCHE %d" % self.catch_count, 6, 5, ink)
        draw_textc(vp, "WURF %d/%d" % (CASTS_MAX - self.casts_left, CASTS_MAX),
                   VW // 2, 5, ink)
        if self._c_hold > 0.05:
            frac = min(1.0, self._c_hold / 3.0)
            bx, bw = VW // 2 - 30, 60
            vp.fill(ink, (bx, 14, int(bw * frac), 2))
            draw_textc(vp, "C HALTEN: ENDE", VW // 2, 18, ink)

    def _draw_title(self, vp, ink, blink):
        tmp = pygame.Surface((text_w("PSEUDO ANGLER"), 5), pygame.SRCALPHA)
        draw_text(tmp, "PSEUDO ANGLER", 0, 0, ink)
        big = pygame.transform.scale(tmp, (tmp.get_width() * 2, 10))
        vp.blit(big, (VW // 2 - big.get_width() // 2, 54))
        draw_textc(vp, "ANGELN", VW // 2, 74, ink)
        if blink:  draw_textc(vp, "B TIPPEN = WURF", VW // 2, 94, ink)
        draw_textc(vp, "B HALTEN = FISCHEN", VW // 2, 108, ink)
        draw_textc(vp, "C 3S HALTEN = ENDE", VW // 2, 122, ink)

    def _draw_track(self, vp, ink, paper):
        """Fangbalken + Fortschritt. Fisch wird PAPER, sobald er im
        schwarzen Fenster ist (uebermalen mit Clip auf die Box)."""
        for yy in range(TY + 4, TY + TH - 2, 6):        # Mittel-Linie
            vp.fill(ink, (TX + TW // 2, yy, 1, 2))
        if self.state == "play" and self.mg:            # Fangfenster
            bh = int(self.mg.bar.size * TH)
            by = int(TY + (self.mg.bar.y - self.mg.bar.size / 2) * TH)
            vp.fill(ink, (TX + 1, by, TW - 2, bh))
        vp.fill(paper, (TX, TY, 1, TH))                 # Rahmen danach
        vp.fill(paper, (TX + TW - 1, TY, 1, TH))
        pygame.draw.rect(vp, ink, (TX - 1, TY - 1, TW + 2, TH + 2), 1)
        if self.state == "play" and self.mg:
            frame = int(self.t / 0.22) % 2              # Fisch (wedelnd)
            fx, fy = TX + (TW - 16) // 2, int(TY + self.mg.fish.y * TH - 4)
            vp.blit(self.fish[frame], (fx, fy))
            bh = int(self.mg.bar.size * TH)
            by = int(TY + (self.mg.bar.y - self.mg.bar.size / 2) * TH)
            vp.set_clip((TX + 1, by, TW - 2, bh))
            vp.blit(self.fish_inv[frame], (fx, fy))     # invertiert im Fenster
            vp.set_clip(None)
            pygame.draw.rect(vp, ink, (PRX - 1, TY - 1, PW + 2, TH + 2), 1)
            ph = int(self.mg.progress * TH)             # Fortschrittsbalken
            if ph: vp.fill(ink, (PRX, TY + TH - ph, PW, ph))
            if self.mg.perfect and int(self.t * 4) % 2:
                draw_text(vp, "*", PRX + 3, TY - 8, ink)
            draw_textc(vp, self.mg.ftype.name, TX + TW // 2, 20, ink)
            for i in range(5):                          # Schwierigkeits-Punkte
                x = TX + TW // 2 - 9 + i * 4
                if i < round(self.mg.ftype.difficulty * 5):
                    vp.fill(ink, (x, 34, 2, 2))
                else:
                    vp.fill(ink, (x, 34, 1, 1))
        else:
            pygame.draw.rect(vp, ink, (PRX - 1, TY - 1, PW + 2, TH + 2), 1)

    def _draw_alert(self, vp, ink, paper, bx, by):
        r = (int(bx) - 5, int(by) - 32, 11, 12)
        if int(self.t * 8) % 2:
            vp.fill(ink, r); draw_text(vp, "!", int(bx) - 1, int(by) - 29, paper)
        else:
            vp.fill(paper, r); pygame.draw.rect(vp, ink, r, 1)
            draw_text(vp, "!", int(bx) - 1, int(by) - 29, ink)
        vp.fill(ink, (int(bx) - 1, int(by) - 20, 1, 3))

    def _draw_caught(self, vp, ink, paper, blink):
        name, size, value, perfect = self.catch
        x, y, w, h = 30, 76, 180, 128
        vp.fill(paper, (x, y, w, h))
        pygame.draw.rect(vp, ink, (x, y, w, h), 1)
        pygame.draw.rect(vp, ink, (x + 3, y + 3, w - 6, h - 6), 1)
        draw_textc(vp, "GEFANGEN!", VW // 2, y + 10, ink)
        vp.blit(self.fish_big, (x + 12, y + 30))
        draw_text(vp, name, x + 52, y + 30, ink)
        draw_text(vp, "%d CM" % int(size), x + 52, y + 42, ink)
        draw_text(vp, "+%d G" % value, x + 52, y + 54, ink)
        if perfect:
            tw = text_w("PERFEKT! X2")
            rx, ry = VW // 2 - tw // 2 - 4, y + 74
            if blink:
                vp.fill(ink, (rx, ry, tw + 8, 11))
                draw_text(vp, "PERFEKT! X2", rx + 4, ry + 3, paper)
            else:
                pygame.draw.rect(vp, ink, (rx, ry, tw + 8, 11), 1)
                draw_text(vp, "PERFEKT! X2", rx + 4, ry + 3, ink)
        draw_textc(vp, "B = WEITER", VW // 2, y + h - 16, ink)

    def _draw_end(self, game):
        c = game.get_colors()
        surf = game.surface
        S = surf.get_width() // VW
        if self.blocked_reason:
            surf.fill(c["bg"])
        r = pygame.Rect(40 * S, 70 * S, 160 * S, 135 * S)
        pygame.draw.rect(surf, c["box_bg"], r)
        pygame.draw.rect(surf, c["box_border"], r, 2 * S)

        def center(txt, font, y):
            t = font.render(txt, True, c["text"])
            surf.blit(t, t.get_rect(center=(VW * S // 2, y * S)))

        if self.blocked_reason:
            center("ZZZ..." if self.blocked_reason == "sleep" else "WAIT!",
                   game.font_huge, 96)
            center("B: OK", game.font_big, 150)
            return
        bonus = max(0, min(30, self.gold // 4))
        center("FISHING!", game.font_huge, 88)
        center("Fish x%d" % self.catch_count, game.font, 112)
        #enter("Gold %d" % self.gold, game.font, 128)
        center("Perfect x%d" % self.perfect_count, game.font, 144)
        center("Happy +%d" % bonus, game.font_big, 168)
        center("B: OK", game.font_big, 192)

# ------------------------------------------------ Solo-Test (ohne PseudoPet)
def _solo():
    pygame.init()
    S = 3
    screen = pygame.display.set_mode((VW * S, VH * S))
    pygame.display.set_caption("PIXEL ANGLER - Solo-Test")
    try:
        f = pygame.font.SysFont("consolas", 10 * S)
        fb = pygame.font.SysFont("consolas", 13 * S, bold=True)
        fh = pygame.font.SysFont("consolas", 18 * S, bold=True)
    except Exception:
        f = pygame.font.Font(None, 14 * S)
        fb = pygame.font.Font(None, 16 * S)
        fh = pygame.font.Font(None, 24 * S)

    class _G:
        surface = screen
        font, font_big, font_huge = f, fb, fh
        def get_colors(self):
            return {"bg": PAPER, "fg": INK, "text": INK,
                    "box_bg": PAPER, "box_border": INK}

    game = _G()
    mg = MiniGameFish(None)
    end_t, clock = 0.0, pygame.time.Clock()
    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        restart = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                elif ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_s):
                    if mg.finished: restart = True
                    else: mg.handle(1)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if mg.finished: restart = True
                else: mg.handle(1)
        if mg.finished:
            end_t += dt
            if end_t > 4.0: restart = True
        if restart:
            mg, end_t = MiniGameFish(None), 0.0
        mg.update(dt)
        mg.draw(game)
        pygame.display.flip()

if __name__ == "__main__":
    _solo()
