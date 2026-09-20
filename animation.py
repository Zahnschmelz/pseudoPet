#!/usr/bin/env python3
"""
fix.py – Patcht main.py mit der Evolutions-Animation.
Einfach ausführen: python fix.py
"""
import os
import sys

MAIN_FILE = "main.py"

# ============================================================
# NEUE METHODEN (werden nach _draw_roll eingefügt)
# ============================================================
NEW_METHODS = '''
    # ================= EVOLUTIONS-ANIMATION =================
    def _ease_out_back(self, x):
        x = max(0.0, min(1.0, x))
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * ((x - 1.0) ** 3) + c1 * ((x - 1.0) ** 2)

    def start_evolution_fx(self, old_key, new_key):
        particles = []
        for _ in range(26):
            particles.append({
                "ang": random.uniform(0.0, 2.0 * math.pi),
                "spd": random.uniform(rwf(30), rwf(95)),
                "size": random.choice((1, 2, 2, 3)),
            })
        self.evo_fx = {
            "t": 0.0,
            "dur": 3.4,
            "old_key": old_key,
            "new_key": new_key,
            "name": FORM_NAMES.get(self.pet.branch_key, "") if self.pet else "",
            "particles": particles,
        }
        self.evo_flash = 0.0
        snd = getattr(self, "evolution", None)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass
        print("[evo-fx] Animation gestartet: %s -> %s" % (old_key, new_key))

    def update_evolution_fx(self, dt):
        if self.evo_fx is None:
            return
        self.evo_fx["t"] += dt
        if self.evo_fx["t"] >= self.evo_fx["dur"]:
            self.evo_fx = None

    def draw_evolution_fx(self):
        fx = self.evo_fx
        if fx is None:
            return
        c = self.get_colors()
        t = fx["t"]
        cx = VW // 2
        old_key, new_key = fx["old_key"], fx["new_key"]
        cy = self._floor_center_y(new_key, 4)

        T_CHARGE = 1.0
        T_FLASH  = 1.45
        T_BURST  = 2.35

        if t < T_CHARGE:
            p = t / T_CHARGE
            lev = int(p * rh(18))
            amp = int(p * rw(5))
            shake = amp if int(t * 28) % 2 == 0 else -amp
            dim = pygame.Surface((VW, VH), pygame.SRCALPHA)
            dim.fill((0, 0, 0, int(110 * p)))
            self.surface.blit(dim, (0, 0))
            for ring in range(3):
                rp = (t * 1.5 + ring / 3.0) % 1.0
                radius = int((1.0 - rp) * rs(52)) + rs(4)
                if radius > rs(3):
                    pygame.draw.circle(self.surface, c["fg"],
                                       (cx, cy - lev), radius, rs(1))
            if p > 0.6 and int(t * 16) % 2 == 0:
                surf = make_sprite_surface(old_key, rs(4), WHITE)
                self.surface.blit(surf, surf.get_rect(center=(cx + shake, cy - lev)))
            else:
                self.draw_pixel_sprite(old_key, cx + shake, cy - lev, scale=rs(4))
            for i in range(10):
                ang = i * (2 * math.pi / 10) + t * 5.0
                rad = (1.0 - p) * rs(64) + rs(6)
                px = int(cx + math.cos(ang) * rad)
                py = int(cy - lev + math.sin(ang) * rad * 0.7)
                pygame.draw.rect(self.surface, c["fg"], (px, py, rs(2), rs(2)))

        elif t < T_FLASH:
            fp = (t - T_CHARGE) / (T_FLASH - T_CHARGE)
            flash_a = int(255 * math.sin(fp * math.pi))
            fl = pygame.Surface((VW, VH), pygame.SRCALPHA)
            fl.fill((255, 255, 255, flash_a))
            self.surface.blit(fl, (0, 0))

        elif t < T_BURST:
            bp = (t - T_FLASH) / (T_BURST - T_FLASH)
            bt = t - T_FLASH
            pop = self._ease_out_back(bp)
            cur_scale = max(rs(1), int(rs(4) * pop))
            bounce = -int(math.sin(min(1.0, bp) * math.pi) * rh(12))
            self.draw_pixel_sprite(new_key, cx, cy + bounce, scale=cur_scale)
            for pt in fx["particles"]:
                px = int(cx + math.cos(pt["ang"]) * pt["spd"] * bt)
                py = int(cy + math.sin(pt["ang"]) * pt["spd"] * bt * 0.8)
                if 0 <= px < VW and 0 <= py < VH:
                    sz = rs(pt["size"])
                    pygame.draw.rect(self.surface, c["fg"], (px, py, sz, sz))
            for i in range(6):
                ang = i * (math.pi / 3) + bt * 3.0
                rad = rs(28) + bt * rs(42)
                px = int(cx + math.cos(ang) * rad)
                py = int(cy + math.sin(ang) * rad * 0.7)
                self.draw_pixel_sprite("spark", px, py, scale=rs(1))
            if bp < 0.35:
                fa = int(230 * (1.0 - bp / 0.35))
                fl = pygame.Surface((VW, VH), pygame.SRCALPHA)
                fl.fill((255, 255, 255, fa))
                self.surface.blit(fl, (0, 0))

        else:
            bounce = abs(math.sin(t * 6.0)) * rh(4)
            self.draw_pixel_sprite(new_key, cx, cy, scale=rs(4), bounce=-int(bounce))
            for i in range(14):
                sx = (i * 37 + int(t * 46)) % VW
                sy = int((t * 70 + i * 53) % VH)
                pygame.draw.rect(self.surface, c["fg"], (sx, sy, rs(1), rs(1)))
            if int(t * 4) % 2 == 0:
                txt = self.font_huge.render("EVOLVED!", True, c["text"])
                self.surface.blit(txt, txt.get_rect(center=(cx, rh(56))))
            if fx["name"]:
                nt = self.font_big.render(fx["name"], True, c["text"])
                self.surface.blit(nt, nt.get_rect(center=(cx, rh(84))))
    # ================= EVOLUTIONS-ANIMATION ENDE =================

'''

