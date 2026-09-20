# defense.py
import random, math
import pygame
from config import LIMITS, STATE_PLAYING
from screen import VW, rs, rp, rrect, rw, rh, rwf, rhf
from spriterender import make_sprite_surface   # (Tippfehler vermeiden: spriterender!)

# ----Minigame "Defense" Tuning ----
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

ENEMY_TYPES = {
    "bug":   {"sprite": "enemy_bug",   "hp": 1, "speed": 1.15, "points": 10, "zigzag": True},
    "slime": {"sprite": "enemy_slime", "hp": 2, "speed": 0.70, "points": 20},
    "ghost": {"sprite": "enemy_ghost", "hp": 1, "speed": 1.00, "points": 15, "wobble": True},
    "cloud": {"sprite": "enemy_cloud", "hp": 2, "speed": 0.85, "points": 25},
    "skull": {"sprite": "enemy_skull", "hp": 1, "speed": 1.40, "points": 30},
}

class MiniGameDefense:

    PET = (120 , 240)
    DIRS = ("left", "mid", "right")

    def __init__(self, pet):
        self.pet = pet
        self.time_left = 30.0
        self.spawn_t = 0.8
        self.enemies = []
        self.shots = []
        self.fx = []
        self.score = 0
        self.combo = 0
        self.best_combo = 0
        self.kills = 0
        self.escaped = 0
        self.finished = False
        self.shoot_cd = SHOT_CD
        self.blocked_reason = None
        if getattr(pet, "sleeping", False):
            self.blocked_reason = "sleep"
        elif pet.age - getattr(pet, "_last_minigame", -1e9) < LIMITS["minigame"]:
            self.blocked_reason = "cooldown"
        if self.blocked_reason:
            self.finished = True
        self.shot_sound = None
        self.shot_sounds = []

    def _spawn(self):
        kind = random.choice(list(ENEMY_TYPES.keys()))
        cfg = ENEMY_TYPES[kind]
        from_left = random.random() < 0.5
        y = random.uniform(rhf(24), rhf(92))
        self.enemies.append({
            "kind": kind, "hp": cfg["hp"], "flash": 0.0,
            "x": rwf(-24) if from_left else (VW + rwf(24)),
            "y": y, "base_y": y,
            "dir": 1 if from_left else -1,
        })

    def _aim(self, direction):
        px, py = self.PET
        if direction == "left":
            tx, ty = rw(6), rh(6)
        elif direction == "right":
            tx, ty = VW - rw(6), rh(6)
        else:
            tx, ty = VW // 2, rh(6)
        dx, dy = tx - px, ty - py
        d = math.hypot(dx, dy) or 1.0
        return dx / d, dy / d

    def update(self, dt):
        if self.finished:
            return
        self.time_left -= dt
        self.shoot_cd = max(0.0, self.shoot_cd - dt)
        self.spawn_t -= dt
        if self.spawn_t <= 0 and self.time_left > SPAWN_STOP_LEAD:
            self.spawn_t = (random.uniform(SPAWN_MIN, SPAWN_MAX) - min(SPAWN_RAMP, (GAME_TIME - self.time_left) / SPAWN_RAMP_TIME))
            self._spawn()
        for e in self.enemies[:]:
            cfg = ENEMY_TYPES[e["kind"]]
            vx = (ENEMY_BASE_SPEED + ENEMY_BASE_SPEED * cfg["speed"]) * e["dir"]
            e["x"] += vx * dt
            if cfg.get("zigzag"):
                e["y"] = e["base_y"] + math.sin(e["x"] / ZIGZAG_DIV) * ZIGZAG_AMP
            elif cfg.get("wobble"):
                e["y"] = e["base_y"] + math.sin(e["x"] / WOBBLE_DIV) * WOBBLE_AMP
            e["flash"] = max(0.0, e["flash"] - dt)
            if e["x"] < -ENEMY_MARGIN or e["x"] > VW + ENEMY_MARGIN:
                self.enemies.remove(e)
                self.escaped += 1
                self.combo = 0
        for s in self.shots[:]:
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            if not (-30 < s["x"] < VW + 30
                    and s["y"] > -10):
                self.shots.remove(s)
                continue
            for e in self.enemies[:]:
                if (abs(s["x"] - e["x"]) < HITBOX_X
                        and abs(s["y"] - e["y"]) < HITBOX_Y):
                    e["hp"] -= 1
                    e["flash"] = HIT_FLASH
                    self.shots.remove(s)
                    if e["hp"] <= 0:
                        pts = ENEMY_TYPES[e["kind"]]["points"]
                        self.combo += 1
                        self.best_combo = max(self.best_combo, self.combo)
                        self.score += pts * self.combo
                        self.kills += 1
                        for _ in range(KILL_FX_COUNT):
                            self.fx.append({
                                "x": e["x"], "y": e["y"],
                                "vx": random.uniform(*FX_VX),
                                "vy": random.uniform(*FX_VY),
                                "age": FX_LIFETIME,
                            })
                        self.enemies.remove(e)
                    break
        for f in self.fx[:]:
            f["age"] -= dt
            f["x"] += f["vx"] * dt
            f["y"] += f["vy"] * dt
            if f["age"] <= 0:
                self.fx.remove(f)
        if self.time_left <= 0:
            self.finish()

    def handle(self, btn):
        if self.finished:
            return
        self.shoot(self.DIRS[btn])

    def shoot(self, direction):
        if self.shoot_cd > 0:
            return
        self.shoot_cd = 0.3
        dx, dy = self._aim(direction)
        px, py = self.PET
        speed = rwf(SHOT_SPEED)
        self.shots.append({
            "x": px, "y": py - rhf(10),
            "vx": dx * speed, "vy": dy * speed,
        })
        _snds = [s for s in (self.shot_sounds or []) if s is not None]
        if not _snds and getattr(self, "shot_sound", None) is not None:
            _snds = [self.shot_sound]
        if _snds:
            try:
                random.choice(_snds).play()
            except Exception:
                pass

    def finish(self):
        if self.finished:
            return
        self.finished = True
        p = self.pet
        p._last_minigame = p.age
        bonus = max(0, min(BONUS_MAX, self.score // BONUS_DIV - int(self.escaped * BONUS_ESCAPE_PEN)))
        p.happiness = min(100.0, p.happiness + bonus)
        p.energy = max(0.0, p.energy - 10)
        p.play_count += 1
        p.state = STATE_PLAYING
        p.state_timer = 0.0
        p.calling = False

    def draw(self, game):
        game.draw_world()
        c = game.get_colors()
        pygame.draw.line(game.surface, c["fg"], (0, rh(100)), (VW, rh(100)), rs(1))
        for s in self.shots:
            x, y = int(s["x"]), int(s["y"])
            x2 = int(s["x"] - s["vx"] * 0.05)
            y2 = int(s["y"] - s["vy"] * 0.05)
            pygame.draw.line(game.surface, c["fg"], (x, y), (x2, y2), rs(1))
            pygame.draw.rect(game.surface, c["fg"], (x, y, rs(2), rs(2)))
        game.draw_pixel_sprite(self.pet.get_sprite_key(),
                               self.PET[0], self.PET[1], rs(4))
        for e in self.enemies:
            sprite = ENEMY_TYPES[e["kind"]]["sprite"]
            color = c["bg"] if e["flash"] > 0 else c["fg"]
            surf = make_sprite_surface(sprite, rs(3), color)
            game.surface.blit(surf, surf.get_rect(
                center=(int(e["x"]), int(e["y"]))))
        for f in self.fx:
            pygame.draw.rect(game.surface, c["fg"],
                             (int(f["x"]), int(f["y"]), rs(1), rs(1)))
        if not self.finished:
            t = game.font_big.render(f"{max(0, self.time_left):.0f}s", True, c["text"])
            game.surface.blit(t, rp(10, 6))
            if self.combo > 1:
                t = game.font_big.render(f"x{self.combo}", True, c["text"])
                game.surface.blit(t, rp(112, 6))
            t = game.font_big.render(f"{self.score}", True, c["text"])
            game.surface.blit(t, rp(200, 6))
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
            center("DEFENSE!", game.font_huge, 88)
            center(f"Score {self.score}", game.font_big, 112)
            center(f"Best Combo x{self.best_combo}", game.font, 130)
            center(f"Escaped {self.escaped}", game.font, 146)
            bonus = max(0, min(30, self.score // 4 - int(self.escaped * 1.5)))
            center(f"Happy +{bonus}", game.font_big, 170)
            center("B: OK", game.font_big, 192)
