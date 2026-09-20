# snack.py
import random
import pygame
from config import LIMITS, STATE_PLAYING
from screen import VW, rs, rh, rp, rrect

GAME_TIME            = 30.0     # Spieldauer
SPAWN_STOP_LEAD      = 3.0      # keine Gegner mehr X s vor Ende
SPAWN_MIN            = 0.8      # Spawn-Intervall-Min
SPAWN_MAX            = 1.5      # Spawn-Intervall-Max
SPAWN_RAMP           = 0.45     # Intervall schrumpft um bis zu...
SPAWN_RAMP_TIME      = 60.0     # ...soviel, innerhalb dieser Zeit
ENEMY_BASE_SPEED     = 26.0     # vx = ENEMY_BASE_SPEED * (1 + speed)
ENEMY_MARGIN         = 30       # Rand, ab dem Gegner despawnen
ZIGZAG_DIV           = 10.0     # Zickzack-Wellenlänge: sin(x/DIV) -> ~63 px pro Welle
ZIGZAG_AMP           = 8.0      # Zickzack-Höhe: ±8 px um die Grundlinie
WOBBLE_DIV           = 16.0     # Wobble-Wellenlänge (sanfter: ~100 px)
WOBBLE_AMP           = 5.0      # Wobble-Höhe: ±5 px
HITBOX_X, HITBOX_Y   = 13, 11   # Trefferbox
HIT_FLASH            = 0.12     # Blitzdauer nach Treffer
SHOT_CD              = 0.3      # Feuerrate
SHOT_SPEED           = 420.0    # Projektil-Tempo
KILL_FX_COUNT        = 6        # Partikel pro Kill
FX_LIFETIME          = 0.5      # Kill-Partikel leben X s
FX_VX                = (-60.0, 60.0) # Partikel-Streuung horizontal (px/s)
FX_VY                = (-70.0, 10.0) # Partikel-Streuung vertikal (fliegen überwiegend nach OBEN)
BONUS_MAX            = 30       # maximaler Glücks-Bonus am Rundenende
BONUS_DIV            = 4        # alle X Score-Punkte = 1 Bonuspunkt
BONUS_ESCAPE_PEN     = 1.5      # jeder entkommene Gegner kostet 1.5 Bonuspunkte

class MiniGameSnack:

    def __init__(self, pet):
        self.pet = pet
        self.items = []
        self.px = VW // 2
        self.counts = {"apple": 0, "heart": 0, "sock": 0}
        self.time_left = GAME_TIME
        self.spawn_t = SPAWN_MIN
        self.finished = False
        self.flash = 0.0
        self.flash_bad = False
        self.blocked_reason = None
        if getattr(pet, "sleeping", False):
            self.blocked_reason = "sleep"
        elif pet.age - getattr(pet, "_last_minigame", -1e9) < LIMITS["minigame"]:
            self.blocked_reason = "cooldown"
        if self.blocked_reason:
            self.finished = True

    def update(self, dt):
        if self.finished:
            return
        self.time_left -= dt
        if self.flash > 0:
            self.flash -= dt
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self.spawn_t = random.uniform(0.7, 1.2)
            r = random.random()
            kind = "apple" if r < 0.55 else ("heart" if r < 0.82 else "sock")
            self.items.append({
                "x": random.randint(25, 215) ,
                "y": -12 ,
                "vy": random.randint(55, 85) ,
                "kind": kind,
            })
        pet_top, pet_bottom = 138 , 168
        for it in self.items[:]:
            it["y"] += it["vy"] * dt
            if (pet_top <= it["y"] <= pet_bottom
                    and abs(it["x"] - self.px) < 26):
                self.counts[it["kind"]] += 1
                self.flash = 0.25
                self.flash_bad = (it["kind"] == "sock")
                _snd = (getattr(self, "item_sounds", None) or {}).get(it["kind"])
                if _snd is not None:
                    try:
                        _snd.play()
                    except Exception:
                        pass
                self.items.remove(it)
            elif it["y"] > 200 :
                self.items.remove(it)
        if self.time_left <= 0:
            self.finish()

    def handle(self, btn):
        if btn == 0:
            self.px = max(24 , self.px - 26)
        elif btn == 1:
            self.finish()
        elif btn == 2:
            self.px = min(VW - 24 , self.px + 26)

    def finish(self):
        if self.finished:
            return
        self.finished = True
        p = self.pet
        p._last_minigame = p.age
        good = self.counts["apple"] + self.counts["heart"] * 2
        bad = self.counts["sock"]
        p.hunger = max(0.0, p.hunger - 5 * self.counts["apple"] - 3 * self.counts["heart"])
        p.happiness = min(100.0, p.happiness + 4 * good - 6 * bad)
        p.energy = max(0.0, p.energy - 10)
        p.play_count += 1
        p.state = STATE_PLAYING
        p.state_timer = 0.0
        p.calling = False

    def draw(self, game):
        game.draw_world()
        c = game.get_colors()
        game.draw_pixel_sprite(self.pet.get_sprite_key(), self.px, rh(160), rs(4))
        for it in self.items:
            game.draw_pixel_sprite(it["kind"], int(it["x"]), int(it["y"]), rs(3))
        if self.flash > 0:
            t = game.font_huge.render("X" if self.flash_bad else "!", True, c["text"])
            game.surface.blit(t, t.get_rect(center=(self.px, rh(118))))
        if not self.finished:
            t = game.font_big.render(f"{max(0, self.time_left):.0f}s", True, c["text"])
            game.surface.blit(t, rp(10, 248))
            t = game.font.render(
                f"A:{self.counts['apple']} H:{self.counts['heart']} S:{self.counts['sock']}",
                True, c["text"])
            game.surface.blit(t, rp(75, 252))
        else:
            r = rrect(40, 70, 160, 135)
            pygame.draw.rect(game.surface, c["box_bg"], r)
            pygame.draw.rect(game.surface, c["box_border"], r, rs(2))

            def center(txt, font, y):
                t = font.render(txt, True, c["text"])
                game.surface.blit(t, t.get_rect(center=(VW // 2, rh(y))))
            if getattr(self, "blocked_reason", None):
                center("ZZZ..." if self.blocked_reason == "sleep" else "WAIT!",
                       game.font_huge, 96)
                center("B: OK", game.font_big, 150)
                return
            center("SNACK TIME!", game.font_huge, 88)
            center(f"Apples x{self.counts['apple']}", game.font, 112)
            center(f"Hearts x{self.counts['heart']}", game.font, 128)
            center(f"Socks  x{self.counts['sock']}", game.font, 144)
            good = self.counts["apple"] + self.counts["heart"] * 2
            center(f"Happy +{max(0, 4 * good - 6 * self.counts['sock'])}",
                   game.font_big, 168)
            center("B: OK", game.font_big, 192)