def patch():
    if not os.path.exists(MAIN_FILE):
        print(f"[FEHLER] {MAIN_FILE} nicht gefunden!")
        sys.exit(1)

    with open(MAIN_FILE, "r", encoding="utf-8") as f:
        src = f.read()

    changes = 0

    # --- 1) __init__: evo_fx + _last_sprite_key hinzufügen ---
    old_init = "self.evo_flash = 0.0\n        self._last_branch = None\n        self.choice_options = []"
    new_init = "self.evo_flash = 0.0\n        self._last_branch = None\n        self.evo_fx = None\n        self._last_sprite_key = None\n        self.choice_options = []"
    if "self.evo_fx = None" not in src:
        if old_init in src:
            src = src.replace(old_init, new_init, 1)
            changes += 1
            print("[OK] __init__: evo_fx + _last_sprite_key hinzugefügt")
        else:
            print("[WARN] __init__-Stelle nicht gefunden (evtl. anderer Zeilenumbruch)")
    else:
        print("[SKIP] __init__ bereits gepatcht")

    # --- 2) Neue Methoden nach _draw_roll einfügen ---
    anchor = "    def draw_buttons(self):"
    if "def start_evolution_fx" not in src:
        if anchor in src:
            src = src.replace(anchor, NEW_METHODS + anchor, 1)
            changes += 1
            print("[OK] Neue Evolutions-Methoden eingefügt")
        else:
            print("[WARN] draw_buttons-Anker nicht gefunden!")
    else:
        print("[SKIP] Methoden bereits vorhanden")

    # --- 3) draw_pet: Früh-Return für evo_fx ---
    old_drawpet = """    def draw_pet(self):
        if not self.pet:
            return
        cx = VW // 2"""
    new_drawpet = """    def draw_pet(self):
        if not self.pet:
            return
        if self.evo_fx is not None:
            self.draw_evolution_fx()
            return
        cx = VW // 2"""
    if "self.draw_evolution_fx()" not in src:
        if old_drawpet in src:
            src = src.replace(old_drawpet, new_drawpet, 1)
            changes += 1
            print("[OK] draw_pet: Evolutions-Check eingefügt")
        else:
            print("[WARN] draw_pet-Stelle nicht gefunden")
    else:
        print("[SKIP] draw_pet bereits gepatcht")

    # --- 4) update_evolution_fx(dt) im Loop aufrufen ---
    old_update = "self.update_butterfly(dt)"
    new_update = "self.update_butterfly(dt)\n        self.update_evolution_fx(dt)"
    if "update_evolution_fx(dt)" not in src:
        if old_update in src:
            src = src.replace(old_update, new_update, 1)
            changes += 1
            print("[OK] update_evolution_fx(dt) im Loop ergänzt")
        else:
            print("[WARN] update_butterfly-Stelle nicht gefunden")
    else:
        print("[SKIP] update_evolution_fx bereits im Loop")

    # --- 5) _sig-Erkennung im Loop ersetzen ---
    old_sig = """        if self.pet:
            _sig = (self.pet.branch_key, self.pet.stage)
            if _sig != self._last_branch:
                self._last_branch = _sig
                self.evo_flash = 1.2"""
    new_sig = """        if self.pet:
            _sig = (self.pet.branch_key, self.pet.stage)
            if _sig != self._last_branch:
                self._last_branch = _sig
            cur_sprite = self.pet.get_sprite_key()
            if (self._last_sprite_key is not None
                    and cur_sprite != self._last_sprite_key
                    and self.pet.state != STATE_HATCHING
                    and self.pet.stage != STAGE_EGG
                    and not str(self._last_sprite_key).startswith("egg")
                    and self.mode == "game"):
                self.start_evolution_fx(self._last_sprite_key, cur_sprite)
            self._last_sprite_key = cur_sprite"""
    if "start_evolution_fx(self._last_sprite_key" not in src:
        if old_sig in src:
            src = src.replace(old_sig, new_sig, 1)
            changes += 1
            print("[OK] _sig-Erkennung durch Sprite-Detection ersetzt")
        else:
            print("[WARN] _sig-Block nicht gefunden")
    else:
        print("[SKIP] _sig-Erkennung bereits gepatcht")

    # --- 6) reset_game: Cleanup ---
    old_reset = "self.evo_flash = 0.0\n        self._last_branch = None\n        self.butterfly = None"
    new_reset = "self.evo_flash = 0.0\n        self._last_branch = None\n        self.evo_fx = None\n        self._last_sprite_key = None\n        self.butterfly = None"
    if "self.evo_fx = None\n        self._last_sprite_key = None\n        self.butterfly" not in src:
        if old_reset in src:
            src = src.replace(old_reset, new_reset, 1)
            changes += 1
            print("[OK] reset_game: Cleanup ergänzt")
        else:
            print("[WARN] reset_game-Stelle nicht gefunden")
    else:
        print("[SKIP] reset_game bereits gepatcht")

    # --- Schreiben ---
    if changes > 0:
        backup = MAIN_FILE + ".bak"
        with open(backup, "w", encoding="utf-8") as f:
            f.write(src)
        # Backup ist die ORIGINAL-Datei
        import shutil
        shutil.copy2(MAIN_FILE, backup)
        with open(MAIN_FILE, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"\n✅ {changes} Änderung(en) in {MAIN_FILE} geschrieben.")
        print(f"   Backup: {backup}")
    else:
        print("\nℹ️  Keine Änderungen nötig – alles bereits gepatcht.")

if __name__ == "__main__":
    patch()
