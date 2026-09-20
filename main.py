# stdlibs
import pygame
import random
import math
import sys
import json
import os
import time
from os import environ
from sys import platform as _sys_platform

# pseudolibs
from config import *
from screen import *
from spriterender import make_sprite_surface, validate_sprites
from pixelfont import PixelFont, draw_text, text_w
from simple_clock import PixelClock
from snack import MiniGameSnack
from defense import MiniGameDefense
from pong import MiniGamePong, HAS_WEBSOCKETS
from fishing import MiniGameFish
from sprites import SPRITES



def platform():
    if 'ANDROID_ARGUMENT' in environ:
        return "android"
    elif _sys_platform in ('linux', 'linux2', 'linux3'):
        return "linux"
    elif _sys_platform in ('win32', 'cygwin'):
        return 'win'
    return 'other'

__DEFAULT__ = 1
_FULLSCREEN_START = True
_ai = 1
DEBUG_SPEED = __DEFAULT__
FULLSCREEN = True
FORCE_DAYLIGHT = None
WINDOW = False

while _ai < len(sys.argv):
    _av = sys.argv[_ai]
    if _av == "--debug" and _ai + 1 < len(sys.argv) and sys.argv[_ai + 1].isdigit():
        DEBUG_SPEED = max(1, int(sys.argv[_ai + 1]))
        _ai += 2
        continue
    if _av.startswith("--debug=") and _av.split("=", 1)[1].isdigit():
        DEBUG_SPEED = max(1, int(_av.split("=", 1)[1]))
    if _av == "--release":
        DEBUG_SPEED = 1
    if _av == "--windowed":
        _FULLSCREEN_START = False
        FULLSCREEN = False
        WINDOW = True
    if _av == "--window":
        _FULLSCREEN_START = False
        FULLSCREEN = False
        WINDOW = True
    if _av == "--fullscreen":
        _FULLSCREEN_START = True
        FULLSCREEN = True
    if _av == "--day":
        FORCE_DAYLIGHT = "day"
    if _av == "--night":
        FORCE_DAYLIGHT = "night"
    _ai += 1

print("[start] Tempo x%d | %s%s" % (DEBUG_SPEED,
      "VOLLBILD" if _FULLSCREEN_START else "Fenster",
      (" | " + FORCE_DAYLIGHT.upper()) if FORCE_DAYLIGHT else ""))

pygame.init()

try:
    pygame.mixer.init()
except Exception:
    print("[mixer] init fehlgeschlagen - Sound deaktiviert")

if pygame.mixer.get_init() is None:
    class _DummyChannel:
        def play(self, *a, **k): pass
        def stop(self, *a, **k): pass
    _DCH = _DummyChannel()
    pygame.mixer.Channel = lambda *a, **k: _DCH

if platform() == "android":
    path = "/data/data/org.beezi.pseudopet/files/app/"
else:
    path = "./"

def detect_system_language():
    if platform() == "android":
        try:
            from jnius import autoclass          # ← nur hier, nur auf Android
            Locale = autoclass("java.util.Locale")
            lang = Locale.getDefault().getLanguage()
            if lang:
                return lang.lower()
        except Exception as e:
            print("[lang] Locale-Fehler:", e)
    try:
        import locale                            # ← stdlib, kein Zusatzpaket
        tag = locale.getlocale()[0] or ""
        if tag:
            return tag[:2].lower()
    except Exception:
        pass
    return LANG_FALLBACK

LANG = detect_system_language()
print("[lang] System-Sprache: %s -> %s" % (LANG, "DE" if LANG == "de" else "EN"))
if LANG != "de":
    MESSAGES = MESSAGES_EN
    NOTIFICATIONTITEL = NOTIFICATIONTITEL_EN
    NOTIF_HEADLINE = NOTIF_HEADLINE_EN

SAVE_FILE = path + "pseudopet_save.json"
AUTOSAVE_INTERVAL = 10.0
HATCH_TIME = max(3, int(180 / DEBUG_SPEED))
BABY_TIME = max(3, int(3600 / DEBUG_SPEED))
CHILD_TIME = max(3, int(10800 / DEBUG_SPEED))
TEEN_TIME = max(3, int(28800 / DEBUG_SPEED))
HATCH_ANIM_SPEED = 4 if DEBUG_SPEED > 1 else 1

HOLD_KEYS = {
    0: (pygame.K_a, pygame.K_LEFT),
    2: (pygame.K_d, pygame.K_RIGHT),
}

_NOTIF_SEQ = [0]

FPS = 20
DW, DH = 240, 320
VW, VH = DW, DH
SCALE = 1
info = pygame.display.Info()

if WINDOW == True:
    SCALE = 2
else:
    SCALE = max(1, min(info.current_w // VW, info.current_h // VH))

WIN_W, WIN_H = VW * SCALE, VH * SCALE

def rw(x):
    return int(round(x * VW / DW))
def rh(y):
    return int(round(y * VH / DH))
def rs(n):
    return max(1, int(round(n * VH / DH)))
def rp(x, y):
    return (rw(x), rh(y))
def rrect(x, y, w, h):
    return pygame.Rect(rw(x), rh(y), rw(w), rh(h))
def rwf(x):
    return x * VW / DW
def rhf(y):
    return y * VH / DH
def on_resolution_selected(self, w, h):
    self.apply_resolution(w, h)

validate_sprites()

def android_notify(title, message, channel_id="pseudopet_default"):
    from jnius import autoclass
    Context = autoclass('android.content.Context')
    NotificationManager = autoclass('android.app.NotificationManager')
    Channel = autoclass('android.app.NotificationChannel')
    Builder = autoclass('android.app.Notification$Builder')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    context = PythonActivity.mActivity.getApplicationContext()
    mgr = context.getSystemService(Context.NOTIFICATION_SERVICE)
    if mgr.getNotificationChannel(channel_id) is None:          # nur 1x anlegen
        mgr.createNotificationChannel(Channel(
            channel_id, "PseudoPet", NotificationManager.IMPORTANCE_HIGH))
    b = Builder(context, channel_id)
    b.setContentTitle(title)
    b.setContentText(message)
    b.setSmallIcon(context.getApplicationInfo().icon)
    b.setAutoCancel(True)
    _NOTIF_SEQ[0] += 1
    mgr.notify(_NOTIF_SEQ[0], b.build())                        # eindeutige ID

class Pet:
    def __init__(self, name, egg_type):
        self.name = name
        self.egg_type = egg_type
        self.branch = EVOLUTION_BRANCHES.get(egg_type, EVOLUTION_BRANCHES["dot"])
        self.branch_key = None
        self.stage = STAGE_EGG
        self.age = 0.0
        self.death_age = 0.0
        self.state = STATE_IDLE
        self.hunger = random.randint(0,20)
        self.happiness = random.randint(60,100)
        self.energy = random.randint(70,100)
        self.health = random.randint(95,100)
        self.discipline = random.randint(1,39)
        self.weight = random.randint(5,35)
        self.sleeping = False
        self.sick = False
        self.poops = 0
        self.light_on = True
        self.calling = False
        self.poop_played = False
        self.poop_sound = None
        self.premium_unlocked = False
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.state_timer = 0.0
        self.stage_timer = 0.0
        self.poop_timer = 0.0
        self.call_timer = 0.0
        self.hatch_phase = 0
        self.hatch_roll_x = 0
        self.hatch_time = HATCH_TIME
        self.baby_time = BABY_TIME
        self.child_time = CHILD_TIME
        self.teen_time = TEEN_TIME
        self.premium_score = 0.0
        self.premium_timer = 0.0
        self.dark_time = 0.0
        self.is_dark = False
        self.stage_dark_time = 0.0
        self.branch_group = None
        self.pending_baby_choice = False
        self.chosen = {}
        self.choice_pending = None
        self.feed_count = 0
        self.play_count = 0
        self.clean_count = 0
        self.sick_count = 0
        self._offline = False
        self.just_hatched = False
        self._sim_clock = 0.0
        self.weather_sick_timer = 0.0
        self.wake_check_t = 0.0
        self.just_woke = False

    def get_sprite_key(self):
        if self.state == STATE_HATCHING or self.stage == STAGE_EGG:
            return f"egg_{self.egg_type}"
        if self.stage == STAGE_PREMIUM:
            b = self.chosen.get(STAGE_ADULT) or self.egg_type
            d = EVOLUTION_BRANCHES.get(b) or EVOLUTION_BRANCHES["dot"]
            return d.get(STAGE_PREMIUM, d[STAGE_ADULT])
        b = self.chosen.get(self.stage) or self.egg_type
        d = EVOLUTION_BRANCHES.get(b) or EVOLUTION_BRANCHES["dot"]
        return d.get(self.stage, d[STAGE_BABY])

    def tick_anim(self, dt):
        self.anim_timer += dt
        if self.anim_timer > 0.4:
            self.anim_frame = (self.anim_frame + 1) % 4
            self.anim_timer = 0.0

    def _advance_stage(self, nxt, key):
        self.chosen[nxt] = key
        self.branch_key = key
        self.branch = EVOLUTION_BRANCHES.get(key) or EVOLUTION_BRANCHES["dot"]
        if key == "dark":
            self.is_dark = True
            self.branch_group = None
        if nxt == STAGE_ADULT:
            if key == "dark":
                self.stage = STAGE_ADULT
            else:
                self.check_premium()
                self.stage = (STAGE_PREMIUM if self.premium_unlocked
                              else STAGE_ADULT)
        else:
            self.stage = nxt
        self.stage_timer = 0.0
        self.stage_dark_time = 0.0
        self.choice_pending = None
        print(f"[evo] {self.name} -> {FORM_NAMES.get(key, key)} ({nxt})")

    def _dark_pct(self):
        if self.stage_timer <= 0.0:
            return 0.0
        return self.stage_dark_time / self.stage_timer

    def _become_dark_premium(self):
        self.is_dark = True
        self.chosen[STAGE_ADULT] = "dark"
        self.branch_key = "dark"
        self.branch = EVOLUTION_BRANCHES["dark"]
        self.branch_group = None
        self.premium_unlocked = True
        self.stage = STAGE_PREMIUM
        self.premium_timer = 0.0
        self.stage_timer = 0.0
        self.stage_dark_time = 0.0
        self.choice_pending = None
        print("[evo] DARK-Premium erreicht!")

    def simulate_offline(self, seconds):
        seconds = min(max(seconds, 0.0), OFFLINE_MAX)
        was = {"poops": self.poops, "sick": self.sick, "stage": self.stage}
        self._offline = True
        self._sim_clock = time.time() - seconds
        self.calling = False
        self.poop_played = False
        _w = getattr(self, "_world", None)          # ← FEHLTE!
        remaining = seconds
        while remaining > 0 and self.state not in (STATE_DEAD, STATE_GHOST):
            step = min(OFFLINE_CHUNK, remaining)
            self.update(step)
            self._sim_clock += step
            remaining -= step
            if _w is not None:
                _w.weather_timer += step          # nur Wetter-Logik
                if _w.weather_timer > 180:
                    _w.weather_timer = 0.0
                    r = random.random()
                    _w.weather = ("sun" if r < 0.45 else "cloud"
                                if r < 0.70 else "rain" if r < 0.90 else "snow")
        self._offline = False
        print(f"[offline-sim] dark: {self.dark_time / 60:.0f} min total, "
            f"diese Stage: {self.stage_dark_time / 60:.0f} min")
        return {
            "hours": round(seconds / 3600, 1),
            "secs": seconds,
            "new_poops": self.poops - was["poops"],
            "sick": self.sick,
            "became_sick": self.sick and not was["sick"],
            "stage": self.stage,
            "stage_up": self.stage != was["stage"] or self.choice_pending is not None,
            "hunger": int(self.hunger),
        }

    def update(self, dt):
        if self.state == STATE_DEAD:
            return
        if self.choice_pending:
            return

        self.age += dt
        self.state_timer += dt
        self.tick_anim(dt)

        dark_now = False
        if getattr(self, "outdoor", False):
            _w = getattr(self, "_world", None)
            if _w is not None:
                _at = self._sim_clock if getattr(self, "_offline", False) else None
                if _w.daylight(_at) == "night":
                    dark_now = True
        elif not self.sleeping and not self.light_on:
            dark_now = True
        if dark_now:
            self.dark_time += dt
            self.stage_dark_time += dt
        if self.state == STATE_GHOST:
            if self.state_timer > GHOST_TIME:
                self.state = STATE_DEAD
            return

        mercy = OFFLINE_MERCY if self._offline else 1.0

        stab = 1.0 - STAGE_STABILITY.get(self.stage, 0.0)
        if not self.sleeping:
            self.hunger = min(100.0, self.hunger + HUNGER_DECAY_WAKE * stab * mercy * dt)
            self.happiness = max(0.0, self.happiness - HAPPINESS_DECAY * mercy * dt)
            self.energy = max(0.0, self.energy - ENERGY_DECAY_WAKE * mercy * dt)
            self.discipline = max(0.0, self.discipline - DISCIPLINE_DECAY * mercy * dt)
        else:
            self.energy = min(100.0, self.energy + ENERGY_REGEN_SLEEP * dt)
            self.hunger = min(100.0, self.hunger + HUNGER_DECAY_SLEEP * stab * mercy * dt)
            # --- automatisch aufwachen bei voller Energie (live & offline identisch) ---
            if self.energy >= 99.5:
                self.wake_check_t += dt
                if self.wake_check_t >= 60.0:
                    self.wake_check_t = 0.0
                    if random.random() < 0.30:
                        self.sleeping = False
                        self.light_on = True
                        self.calling = False
                        self.wake_check_t = 0.0
                        self.just_woke = True
            else:
                self.wake_check_t = 0.0

        if not self.sick and self.hunger < HEAL_HUNGER_MAX and self.energy > HEAL_ENERGY_MIN:
            if not self.sleeping:
                heal = HEAL_RATE_WAKE_HAPPY if self.happiness > HEAL_HAPPY_MIN else HEAL_RATE_WAKE
            else:
                heal = HEAL_RATE_SLEEP_HAPPY if self.happiness > HEAL_HAPPY_MIN else HEAL_RATE_SLEEP
            self.health = min(100.0, self.health + heal * dt)

        if self.hunger > STARVE_HUNGER or self.energy < EXHAUST_ENERGY:
            self.health = max(0.0, self.health - HEALTH_DECAY_CRITICAL * stab * mercy * dt)

        if self.poops > 0:
            self.health = max(0.0, self.health - POOP_HEALTH_DECAY * stab * mercy * min(self.poops, POOP_HEALTH_CAP) * dt)
            self.happiness = max(0.0, self.happiness - POOP_HAPPINESS_DECAY * mercy * self.poops * dt)

        if self.energy < SICK_ENERGY and random.random() < SICK_CHANCE * dt and not self.sleeping:
            if not self.sick:
                self.sick_count += 1
            self.sick = True
        # --- Outdoor-Wetter-Krankheit: Regen & Schnee (Intervall-Wurf) ---
        _w = getattr(self, "_world", None)
        _wc = None
        if (not self.sick
                and getattr(self, "outdoor", False)
                and self.state not in (STATE_DEAD, STATE_GHOST, STATE_HATCHING)
                and self.stage != STAGE_EGG):
            if _w is not None and _w.weather == "rain":
                _wc = (OUTDOOR_SICK_INTERVAL, OUTDOOR_SICK_CHANCE)
            elif _w is not None and _w.weather == "snow":
                _wc = (SNOW_SICK_INTERVAL, SNOW_SICK_CHANCE)
        if _wc is not None:
            self.weather_sick_timer += dt
            if self.weather_sick_timer >= _wc[0]:
                self.weather_sick_timer = 0.0
                if random.random() < _wc[1]:
                    self.sick = True
                    self.sick_count += 1
                    self.calling = True
        else:
            self.weather_sick_timer = 0.0

        if self.sick:
            self.health = max(0.0, self.health - SICK_HEALTH_DECAY * stab * mercy * dt)
            self.happiness = max(0.0, self.happiness - SICK_HAPPINESS_DECAY * mercy * dt)

        if self.health <= 0:
            if self._offline:
                self.health = OFFLINE_HEALTH_FLOOR
                if not self.sick:
                    self.sick_count += 1
                self.sick = True
            else:
                self.die()
                return

        self.poop_timer += dt * mercy
        if (self.poop_timer > POOP_TIMER_GATE and self.stage != STAGE_EGG
                and not self.sleeping and self.state != STATE_HATCHING):
            if random.random() < POOP_CHANCE * stab * dt:
                self.poops = min(POOP_MAX, self.poops + 1)
                self.poop_timer = 0.0
                if not self._offline:
                    snd = getattr(self, "poop_sound", None)
                    if snd is None:
                        snd = globals().get("_POOP_SOUND_HOOK")
                    if snd is not None:
                        try:
                            snd.play()
                        except Exception:
                            pass

        if not self.sleeping and self.stage != STAGE_EGG and self.state != STATE_HATCHING:
            needs = (self.hunger > CALL_HUNGER or self.happiness < CALL_HAPPINESS
                     or self.energy < CALL_ENERGY or self.sick or self.poops > 0)
            if needs:
                self.call_timer += dt
                if self.call_timer > CALL_DELAY:
                    self.calling = True
            else:
                self.calling = False
                self.poop_played = False
                self.call_timer = 0.0

        # --- Gewicht / Metabolismus ---
        if not self.sleeping:
            # wach: langsamer Grundumsatz
            self.weight = max(5.0, self.weight - 0.012 * stab * mercy * dt)
        else:
            # schlaf: minimaler Verbrauch
            self.weight = max(5.0, self.weight - 0.004 * stab * mercy * dt)

        self.stage_timer += dt


        if self.stage == STAGE_EGG and self.stage_timer > self.hatch_time:
            egg_dark = self._dark_pct()
            self.stage = STAGE_BABY
            self.state = STATE_HATCHING
            self.state_timer = 0.0
            self.stage_timer = 0.0
            self.stage_dark_time = 0.0
            self.hatch_phase = 0
            if egg_dark > DARK_THRESHOLD:
                self.is_dark = True
                self.branch_group = None
                self.pending_baby_choice = False
                self.chosen[STAGE_BABY] = "dark"
                self.branch_key = "dark"
                self.branch = EVOLUTION_BRANCHES["dark"]
                print("[hatch] DARK-Baby! (Ei-Phase %d%% Licht-aus)"
                      % int(egg_dark * 100))
            else:
                groups = EGG_GROUPS.get(self.egg_type, EGG_GROUPS["dot"])
                self.branch_group = list(random.choice(groups))
                self.pending_baby_choice = True
                print("[hatch] Gruppe: %s" % "/".join(self.branch_group))

        elif self.state == STATE_HATCHING:
            if HATCH_ANIM_SPEED > 1:
                self.state_timer += dt * (HATCH_ANIM_SPEED - 1)
            self.update_hatch(dt)

        elif self.stage == STAGE_BABY and self.stage_timer > self.baby_time:
            if self.is_dark or self._dark_pct() > DARK_THRESHOLD:
                self._advance_stage(STAGE_CHILD, "dark")
            else:
                self.choice_pending = {"next": STAGE_CHILD}

        elif self.stage == STAGE_CHILD and self.stage_timer > self.child_time:
            if self.is_dark or self._dark_pct() > DARK_THRESHOLD:
                self._advance_stage(STAGE_TEEN, "dark")
            else:
                self.choice_pending = {"next": STAGE_TEEN}

        elif self.stage == STAGE_TEEN and self.stage_timer > self.teen_time:
            if self.is_dark or self._dark_pct() > DARK_THRESHOLD:
                self._advance_stage(STAGE_ADULT, "dark")
            else:
                self.choice_pending = {"next": STAGE_ADULT}

        elif self.stage == STAGE_ADULT and not self.premium_unlocked:
            if (self._dark_pct() > DARK_THRESHOLD
                    and self.stage_timer >= DARK_ADULT_MIN):
                self._become_dark_premium()
            elif not self.is_dark:
                stats = [100 - self.hunger, self.happiness, self.energy,
                         self.health, self.discipline]
                if all(s > 80 for s in stats):
                    self.premium_timer += dt
                    if self.premium_timer >= 60.0:
                        self.premium_unlocked = True
                        self.stage = STAGE_PREMIUM
                        self.premium_timer = 0.0
                        self.stage_timer = 0.0
                        self.stage_dark_time = 0.0
                else:
                    self.premium_timer = max(0.0, self.premium_timer - dt * 1.5)

        if self.state == STATE_EATING and self.state_timer > 6.0:
            self.state = STATE_IDLE
        elif self.state == STATE_PLAYING and self.state_timer > 7.0:
            self.state = STATE_IDLE

    def update_hatch(self, dt):
        t = self.state_timer
        if t < 8.0:
            self.hatch_phase = 0
        elif t < 14.0:
            self.hatch_phase = 1
        elif t < 20.0:
            self.hatch_phase = 2
            self.hatch_roll_x = math.sin(t * 2) * 15
        elif t < 26.0:
            self.hatch_phase = 3
        elif t < 30.0:
            self.hatch_phase = 4
        else:
            self.state = STATE_IDLE
            self.hatch_phase = 5
            self.just_hatched = True
            self.stage_timer = 0.0
            self.stage_dark_time = 0.0
            if self.pending_baby_choice:
                self.pending_baby_choice = False
                self.choice_pending = {"next": STAGE_BABY}

    def check_premium(self):
        stats = [100 - self.hunger, self.happiness, self.energy,
                 self.health, self.discipline]
        avg = sum(stats) / len(stats)
        self.premium_score = avg
        if avg >= 78:
            self.premium_unlocked = True

    def to_dict(self):
        return {
            "name": self.name, "egg_type": self.egg_type,
            "stage": self.stage, "age": self.age, "death_age": self.death_age,
            "state": self.state,
            "hunger": self.hunger, "happiness": self.happiness,
            "energy": self.energy, "health": self.health,
            "discipline": self.discipline, "weight": self.weight,
            "sleeping": self.sleeping, "sick": self.sick, "poops": self.poops,
            "light_on": self.light_on, "premium_unlocked": self.premium_unlocked,
            "stage_timer": self.stage_timer, "premium_timer": self.premium_timer,
            "hatch_phase": self.hatch_phase,
            "dark_time": self.dark_time, "is_dark": self.is_dark,
            "stage_dark_time": self.stage_dark_time,
            "branch_group": self.branch_group,
            "choice_pending": self.choice_pending,
            "chosen": self.chosen, "branch_key": self.branch_key,
            "feed_count": self.feed_count, "play_count": self.play_count,
            "clean_count": self.clean_count, "sick_count": self.sick_count,
        }

    @classmethod
    def from_dict(cls, data):
        pet = cls(data["name"], data["egg_type"])
        pet.stage = data["stage"]
        pet.age = data["age"]
        pet.death_age = data.get("death_age", 0.0)
        pet.state = data["state"]
        pet.hunger = data["hunger"]
        pet.happiness = data["happiness"]
        pet.energy = data["energy"]
        pet.health = data["health"]
        pet.discipline = data["discipline"]
        pet.weight = data["weight"]
        pet.sleeping = data["sleeping"]
        pet.sick = data["sick"]
        pet.poops = data["poops"]
        pet.light_on = data["light_on"]
        pet.premium_unlocked = data["premium_unlocked"]
        pet.stage_timer = data["stage_timer"]
        pet.premium_timer = data.get("premium_timer", 0.0)
        pet.hatch_phase = data.get("hatch_phase", 0)
        pet.dark_time = data.get("dark_time", 0.0)
        pet.is_dark = data.get("is_dark", False)
        pet.stage_dark_time = data.get("stage_dark_time", 0.0)
        pet.chosen = dict(data.get("chosen", {}))
        pet.branch_key = data.get("branch_key")
        pet.feed_count = data.get("feed_count", 0)
        pet.play_count = data.get("play_count", 0)
        pet.clean_count = data.get("clean_count", 0)
        pet.sick_count = data.get("sick_count", 0)
        pet.choice_pending = data.get("choice_pending")
        bg = data.get("branch_group")
        if bg:
            pet.branch_group = list(bg)
        elif pet.chosen.get(STAGE_BABY):
            for grp in EGG_GROUPS.get(pet.egg_type, ()):
                if pet.chosen[STAGE_BABY] in grp:
                    pet.branch_group = list(grp)
                    break

        bk = pet.branch_key
        if bk and not pet.chosen:
            st = pet.stage
            if st == STAGE_PREMIUM:
                pet.chosen[STAGE_ADULT] = bk
            elif st in (STAGE_CHILD, STAGE_TEEN, STAGE_ADULT):
                pet.chosen[st] = bk
        if pet.is_dark:
            st = pet.stage
            pet.chosen[STAGE_ADULT if st == STAGE_PREMIUM else st] = "dark"
            pet.branch_key = "dark"
            pet.branch = EVOLUTION_BRANCHES["dark"]
            pet.branch_group = None
            pet.choice_pending = None
        elif (pet.stage == STAGE_BABY
                and not pet.chosen.get(STAGE_BABY)
                and pet.choice_pending is None
                and pet.branch_group):
            pet.choice_pending = {"next": STAGE_BABY}
        if pet.state == STATE_HATCHING:
            pet.state = STATE_IDLE
        return pet

    def die(self):
        self.state = STATE_GHOST
        self.state_timer = 0.0
        self.death_age = self.age
        self.sleeping = False
        self.sick = False
        self.calling = False
        self.poops = 0

    def feed(self):
        if self.state in (STATE_DEAD, STATE_GHOST) or self.sleeping:
            return False
        if self.hunger < OVERFEED_THRESHOLD:
            self.weight += 5
            stab = 1.0 - STAGE_STABILITY.get(self.stage, 0.0)
            if self.hunger < OVERFEED_SICK_THRESHOLD:
                if random.random() < OVERFEED_SICK_CHANCE * stab:
                    self.sick = True
                    self.sick_count += 1
        self.hunger = max(0.0, self.hunger - 30)
        self.weight = min(80.0, self.weight + 3.0)    # ← Cap von 50 auf 80
        self.state = STATE_EATING
        self.state_timer = 0.0
        self.calling = False
        self.feed_count += 1
        return True

    def play(self):
        if self.state in (STATE_DEAD, STATE_GHOST) or self.sleeping:
            return False
        self.happiness = min(100.0, self.happiness + 25)
        self.energy = max(0.0, self.energy - 18)
        self.hunger = min(100.0, self.hunger + 12)
        self.weight = max(5.0, self.weight - 2.5)     # ← war 1.0, jetzt 2.5
        self.state = STATE_PLAYING
        self.state_timer = 0.0
        self.calling = False
        self.play_count += 1
        return True

    def toggle_sleep(self):
        if self.state in (STATE_DEAD, STATE_GHOST):
            return
        w = getattr(self, "_world", None)
        if w is not None:
            outdoor = (w.room == "outdoor")
        else:
            outdoor = getattr(self, "outdoor", False)
        if outdoor:
            return
        self.sleeping = not self.sleeping
        self.light_on = not self.sleeping
        self.calling = False

    def give_medicine(self):
        if self.state in (STATE_DEAD, STATE_GHOST):
            return False
        self.sick = False
        self.health = min(100.0, self.health + 5)
        self.state = STATE_IDLE
        self.calling = False
        return True

    def clean(self):
        if self.state in (STATE_DEAD, STATE_GHOST):
            return
        if self.poops > 0:
            self.poops -= 1
            self.clean_count += 1
            self.happiness = min(100.0, self.happiness + 8)
            self.calling = False

    def discipline_pet(self):
        if self.state in (STATE_DEAD, STATE_GHOST) or self.sleeping:
            return
        if self.age - getattr(self, "_last_discipline", -1e9) < LIMITS["discipline"]:
            return
        self._last_discipline = self.age
        self.discipline = min(100.0, self.discipline + 20)
        self.happiness = max(0.0, self.happiness - 8)
        self.calling = False

class World:
    def __init__(self):
        self.room = "indoor"
        self.weather = "sun"
        self.weather_timer = 0.0
        self.cloud_x = 0.0
        rnd = random.Random(1337)
        self._stars = [(rnd.randint(0, 235), rnd.randint(4, 95)) for _ in range(18)]
        self._grass = [rnd.randint(0, 235) for _ in range(16)]
        self.particles = []
        self.shooting_star = None
        self.star_timer = random.uniform(20, 180)
        self.wish_fx = 0.0
        self.star_sound = None

    def daylight(self, at=None):
        if FORCE_DAYLIGHT is not None:
            return FORCE_DAYLIGHT
        h = time.localtime(at).tm_hour
        if HOUR_DAY_START <= h < HOUR_DAY_END:
            return "day"
        if (HOUR_DAY_END <= h < HOUR_NIGHT_START
                or HOUR_NIGHT_END <= h < HOUR_DAY_START):
            return "dusk"
        return "night"

    def update(self, dt):
        self.cloud_x = (self.cloud_x + 9 * dt) % (VW + 80)
        self.weather_timer += dt
        if self.weather_timer > 180:
            self.weather_timer = 0.0
            r = random.random()
            self.weather = ("sun" if r < 0.45 else "cloud"
                            if r < 0.70 else "rain" if r < 0.90 else "snow")

        if self.wish_fx > 0:
            self.wish_fx -= dt

        if self.room == "outdoor":
            if self.weather == "rain" and len(self.particles) < 26:
                if random.random() < dt * 24:
                    self.particles.append({
                        "kind": "rain",
                        "x": random.uniform(0, VW),
                        "y": random.uniform(-30 , 0),
                        "vy": random.uniform(280, 380) ,
                    })
            elif self.weather == "snow" and len(self.particles) < 22:
                if random.random() < dt * 10:
                    self.particles.append({
                        "kind": "snow",
                        "x": random.uniform(0, VW),
                        "y": random.uniform(-15 , 0),
                        "vy": random.uniform(22, 42) ,
                        "ph": random.uniform(0, 6.28),
                    })
            for p in self.particles[:]:
                p["y"] += p["vy"] * dt
                if p["kind"] == "snow":
                    p["x"] += math.sin(time.time() * 1.5 + p["ph"]) * 18 * dt
                if p["y"] > 185 :
                    self.particles.remove(p)
        else:
            if self.particles:
                self.particles.clear()
        if self.daylight() == "night":
            if self.shooting_star is None:
                self.star_timer -= dt
                if self.star_timer <= 0:
                    self.shooting_star = {
                        "x": -20 ,
                        "y": (15 + random.uniform(0, 45)) ,
                        "vx": (140 + random.uniform(0, 60)) ,
                        "vy": (30 + random.uniform(0, 25)) ,
                    }
                    if (self.star_sound is not None
                            and not getattr(self, "_ambient_muted", False)):
                        try:
                            self.star_sound.play()
                        except Exception:
                            pass
            else:
                s = self.shooting_star
                s["x"] += s["vx"] * dt
                s["y"] += s["vy"] * dt
                if s["x"] > VW + 30 :
                    self.shooting_star = None
                    self.star_timer = random.uniform(20, 185)
        else:
            self.shooting_star = None

    def apply_effects(self, pet, dt):
        if pet is not None:
            pet.outdoor = (self.room == "outdoor")
            pet._world = self
            if pet.outdoor and getattr(pet, "sleeping", False):
                pet.sleeping = False
                pet.light_on = True
                pet.calling = False
        if self.room != "outdoor" or pet.state in (STATE_DEAD, STATE_GHOST):
            return
        pet.happiness = min(100.0, pet.happiness + 0.05 * dt)
        pet.hunger = min(100.0, pet.hunger + 0.02 * dt)
        if self.weather == "snow":
            pet.happiness = min(100.0, pet.happiness + 0.02 * dt)
        # Regen-Krankheit jetzt zentral in Pet.update (OUTDOOR_SICK_INTERVAL / OUTDOOR_SICK_CHANCE)
# ============
# MINIGAME 1
# ============


AC_BACK = getattr(pygame, "K_AC_BACK", None)
APP_BG = getattr(pygame, "APP_WILLENTERBACKGROUND", None)
APP_FG = getattr(pygame, "APP_DIDENTERFOREGROUND", None)
WL = getattr(pygame, "WINDOWFOCUSLOST", None)
WG = getattr(pygame, "WINDOWFOCUSGAINED", None)
_SLEEPGUARD_GAME = None

class _SleepGuardSound(pygame.mixer.Sound):
    def play(self, loops=0, maxtime=0, fade_ms=0):
        g = _SLEEPGUARD_GAME
        p = getattr(g, "pet", None) if g is not None else None
        if p is not None and getattr(p, "sleeping", False):
            return None
        return pygame.mixer.Sound.play(self, loops, maxtime, fade_ms)

class Game:
    def __init__(self):
        self._alarm_refresh_t = 0.0
        self._last_notif_time = 0.0
        self._in_background = False
        self.surface = pygame.Surface((VW, VH))
        self.framebuf = None
        self.screen = None
        self.present_scale = None
        self.present_off_x = self.present_off_y = 0
        self._init_layout()
        self.apply_resolution()
        pygame.display.set_caption("PseudoPet")
        self.clock = pygame.time.Clock()
        self.font_micro = PixelFont(1)
        self.font_small = PixelFont(2)
        self.font       = PixelFont(2)
        self.font_big   = PixelFont(3)
        self.font_huge  = PixelFont(3)
        self.mode = "name"
        self.pet = None
        self.alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.name_input = ""
        self.name_cursor = 0
        self.egg_types = ["dot", "stripe", "clean"]
        self.egg_names = ["DOT", "STRIPE", "CLEAN"]
        self.egg_sel = 0
        self.menu_open = False
        self.menu_sel = 0
        self.menu_items = ["Feed", "Play", "Sleep", "Medicine", "Clean",
                           "Light", "Discipline", "Out/In", "Settings"]
        #self.menu_items.append("Notif-Test")   # temporaer zum Testen
        #self.menu_items.append("Evolve-Test")   # temporaer zum Testen
        self.submenu_open = False
        self.submenu_sel = 0
        self.submenu_kind = "games"        # <<< NEU: "games" | "settings"
        self.submenu_items = []
        self._away_since = None
        self.notifications_on = True       # <<< NEU: Kill-Switch
        if MiniGameFish is not None:
            self.submenu_items.extend(["Fishing"])
        if MiniGamePong is not None:
            self.submenu_items.extend(["Pong: AI", "Pong: Host", "Pong: Join"])
        self.buttons = [
            pygame.Rect(25 , 285 , 55 , 28),
            pygame.Rect(92 , 285 , 55 , 28),
            pygame.Rect(159 , 285 , 55 , 28),
        ]
        self.world = World()
        self.clock_widget = PixelClock(x=62, y=38, scale=2)
        self.roll_t = 0.0
        self.roll_dur = 1.2
        self.roll_dir = 1
        self.roll_turns = 2.0
        self.roll_mode = "tumble" 
        self.minigame = None
        self.offline_report = None
        self.pet_cooldown = 0.0
        self.petting = 0.0
        self.med_count = 0
        self.med_window_t = 0.0
        self.pet_strokes = 0
        self.pet_window_t = 0.0
        self.pet_msg = None
        self.pet_msg_t = 0.0
        self.pet_msg_pos = 0
        self.evo_flash = 0.0
        self._last_branch = None
        self.evo_fx = None
        self._last_sprite_key = None
        self.choice_options = []
        self.choice_sel = 0
        self._bg_since = None
        self.rep_t = 0.5
        self.fly_t = 0.0
        self.rep_t = [0.0, 0.0, 0.0]
        self.mouse_down = False
        self.mouse_hold_btn = None
        self._quit_hold_t = 0.0
        self.last_save_time = 0.0
        self._wake_check_t = 0.0
        self._was_full_asleep = False
        self._was_sick = False
        self._sneeze_t = 0.0
        self.sound_on = True
        self.music_on = False
        self.butterfly = None
        self.butterfly_timer = random.uniform(30.0, 150.0)
        self.butterfly_fx = None
        self.try_load()
        self._cancel_pet_alarm()
        if self.pet:
            self._last_branch = (self.pet.branch_key, self.pet.stage)

        self.poop_sound = None
        self.play_sound = None
        self.jamjam_sound = None
        self.kikiriki_sound = None
        self.peng_sound = None
        self.star_sound = None
        self.pup_sound = None
        self.hust_sound = None
        self.sneeze_sound = None
        self.pow_sound = None
        self.boom_sound = None
        self.flutter_sound = None
        self.clap_sound = None
        self.played_crack1=False
        self.played_crack2=False
        self.played_crack3=False
        for attr, fname in (("poop_sound", "poop.ogg"),
                            ("play_sound", "play.ogg"),
                            ("jamjam_sound", "jamjam.ogg"),
                            ("kikiriki_sound", "kikiriki.ogg"),
                            ("peng_sound", "peng.ogg"),
                            ("star_sound", "star.ogg"),
                            ("pup_sound", "pup.ogg"),
                            ("hust_sound", "hust.ogg"),
                            ("sneeze_sound", "sneeze.ogg"),
                            ("pow_sound", "pow.ogg"),
                            ("boom_sound", "boom.ogg"),
                            ("flutter_sound", "flutter.ogg"),
                            ("kiss_sound", "kiss.ogg"),
                            ("pseudosound_sound", "pseudosound.ogg"),
                            ("pills_sound", "pills.ogg"),
                            ("evolution", "evolution.ogg"),
                            ("whistle_sound", "whistle.ogg"),
                            ("hatch_sound", "hatch.ogg"),
                            ("clap_sound", "clap.ogg")):
            try:
                setattr(self, attr, pygame.mixer.Sound(path + fname))
            except Exception:
                pass
        for _attr, _fname in (("pup_sound", "pup.ogg"),
                              ("hust_sound", "hust.ogg"),
                              ("sneeze_sound", "sneeze.ogg"),
                              ("pow_sound", "pow.ogg"),
                              ("boom_sound", "boom.ogg"),
                              ("flutter_sound", "flutter.ogg"),
                              ("kiss_sound", "kiss.ogg"),
                              ("pseudosound_sound", "pseudosound.ogg"),
                              ("pills_sound", "pills.ogg"),
                              ("evolution", "evolution.ogg"),
                              ("whistle_sound", "whistle.ogg"),
                              ("hatch_sound", "hatch.ogg"),
                              ("clap_sound", "clap.ogg")):
            if getattr(self, _attr, None) is None:
                print("[sound] %s NICHT gefunden - Datei neben main.py legen!" % _fname)

        if self.kikiriki_sound is None:
            print("[sound] kikiriki.ogg NICHT gefunden - "
                  "Datei neben main.py legen!")
        if getattr(self, "star_sound", None) is None:
            print("[sound] star.ogg NICHT gefunden - "
                  "Datei neben main.py legen!")
        global _SLEEPGUARD_GAME
        _SLEEPGUARD_GAME = self
        for _attr, _fname in (("jamjam_sound", "jamjam.ogg"),
                              ("play_sound", "play.ogg"),
                              ("peng_sound", "peng.ogg"),
                              ("poop_sound", "poop.ogg"),
                              ("pup_sound", "pup.ogg"),
                              ("hust_sound", "hust.ogg"),
                              ("sneeze_sound", "sneeze.ogg"),
                              ("pow_sound", "pow.ogg"),
                              ("boom_sound", "boom.ogg"),
                              ("flutter_sound", "flutter.ogg"),
                              ("kiss_sound", "kiss.ogg"),
                              ("pseudosound_sound", "pseudosound.ogg"),
                              ("pills_sound", "pills.ogg"),
                              ("evolution", "evolution.ogg"),
                              ("whistle_sound", "whistle.ogg"),
                              ("hatch_sound", "hatch.ogg"),
                              ("clap_sound", "clap.ogg")):
            try:
                setattr(self, _attr, _SleepGuardSound(path + _fname))
            except Exception:
                pass
        self.world.star_sound = getattr(self, "star_sound", None)
        global _POOP_SOUND_HOOK
        _POOP_SOUND_HOOK = self.poop_sound
        if self.pet is not None:
            self.pet.poop_sound = self.poop_sound
        self.channel1 = pygame.mixer.Channel(1)
        self.channel2 = pygame.mixer.Channel(2)
        self.channel3 = pygame.mixer.Channel(3)
        self.bgm_volume = 0.55
        self.bgm_ready = False
        try:
            pygame.mixer.music.load(path + "pseudosound.ogg")
            pygame.mixer.music.set_volume(self.bgm_volume if self.music_on else 0.0)
            self.bgm_ready = True
        except Exception:
            print("[bgm] pseudosound.ogg nicht gefunden - keine Hintergrundmusik")
        if self.bgm_ready:
            if self.music_on:
                self.start_bgm()                    # <<< NEU: gespeicherten Zustand anwenden
            else:
                pygame.mixer.music.set_volume(0.0)
        if not self.sound_on:
            self._set_all_volumes(0.0)
            try:
                pygame.mixer.stop()
            except Exception:
                pass
        if not self.music_on:
            try:
                pygame.mixer.music.set_volume(0.0)
            except Exception:
                pass
        if self.offline_report:
            self.mode = "offline"

    def _init_layout(self):
        self.buttons = [pygame.Rect(rw(x), rh(252), rw(46), rh(44))
                        for x in (20, 97, 174)]
        self.name_grid = (rw(30), rh(72), rw(30), 6)
        MiniGameDefense.PET = (rw(120), rh(240))

    def _enter_background(self):
        if self._in_background:
            return
        self._in_background = True
        print("[lifecycle] -> Hintergrund")
        if self.pet:
            if self._away_since is None:
                self._away_since = time.time()
            self._bg_since = time.time()
            self.save()
            self._schedule_evolve_warning()
            self._schedule_need_warning()      # prüft Cooldown intern
            self._schedule_death_warning()
            if self._should_notify():
                reason = self._pet_need_reason()
                if reason:
                    msg = self._need_message(reason)
                    if self._notify(self._notif_title(), msg):
                        self._last_notif_time = time.time()  # ← nur bei echtem Senden

    def _enter_foreground(self):
        if not self._in_background:
            return
        self._in_background = False
        print("[lifecycle] -> Vordergrund")
        self._away_since = None
        self._cancel_pet_alarm()
        try:
            if self.music_on:
                pygame.mixer.music.unpause()
        except Exception:
            pass

        # --- Cooldown-Logik ---
        if self._bg_since is not None:
            bg_duration = time.time() - self._bg_since
            # Wenn die App länger als der Cooldown im Hintergrund war,
            # ist der Cooldown sicher abgelaufen → zurücksetzen
            if bg_duration >= NOTIF_COOLDOWN:
                self._last_notif_time = 0.0
                print(f"[notif] Cooldown zurückgesetzt (bg {bg_duration:.0f}s)")
        self._bg_since = None
        # --- Ende Cooldown-Logik ---

        if platform() == "android":
            try:
                from android.permissions import check_permission
                self.notif_permitted = check_permission("android.permission.POST_NOTIFICATIONS")
            except Exception:
                self.notif_permitted = True
        self._cancel_pet_alarm()

    def apply_resolution(self, win_w=None, win_h=None):
        global WIN_W, WIN_H
        if FULLSCREEN:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            WIN_W, WIN_H = self.screen.get_size()
        else:
            if win_w is None:
                win_w, win_h = WIN_W, WIN_H
            WIN_W, WIN_H = int(win_w), int(win_h)
            self.screen = pygame.display.set_mode((WIN_W, WIN_H))

        self.sw, self.sh = self.screen.get_size()
        if self.framebuf is None or self.framebuf.get_size() != (self.sw, self.sh):
            self.framebuf = pygame.Surface((self.sw, self.sh))
        self.display_w, self.display_h = self.sw, self.sh
        self.display_x, self.display_y = 0, 0

        self.present_scale = None
        self.present_off_x = self.present_off_y = 0
        self._init_layout()
        print(f"[res] screen={self.sw}x{self.sh} "
              f"framebuf={self.framebuf.get_size()} "
              f"surface={self.surface.get_size()} offsets=(0,0)")

    def _scroll_repeat(self, dt):
        kp = pygame.key.get_pressed()
        for btn in (0, 2):
            held = any(kp[k] for k in HOLD_KEYS.get(btn, ()))
            if not held and self.mouse_hold_btn == btn and self.mouse_down:
                held = True
            if held and self._can_scroll(btn):
                self.rep_t[btn] += dt
                if self.rep_t[btn] >= REPEAT_DELAY:
                    self.handle_input(btn)
                    self.rep_t[btn] = REPEAT_DELAY - REPEAT_RATE
            else:
                self.rep_t[btn] = 0.0

    def _can_scroll(self, btn):
        if self.mode == "name":
            return btn == 0
        if self.menu_open or self.submenu_open:
            return btn in (0, 2)
        if self.mode == "egg":
            return btn in (0, 2)
        return False

    def _settings_items(self):
        return [
            f"Sound: {'ON' if self.sound_on else 'OFF'}",
            f"Music: {'ON' if self.music_on else 'OFF'}",
            f"Notifications: {'ON' if self.notifications_on else 'OFF'}",
        ]

    def _games_items(self):
        items = ["Ball", "Defense", "SnackDrop"]
        if MiniGameFish is not None:
            items.append("Fishing")
        if MiniGamePong is not None:
            items.extend(["Pong: AI", "Pong: Host", "Pong: Join"])
        return items

    def present(self):
        if self.framebuf is None or self.screen is None:
            self.apply_resolution()

        fw, fh = self.framebuf.get_size()

        if fw * VH < fh * VW:
            s = fw / VW
            w2 = fw
            h2 = int(round(VH * s))
        else:
            s = max(1, min(fw // VW, fh // VH))
            w2, h2 = VW * s, VH * s

        off_x = (fw - w2) // 2
        off_y = (fh - h2) // 2
        scaled = pygame.transform.scale(self.surface, (w2, h2))
        self.framebuf.fill((0, 0, 0))
        self.framebuf.blit(scaled, (off_x, off_y))
        self.screen.blit(self.framebuf, (self.display_x, self.display_y))
        self.present_scale = s
        self.present_off_x = off_x
        self.present_off_y = off_y
        pygame.display.flip()

    def _ambient_sound_allowed(self):
        return self.mode not in ("name", "egg", "minigame")

    def _find_real_sound(self, obj):
        if isinstance(obj, pygame.mixer.Sound):
            return obj
        for _n in ("sound", "snd", "_sound", "_snd"):
            cand = getattr(obj, _n, None)
            if isinstance(cand, pygame.mixer.Sound):
                return cand
        for v in getattr(obj, "__dict__", {}).values():
            if isinstance(v, pygame.mixer.Sound):
                return v
        return None

    def _set_all_volumes(self, vol):
        for attr in ("poop_sound", "play_sound", "jamjam_sound",
                     "kikiriki_sound", "peng_sound", "star_sound",
                     "pup_sound", "hust_sound", "sneeze_sound",
                     "pow_sound", "boom_sound", "flutter_sound",
                     "kiss_sound", "pseudosound_sound", "clap_sound",
                     "hatch_sound", "whistle_sound", "evolution",
                     "pills_sound"):
            obj = getattr(self, attr, None)
            if obj is None:
                continue
            snd = self._find_real_sound(obj)
            if snd is not None:
                try:
                    snd.set_volume(vol)
                except Exception:
                    pass

    def toggle_sound(self):
        self.sound_on = not self.sound_on
        self._set_all_volumes(1.0 if self.sound_on else 0.0)
        if not self.sound_on:
            try:
                pygame.mixer.stop()
            except Exception:
                pass
        self.show_pet_msg("SOUND ON" if self.sound_on else "SOUND OFF", 1.2)

    def toggle_music(self):
        self.music_on = not self.music_on
        try:
            if self.music_on:
                pygame.mixer.music.set_volume(self.bgm_volume)
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.play(-1, fade_ms=400)
            else:
                pygame.mixer.music.fadeout(400)   # statt nur Volume 0: richtig stoppen
        except Exception:
            pass
        self.show_pet_msg("MUSIC ON" if self.music_on else "MUSIC OFF", 1.2)
        self.save()                               # Status sofort sichern

    def _play_flutter(self):
        if not self._ambient_sound_allowed():
            return
        if self.flutter_sound is not None:
            try:
                self.flutter_sound.play()
            except Exception:
                pass

    def _play_kiss(self):
        if self.kiss_sound is not None:
            try:
                self.kiss_sound.play()
            except Exception:
                pass

    def _play_pills(self):
        if self.pills_sound is not None:
            try:
                self.pills_sound.play()
            except Exception:
                pass

    def _play_whistle(self):
        if self.whistle_sound is not None:
            try:
                self.whistle_sound.play()
            except Exception:
                pass

    def _play_hatch(self):
        if self.hatch_sound is not None:
            try:
                self.hatch_sound.play()
            except Exception:
                pass

    def _play_pseudosound(self):
        if self.pseudosound_sound is not None:
            try:
                self.pseudosound_sound.play()
            except Exception:
                pass

    def _play_clap(self):
        if not self._ambient_sound_allowed():
            return
        if self.clap_sound is not None:
            try:
                self.clap_sound.play()
            except Exception:
                pass

    def _need_message(self, reason):
        msgs = MESSAGES.get(reason, MESSAGES["happy"])
        return random.choice(msgs).format(name=self.pet.name)

    def start_bgm(self):
        if not self.music_on:                          # <<< Guard: nie starten, wenn "aus"
            return
        if not getattr(self, "bgm_ready", False):
            return
        try:
            pygame.mixer.music.set_volume(self.bgm_volume)   # <<< NEU
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1, fade_ms=600)
        except Exception:
            pass

    def stop_bgm(self, fade_ms=400):
        try:
            pygame.mixer.music.fadeout(fade_ms)
        except Exception:
            pass

    def _fmt_absence(self, secs):
        if secs < 60:
            return f"{secs:.0f} SEC"
        if secs < 3600:
            return f"{secs / 60:.0f} MIN"
        h = secs / 3600
        if h < 10:
            return f"{h:.1f} H"
        return f"{h:.0f} H"

    def update_butterfly(self, dt):
        if self.butterfly is None:
            if (self.pet is not None
                    and self.world.daylight() == "day"):
                self.butterfly_timer -= dt
                if self.butterfly_timer <= 0.0:
                    d = random.choice((-1, 1))
                    y0 = random.uniform(rhf(45.0), rhf(105.0))
                    self.butterfly = {
                        "x": rwf(-30.0) if d > 0 else (VW + rwf(30.0)),
                        "dir": d,
                        "y0": y0,
                        "t": 0.0,
                        "speed": random.uniform(rwf(24.0), rwf(34.0)),
                        "phase": random.uniform(0.0, 6.28),
                        "amp": random.uniform(rhf(10.0), rhf(22.0)),
                    }
                    self.butterfly_timer = random.uniform(42.0, 180.0)
                    if self._ambient_sound_allowed():
                        self._play_flutter()
            return
        b = self.butterfly
        if self.world.daylight() != "day":
            self.butterfly = None
            self.butterfly_timer = random.uniform(30.0, 150.0)
            return
        b["t"] += dt
        b["x"] += b["dir"] * b["speed"] * dt
        b["y"] = b["y0"] + math.sin(b["t"] * 2.4 + b["phase"]) * b["amp"]
        off = rwf(40.0)
        if ((b["dir"] > 0 and b["x"] > VW + off)
                or (b["dir"] < 0 and b["x"] < -off)):
            self.butterfly = None
            self.butterfly_timer = random.uniform(50.0, 185.0)

    def try_catch_butterfly(self):
        if self.butterfly is None:
            return False
        pos = self.butterfly_touch_pos()
        if pos is None:
            pos = (VW // 2, rh(100))
        self.butterfly = None
        self.butterfly_timer = random.uniform(50.0, 185.0)
        self.butterfly_fx = {"x": pos[0], "y": pos[1], "t": 1.2}
        if self.pet:
            self.pet.happiness = min(100.0, self.pet.happiness + 8)
        if self.flutter_sound is not None:
            self.flutter_sound.stop()
        self._play_clap()
        print("[butterfly] gefangen! Happiness +8")
        return True

    def butterfly_touch_pos(self):
        b = self.butterfly
        if b is None:
            return None
        y = b.get("y", b["y0"])
        if self.world.room == "outdoor":
            return (b["x"], y)
        ix, iy, iw, ih = self._window_inner()
        rx = ix + (b["x"] / VW) * iw
        ry = iy + (y / rh(120)) * ih
        return (rx, ry)

    def draw_butterfly_at(self, x, y):
        c = self.get_colors()
        key = "butterfly" if int(time.time() * 8) % 2 == 0 else "butterfly2"
        bob = math.sin(time.time() * 9.0) * rh(2)
        surf = make_sprite_surface(key, rs(2), c["fg"])
        self.surface.blit(surf, surf.get_rect(center=(int(x), int(y + bob))))

    def draw_butterfly_in_window(self):
        b = self.butterfly
        if b is None:
            return
        night = (self.world.daylight() == "night")
        col = WHITE if night else BLACK
        ix, iy, iw, ih = self._window_inner()
        y = b.get("y", b["y0"])
        sx = (b["x"] / VW) * iw
        sy = (y / rh(120)) * ih
        m = 4   # Rand = halbe Spritebreite, damit nichts im Rahmen klebt
        sx = max(m, min(iw - 1 - m, sx))
        sy = max(m, min(ih - 1 - m, sy))
        key = "butterfly" if int(time.time() * 8) % 2 == 0 else "butterfly2"
        surf = make_sprite_surface(key, rs(1), col)
        old_clip = self.surface.get_clip()
        self.surface.set_clip((ix, iy, iw, ih))
        self.surface.blit(surf, surf.get_rect(
            center=(int(ix + sx), int(iy + sy))))
        self.surface.set_clip(old_clip)

    def get_colors(self):
        if (self.pet and not self.pet.light_on
                and self.mode in ("game", "status", "minigame", "choice", "offline")):
            base = {"bg": BLACK, "fg": WHITE, "grid": DARK_GRAY, "text": WHITE,
                    "box_bg": BLACK, "box_border": WHITE}
        else:
            base = {"bg": WHITE, "fg": BLACK, "grid": (127, 127, 127),
                    "text": BLACK, "box_bg": WHITE, "box_border": BLACK}
        if (self.mode in ("game", "status", "minigame", "offline")
                and self.world.room == "outdoor"
                and self.world.daylight() == "night"):
            base.update(bg=BLACK, fg=WHITE, grid=DARK_GRAY, text=WHITE,
                        box_bg=BLACK, box_border=WHITE)
        return base

    def draw_pixel_sprite(self, key, cx, cy, scale=4, bounce=0, shake=0, alpha=255, rot=0, flipx=False, flipy=False):
        if key not in SPRITES:
            return
        if (self.mode == "game" and self.pet is not None
                and getattr(self.pet, "sleeping", False)
                and key == self.pet.get_sprite_key()):
            self._draw_zzz(int(cx), int(cy))
        c = self.get_colors()
        if alpha < 255:
            rows = SPRITES[key]
            w = max(len(r) for r in rows)
            surf = pygame.Surface((w * scale, len(rows) * scale), pygame.SRCALPHA)
            aq = max(0, min(255, int(alpha)))
            for y, row in enumerate(rows):
                for x, ch in enumerate(row):
                    if ch in "XO-*/\\" and ((x * 5 + y * 3) % 256) < aq:
                        pygame.draw.rect(surf, c["fg"],
                                         (x * scale, y * scale, scale, scale))
            if flipx or flipy:
                surf = pygame.transform.flip(surf, flipx, flipy)
            if rot:
                surf = pygame.transform.rotate(surf, int(rot) % 360)
        else:
            surf = make_sprite_surface(key, scale, c["fg"], rot=rot, flipx=flipx, flipy=flipy)
        rect = surf.get_rect(center=(int(cx + shake), int(cy + bounce)))
        self.surface.blit(surf, rect)

    def _draw_zzz(self, px, py):
        c = self.get_colors()
        t = time.time()
        for i in range(3):
            ph = (t * 0.7 + i / 3.0) % 1.0
            if ph > 0.85:
                continue
            rise = ph * rh(24)
            x = px + rw(12) + i * rw(6) + math.sin(ph * 6.283) * rw(3)
            y = py - rh(16) - rise
            zt = self.font_big.render("Z", True, c["text"])
            self.surface.blit(zt, zt.get_rect(center=(int(x), int(y))))

    def start_roll(self, dur=1.2, direction=1, turns=2.0, mode="tumble"):
        if getattr(self, "roll_t", 0) > 0 or self.pet is None:
            return False
        p = self.pet
        if p.sleeping or p.choice_pending is not None:
            return False
        if p.state in (STATE_DEAD, STATE_GHOST, STATE_HATCHING):
            return False
        self.roll_dur = max(0.3, float(dur))
        self.roll_t = self.roll_dur
        self.roll_dir = 1 if direction >= 0 else -1
        self.roll_turns = float(turns)
        self.roll_mode = mode
        return True

    def _draw_roll(self, cx):
        if self.pet is None or getattr(self, "roll_t", 0) <= 0:
            return False
        c = self.get_colors()
        key = self.pet.get_sprite_key()
        sc = rs(4)
        dur = max(0.05, self.roll_dur)
        prog = 1.0 - (max(0.0, self.roll_t) / dur)
        prog = max(0.0, min(1.0, prog))
        angle = -self.roll_dir * 360.0 * self.roll_turns * prog
        flipy = False
        if self.roll_mode == "tumble":
            angle = round(angle / 90.0) * 90.0
        elif self.roll_mode == "flip":
            angle = 0
            flipy = (0.20 <= prog < 0.80)
        jump = math.sin(prog * math.pi) * rh(38)
        travel = (prog - 0.5) * rw(56) * self.roll_dir
        surf = make_sprite_surface(key, sc, c["fg"], rot=angle, flipy=flipy)
        rect = surf.get_rect()
        rect.bottom = rh(180) - int(jump)
        rect.centerx = int(cx + travel)
        self.surface.blit(surf, rect)
        if jump < rh(9):
            for i in (-1, 0, 1):
                pygame.draw.rect(self.surface, c["fg"],
                                 (rect.centerx + i * rw(9), rh(178), rs(1), rs(1)))
        return True


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

    def draw_buttons(self):
        labels = ["A", "B", "C"]
        for i, rect in enumerate(self.buttons):
            pygame.draw.ellipse(self.surface, WHITE, rect)
            pygame.draw.ellipse(self.surface, BLACK, rect, rs(2))
            t = self.font_big.render(labels[i], True, BLACK)
            self.surface.blit(t, t.get_rect(center=rect.center))

    def draw_button_text(self, a, b, c, color=None):
        labels = [a, b, c]
        col = color if color is not None else self.get_colors()["text"]
        for i, rect in enumerate(self.buttons):
            t = self.font.render(labels[i], True, col)
            r = t.get_rect()
            r.midbottom = (rect.centerx, rect.top - rh(3))
            self.surface.blit(t, r)

    def draw_world(self):
        c = self.get_colors()
        self.surface.fill(c["bg"])
        dl = self.world.daylight()
        if self.world.room == "outdoor":
            if dl == "night":
                self.surface.blit(make_sprite_surface("moon", rs(4), c["fg"]), rp(200, 22))
            else:
                cx, cy = rw(214), rh(36)
                pygame.draw.circle(self.surface, c["fg"], (cx, cy), rs(7), rs(1))
                for a in range(0, 360, 45):
                    self.surface.fill(c["fg"], (int(cx + math.cos(math.radians(a)) * rs(10)),
                                              int(cy + math.sin(math.radians(a)) * rs(10)), rs(1), rs(1)))

            if dl == "night":
                for (sx, sy) in self.world._stars:
                    pygame.draw.rect(self.surface, (255, 255, 255),
                                     (sx, sy, rs(2), rs(2)))

            else:
                for i in range(2):
                    cx = int(self.world.cloud_x + i * rw(130)) % (VW + rw(80))
                    self.surface.blit(make_sprite_surface("cloud", rs(3), c["fg"]),
                                      (cx - rw(40), rh(30)))
            pygame.draw.line(self.surface, c["fg"], (0, rh(180)), (VW, rh(180)), rs(2))
            for gx in self.world._grass:
                pygame.draw.line(self.surface, c["fg"], (gx, rh(180)),
                                 (gx - rw(2), rh(174)))
            self.surface.blit(make_sprite_surface("tree", rs(4), c["fg"]), rp(12, 140))
            self.surface.blit(make_sprite_surface("flower", rs(2), c["fg"]), rp(206, 172))
            self.surface.blit(make_sprite_surface("flower", rs(2), c["fg"]), rp(115, 199))
            self.surface.blit(make_sprite_surface("sprout", rs(2), c["fg"]), rp(42, 195))
            self.surface.blit(make_sprite_surface("sprout", rs(2), c["fg"]), rp(75, 210))
            self.surface.blit(make_sprite_surface("tulip", rs(2), c["fg"]), rp(64, 255))
            self.surface.blit(make_sprite_surface("tulip", rs(3), c["fg"]), rp(180, 190))
            self.surface.blit(make_sprite_surface("mush_small", rs(2), c["fg"]), rp(145, 185))
            for p in self.world.particles:
                if p["kind"] == "rain":
                    pygame.draw.line(self.surface, c["fg"],
                                     (int(p["x"]), int(p["y"])),
                                     (int(p["x"]) + rw(2), int(p["y"]) + rh(4)))
                else:
                    pygame.draw.rect(self.surface, c["fg"],
                                     (int(p["x"]), int(p["y"]), rs(2), rs(2)))
            st = self.world.shooting_star
            if st is not None:
                for i in range(9):
                    px = int(st["x"] - st["vx"] * 0.028 * i)
                    py = int(st["y"] - st["vy"] * 0.028 * i)
                    if 0 <= px < VW and 0 <= py < VH:
                        size = rs((9 - i) // 3)
                        pygame.draw.rect(self.surface, c["fg"], (px, py, size, size))
            if self.butterfly is not None:
                self.draw_butterfly_at(
                    self.butterfly["x"],
                    self.butterfly.get("y", self.butterfly["y0"]))
        else:
            for wy in range(rh(30), rh(180), rh(12)):
                for wx in range(rw(8), VW, rw(16)):
                    pygame.draw.rect(self.surface, c["grid"], (wx, wy, rs(1), rs(1)))
            self.draw_door()
            if hasattr(self, 'clock_widget'):
                self.clock_widget.draw(self.surface, fg=c["fg"], bg=c["bg"])
                pygame.draw.line(self.surface, c["fg"], (0, rh(180)), (VW, rh(180)), rs(2))
                for fx in range(rw(-140), VW, rw(24)):
                    pygame.draw.line(self.surface, c["grid"], (fx, rh(184)),
                                    (fx + rw(96), rh(280)))
            self.draw_window()
            self.draw_star_in_window()
            self.draw_butterfly_in_window()
        if self.world.wish_fx > 0 and self.mode == "game":
            fx = self.world.wish_fx
            if int(fx * 6) % 2 == 0:
                t = self.font_huge.render("WISH!", True, c["text"])
                self.surface.blit(t, t.get_rect(center=(VW // 2, rh(70))))
            star_sz = rs(int(3 + 2 * abs(math.sin(fx * 4))))
            self.draw_pixel_sprite("star" if "star" in SPRITES else "heart",
                                   VW // 2, rh(100), scale=star_sz)
            rise = (2.5 - fx) * rh(35)
            self.draw_pixel_sprite("heart", VW // 2 - rw(40), rh(160) - rise, scale=rs(2))
            self.draw_pixel_sprite("heart", VW // 2 + rw(40), rh(160) - rise * 0.7, scale=rs(2))
        bfx = self.butterfly_fx
        if bfx is not None and self.mode == "game":
            brise = (1.2 - bfx["t"]) * rh(30)
            self.draw_pixel_sprite("heart", bfx["x"], bfx["y"] - brise, scale=rs(2))
            t = self.font_big.render("+8", True, c["text"])
            self.surface.blit(t, t.get_rect(
                center=(int(bfx["x"]), int(bfx["y"] - brise - rh(16)))))

    def draw_door(self):
        c = self.get_colors()
        dx, dy, dw, dh = rw(14), rh(100), rw(36), rh(80)
        pygame.draw.rect(self.surface, c["bg"], (dx, dy, dw, dh))
        pygame.draw.rect(self.surface, c["fg"], (dx, dy, dw, dh), rs(2))
        pygame.draw.rect(self.surface, c["fg"],
                         (dx + rw(6), dy + rh(6), dw - rw(12), dh - rh(12)), rs(1))
        pygame.draw.rect(self.surface, c["fg"],
                         (dx + dw - rw(10), dy + dh // 2 - rh(2), rw(4), rh(4)))

    def draw_window(self):
        c = self.get_colors()
        dl = self.world.daylight()
        wx, wy, ww, wh = rw(148), rh(32), rw(60), rh(56)
        night = (dl == "night")
        sky = BLACK if night else WHITE
        pygame.draw.rect(self.surface, sky, (wx + rw(1), wy + rh(2),
                                             ww - rw(1), wh - rh(2)))
        pygame.draw.rect(self.surface, GRAY, (wx, wy, ww, wh), rs(3))
        pygame.draw.line(self.surface, GRAY, (wx + ww // 2, wy + rh(2)),
                         (wx + ww // 2, wy + wh - rh(2)), rs(1))
        pygame.draw.line(self.surface, GRAY, (wx + rw(2), wy + wh // 2),
                         (wx + ww - rw(2), wy + wh // 2), rs(1))
        sky_fg = WHITE if night else BLACK
        if night:
            self.surface.blit(make_sprite_surface("moon", rs(2), sky_fg),
                              (wx + rw(8), wy + rh(7)))
            for i in range(4):
                sx = wx + rw(20) + i * rw(9)
                sy = wy + rh(10) + (i % 2) * rh(8)
                pygame.draw.rect(self.surface, sky_fg, (sx, sy, rs(1), rs(1)))
        else:
            scx, scy = wx + rw(12), wy + rh(10)
            pygame.draw.circle(self.surface, sky_fg, (scx, scy), rs(3), rs(1))
            for a in range(0, 360, 45):
                self.surface.fill(sky_fg, (int(scx + math.cos(math.radians(a)) * rs(5)),
                                        int(scy + math.sin(math.radians(a)) * rs(5)), rs(1), rs(1)))
            self.surface.blit(make_sprite_surface("cloud", rs(1), sky_fg),
                              (wx + rw(45), wy + rh(8)))
        tms = int(time.time() * 100)
        if self.world.weather == "rain":
            for i in range(3):
                rx = wx + rw(10) + i * rw(16)
                ry = wy + rh(6) + (tms // 6 + i * 7) % rh(44)
                pygame.draw.line(self.surface, sky_fg, (rx, ry), (rx, ry + rh(3)))
        elif self.world.weather == "snow":
            for i in range(4):
                rx = wx + rw(8) + i * rw(13) + int(math.sin(tms / 40.0 + i) * rw(2))
                ry = wy + rh(28) + (tms // 3 + i * 5) % rh(22)
                pygame.draw.rect(self.surface, sky_fg, (rx, ry, rs(1), rs(1)))

    def _window_inner(self):
        return (rw(151), rh(35), rw(54), rh(50))

    def star_touch_pos(self):
        st = self.world.shooting_star
        if st is None:
            return None
        if self.world.room == "outdoor":
            return (st["x"], st["y"])
        ix, iy, iw, ih = self._window_inner()
        rx = ix + (st["x"] / VW) * iw
        ry = iy + (st["y"] / rh(120)) * ih
        return (rx, ry)

    def draw_star_in_window(self):
        st = self.world.shooting_star
        if st is None:
            return
        night = (self.world.daylight() == "night")
        star_color = WHITE if night else self.get_colors()["fg"]
        ix, iy, iw, ih = self._window_inner()
        sx = (st["x"] / VW) * iw
        sy = (st["y"] / rh(120)) * ih
        kx = iw / VW
        ky = ih / rh(120)
        m = 2
        sx = max(m, min(iw - 1 - m, sx))
        sy = max(m, min(ih - 1 - m, sy))
        old_clip = self.surface.get_clip()
        self.surface.set_clip((ix, iy, iw, ih))
        for i in range(6):
            px = int(ix + sx - st["vx"] * 0.03 * i * kx)
            py = int(iy + sy - st["vy"] * 0.03 * i * ky)
            size = rs(2) if i == 0 else rs(1)
            pygame.draw.rect(self.surface, star_color, (px, py, size, size))
        self.surface.set_clip(old_clip)

    def draw_poops(self):
        if not self.pet or self.pet.poops <= 0:
            return
        c = self.get_colors()
        for i in range(self.pet.poops):
            _row = i // 6
            _col = i % 6
            px = rw(35) + _col * rw(38)
            py = rh(200) + _row * rh(26)
            self.draw_pixel_sprite("poop", px, py, scale=rs(3))
            ang = self.fly_t * 3.2 + i * 2.1
            fx = int(px + math.cos(ang) * rw(13))
            fy = int(py - rh(12) + math.sin(ang * 1.7 + i) * rh(5))
            pygame.draw.rect(self.surface, c["fg"], (fx, fy, rs(2), rs(2)))
            if int(self.fly_t * 18) % 2 == 0:
                pygame.draw.rect(self.surface, c["fg"], (fx, fy, rs(1), rs(1)))
                pygame.draw.rect(self.surface, c["fg"], (fx + rw(2), fy, rs(1), rs(1)))

    def show_pet_msg(self, txt, dur=1.75):
        self.pet_msg = txt
        self.pet_msg_t = dur
        self.pet_msg_pos = random.randint(rw(-30), rw(30))

    def draw_pet_msg(self):
        cx = VW // 2
        cy = VH // 2
        if not self.pet_msg or self.pet_msg_t <= 0:
            return
        c = self.get_colors()
        t = self.font_big.render(self.pet_msg, True, c["text"])
        if int(time.time() * 2.5) % 2 == 0:
            t = pygame.transform.scale(
                t, (int(t.get_width() * 1.5), int(t.get_height() * 1.5)))
        self.surface.blit(t, t.get_rect(
            center=(VW // 2 + self.pet_msg_pos, rh(95))))

    def _floor_center_y(self, key, scale):
        rows = SPRITES.get(key)
        if not rows:
            return rh(125)
        return rh(180) - (len(rows) * rs(scale)) // 2

    def draw_pet(self):
        if not self.pet:
            return
        if self.evo_fx is not None:
            self.draw_evolution_fx()
            return
        cx = VW // 2
        c = self.get_colors()
        bounce, shake = 0, 0
        if self.pet.state == STATE_DEAD:
            cy = self._floor_center_y("gravestone", 5)
            self.draw_pixel_sprite("gravestone", cx, cy, scale=rs(5))
            self.draw_pixel_sprite("cross", cx, cy - rh(55), scale=rs(3))
            return
        if self.pet.state == STATE_GHOST:
            cy = self._floor_center_y("ghost", 4)
            ghost_y = cy - int(self.pet.state_timer * rh(9))
            ghost_x = cx + int(math.sin(self.pet.state_timer * 1.5) * rh(12))
            alpha = max(0, 255 - int(self.pet.state_timer * 20))
            self.draw_pixel_sprite("ghost", ghost_x, ghost_y, scale=rs(4), alpha=alpha)
            return
        if self.pet.state == STATE_HATCHING:
            cy = self._floor_center_y(self.pet.get_sprite_key(), 5)
            roll_x = int(self.pet.hatch_roll_x)
            if self.pet.hatch_phase in (0, 4):
                shake = random.randint(-rw(4), rw(4)) if self.pet.anim_frame % 2 == 0 else 0
                bounce = random.randint(-rh(2), rh(2))
            elif self.pet.hatch_phase == 2:
                shake = roll_x
                bounce = abs(math.sin(self.pet.anim_frame * 0.8)) * rh(3)
            else:
                shake = random.randint(-rw(1), rw(1))
            self.draw_pixel_sprite(self.pet.get_sprite_key(), cx + shake, cy,
                                   scale=rs(5), bounce=bounce)
            crack = c["bg"]
            if self.pet.hatch_phase >= 1:
                pygame.draw.line(self.surface, crack,
                                 (cx - rw(8) + shake, cy - rh(45)),
                                 (cx + rw(4) + shake, cy + rh(45)), rs(2))
                if self.played_crack1 == False:
                    self._play_hatch()
                    self.played_crack1 = True
            if self.pet.hatch_phase >= 3:
                pygame.draw.line(self.surface, crack,
                                 (cx + rw(8) + shake, cy - rh(45)),
                                 (cx - rw(6) + shake, cy + rh(45)), rs(2))
                pygame.draw.line(self.surface, crack,
                                 (cx + shake, cy - rh(45)),
                                 (cx + shake, cy + rh(45)), rs(2))
                if self.played_crack2 == False:
                    self._play_hatch()
                    self.played_crack2 = True
            if self.pet.hatch_phase >= 4:
                pygame.draw.line(self.surface, crack,
                                 (cx - rw(30) + shake, cy),
                                 (cx + rw(30) + shake, cy + rh(3)), rs(2))
                if self.played_crack3 == False:
                    self._play_hatch()
                    self.played_crack3 = True
            return
        cy = self._floor_center_y(self.pet.get_sprite_key(), 4)

        if self.pet.sleeping:
            bounce = math.sin(self.pet.anim_frame * 0.5) * rh(1)
        elif self.pet.calling:
            shake = math.sin(self.pet.anim_frame * 2.0) * rh(4)
        else:
            bounce = abs(math.sin(self.pet.anim_frame * 0.7)) * rh(3)
        if getattr(self, "roll_t", 0) > 0 and self._draw_roll(cx):
            pass
        elif self.evo_flash > 0 and int(self.evo_flash * 8) % 2 == 1:
            pass
        else:
            self.draw_pixel_sprite(self.pet.get_sprite_key(), cx, cy, scale=rs(4),
                                   bounce=bounce, shake=shake)
        if self.pet.sick and not self.pet.sleeping and self.pet.anim_frame % 2 == 0:
            t = self.font_big.render("X", True, c["text"])
            self.surface.blit(t, (cx - rw(32), cy - rh(40)))
        if self.pet.calling and not self.pet.sleeping:
            t = self.font_huge.render("!", True, c["text"])
            if int(time.time() * 2.5) % 2 == 0:
                t = pygame.transform.scale(
                    t, (int(t.get_width() * 1.5), int(t.get_height() * 1.5)))
            t_rect = t.get_rect(center=(int(cx + rw(37)), int(cy - rh(34))))
            self.surface.blit(t, t_rect)
        if self.petting > 0 and not self.pet.sleeping:
            self.draw_pixel_sprite("heart", cx + rw(46), cy - rh(46), scale=rs(3))
        if (self.pet.stage == STAGE_ADULT and not self.pet.premium_unlocked
                and self.pet.premium_timer > 0):
            pct = min(1.0, self.pet.premium_timer / 60.0)
            bar_w, bar_h = rw(40), rh(4)
            bx, by = cx - bar_w // 2, rh(183)
            pygame.draw.rect(self.surface, c["fg"], (bx, by, bar_w, bar_h), rs(1))
            fill = int((bar_w - rw(2)) * pct)
            if fill > 0:
                pygame.draw.rect(self.surface, c["fg"],
                                 (bx + rw(1), by + rh(1), fill, bar_h - rh(2)))
            t = self.font.render("*", True, c["fg"])
            self.surface.blit(t, (bx + bar_w + rw(4), by - rh(2)))
        if self.pet.stage == STAGE_PREMIUM:
            t = self.font_big.render("*", True, c["text"])
            self.surface.blit(t, (cx + rw(30), cy - rh(50)))
        self.draw_poops()
        if self.pet.state == STATE_EATING:
            foods = ["+", "*", "o", "."]
            t = self.font_big.render(foods[self.pet.anim_frame % 4], True, c["text"])
            self.surface.blit(t, (cx + rw(24), cy - rh(18) - self.pet.anim_frame * rh(3)))
            t2 = self.font_big.render(foods[(self.pet.anim_frame + 2) % 4], True, c["text"])
            self.surface.blit(t2, (cx + rw(36), cy - rh(12) - self.pet.anim_frame * rh(2)))
        if self.pet.state == STATE_PLAYING:
            ball_x = cx + math.sin(self.pet.anim_frame * 1.2) * rw(35)
            ball_y = cy - rh(15) + abs(math.cos(self.pet.anim_frame * 1.2)) * rh(25)
            self.draw_pixel_sprite("ball", int(ball_x), int(ball_y), scale=rs(3))

    def draw_status_bars(self):
        if not self.pet or self.pet.state in (STATE_DEAD, STATE_GHOST):
            return
        c = self.get_colors()
        bar_w, bar_h = rw(52), rh(5)
        y = rh(8)
        stats = [("Hunger", self.pet.hunger, True), ("Happy", self.pet.happiness, False),
                 ("Energy", self.pet.energy, False), ("Health", self.pet.health, False)]
        for i, (label, val, inverted) in enumerate(stats):
            x = rw(6) + i * rw(59)
            border = rs(1)
            pygame.draw.rect(self.surface, c["fg"], (x, y, bar_w, bar_h), border)
            pct = (100.0 - val) / 100.0 if inverted else val / 100.0
            inner_w = bar_w - 2 * border
            inner_h = bar_h - 2 * border
            fill = max(0, min(inner_w, int(round(inner_w * pct))))
            if fill > 0:
                pygame.draw.rect(self.surface, c["fg"],
                                 (x + border, y + border, fill, inner_h))
            t = self.font_micro.render(label, True, c["text"])
            self.surface.blit(t, (x + rw(2), y + rh(7)))

    def _name_start_rect(self):
        gx, gy, cell, _cols = self.name_grid
        return pygame.Rect(gx + 2 * cell, gy + 4 * cell, 4 * cell, cell)

    def draw_name_input(self):
        self.surface.fill(self.get_colors()["bg"])
        c = self.get_colors()
        t = self.font_huge.render("NAME?", True, c["text"])
        self.surface.blit(t, t.get_rect(center=(VW // 2, rh(22))))
        display = self.name_input + "_" if len(self.name_input) < 8 else self.name_input
        t = self.font_big.render(display, True, c["text"])
        self.surface.blit(t, t.get_rect(center=(VW // 2, rh(52))))
        gx, gy, cell, cols = self.name_grid
        for i, char in enumerate(self.alphabet):
            row, column = divmod(i, cols)
            x = gx + column * cell
            y = gy + row * cell
            if i == self.name_cursor:
                pygame.draw.rect(self.surface, c["fg"], (x, y, cell, cell))
                char_color = c["bg"]
            else:
                pygame.draw.rect(self.surface, c["fg"], (x, y, cell, cell), rs(1))
                char_color = c["text"]
            t = self.font_big.render(char, True, char_color)
            self.surface.blit(t, t.get_rect(center=(x + cell // 2, y + cell // 2)))
        sr = self._name_start_rect()
        if self.name_cursor == len(self.alphabet):
            pygame.draw.rect(self.surface, c["fg"], sr)
            t = self.font_big.render("START", True, c["bg"])
        else:
            pygame.draw.rect(self.surface, c["fg"], sr, rs(2))
            t = self.font_big.render("START", True, c["text"])
        self.surface.blit(t, t.get_rect(center=sr.center))
        self.draw_button_text("MOVE", "SELECT", "DELETE")

    def draw_egg_select(self):
        self.surface.fill(self.get_colors()["bg"])
        c = self.get_colors()
        t = self.font_huge.render("CHOOSE EGG", True, c["text"])
        self.surface.blit(t, t.get_rect(center=(VW // 2, rh(20))))
        t = self.font.render(f"Name: {self.name_input}", True, c["text"])
        self.surface.blit(t, t.get_rect(center=(VW // 2, rh(55))))
        positions = [rw(55), rw(120), rw(185)]
        for i, (egg_type, name) in enumerate(zip(self.egg_types, self.egg_names)):
            x = positions[i]
            selected = (i == self.egg_sel)
            if selected:
                box_x = x - rw(30)
                pygame.draw.rect(self.surface, c["fg"],
                                 (box_x, rh(100), rw(60), rh(80)))
                surf = make_sprite_surface(f"egg_{egg_type}", rs(4), c["bg"])
            else:
                surf = make_sprite_surface(f"egg_{egg_type}", rs(4), c["fg"])
            self.surface.blit(surf, surf.get_rect(center=(x, rh(140))))
            color = c["bg"] if selected else c["text"]
            t = self.font_big.render(name, True, color)
        self.draw_button_text("<-", "OK", "->")

    def draw_choice(self):
        c = self.get_colors()
        self.surface.fill(c["bg"])
        t = self.font_huge.render("EVOLUTION!", True, c["text"])
        self.surface.blit(t, t.get_rect(center=(VW // 2, rh(16))))
        _nxt = (self.pet.choice_pending or {}).get("next")
        _sub = ("A baby hatches! Choose:" if _nxt == STAGE_BABY
                else f"{self.pet.name} grows up...")
        t = self.font.render(_sub, True, c["text"])
        self.surface.blit(t, t.get_rect(center=(VW // 2, rh(34))))
        xs = [rw(70), rw(170)]
        for i, (key, spritekey) in enumerate(self.choice_options):
            sel = (i == self.choice_sel)
            box = pygame.Rect(xs[i] - rw(42), rh(52), rw(84), rh(118))
            if sel:
                pygame.draw.rect(self.surface, c["fg"], box)
                surf = make_sprite_surface(spritekey, rs(4), c["bg"])
            else:
                pygame.draw.rect(self.surface, c["fg"], box, rs(1))
                surf = make_sprite_surface(spritekey, rs(4), c["fg"])
            self.surface.blit(surf, surf.get_rect(center=(xs[i], rh(105))))
            name = FORM_NAMES.get(key, key)
            t = self.font_big.render(name, True, c["bg"] if sel else c["text"])
            self.surface.blit(t, t.get_rect(center=(xs[i], rh(148))))
            self.draw_button_text("<-","OK","->")
            if CHOICE_REQUIRE_RULE and key in BRANCH_RULES \
                    and not BRANCH_RULES[key](self.pet):
                t = self.font.render("(LOCK)", True, c["bg"] if sel else c["text"])
                self.surface.blit(t, t.get_rect(center=(xs[i], rh(162))))

    def draw_menu(self):
        if not self.menu_open:
            return
        c = self.get_colors()
        r = rrect(28, 40, 184, 215)
        pygame.draw.rect(self.surface, c["box_bg"], r)
        pygame.draw.rect(self.surface, c["box_border"], r, rs(2))
        for i, item in enumerate(self.menu_items):
            y = rh(46 + i * 21)
            if i == self.menu_sel:
                pygame.draw.rect(self.surface, c["fg"],
                                 (rw(34), y - rh(2), rw(172), rh(17)))
                t = self.font.render(item, True, c["bg"])
            else:
                t = self.font.render(item, True, c["text"])
            self.surface.blit(t, (rw(40), y))

    def draw_submenu(self):
        if not self.submenu_open:
            return
        c = self.get_colors()
        item_count = len(self.submenu_items)
        box_h = rh(30 + item_count * 24)
        r = pygame.Rect(rw(40), rh(70), rw(160), box_h)
        pygame.draw.rect(self.surface, c["box_bg"], r)
        pygame.draw.rect(self.surface, c["box_border"], r, rs(2))
        title = "SETTINGS" if self.submenu_kind == "settings" else "PLAY"
        t = self.font_big.render(title, True, c["text"])
        #t = self.font_big.render("PLAY", True, c["text"])
        self.surface.blit(t, t.get_rect(center=(VW // 2, rh(82))))
        for i, item in enumerate(self.submenu_items):
            y = rh(96 + i * 24)
            if i == self.submenu_sel:
                pygame.draw.rect(self.surface, c["fg"],
                                 (rw(46), y - rh(2), rw(148), rh(18)))
                t = self.font.render(item, True, c["bg"])
            else:
                t = self.font.render(item, True, c["text"])
            self.surface.blit(t, (rw(52), y))

    def draw_status_screen(self):
        if not self.pet:
            return
        c = self.get_colors()
        r = rrect(15, 45, 210, 225)
        pygame.draw.rect(self.surface, c["box_bg"], r)
        pygame.draw.rect(self.surface, c["box_border"], r, rs(2))
        t = self.font_big.render(self.pet.name, True, c["text"])
        self.surface.blit(t, (rw(22), rh(55)))
        stage_text = self.pet.stage
        if self.pet.premium_unlocked:
            stage_text += " (*)"
        t = self.font.render(f"Age:{int(self.pet.age)}s {stage_text}", True, c["text"])
        self.surface.blit(t, (rw(22), rh(75)))
        if (self.pet.stage == STAGE_ADULT and not self.pet.premium_unlocked
                and not self.pet.is_dark):
            pct = min(1.0, self.pet.premium_timer / 60.0)
            t = self.font.render(f"Prem:{int(pct * 100)}%", True, c["text"])
            self.surface.blit(t, (rw(22), rh(105)))
        if self.pet.stage == STAGE_EGG:
            form = "???"
        else:
            fk = self.pet.chosen.get(self.pet.stage) or self.pet.egg_type
            if self.pet.stage == STAGE_PREMIUM:
                fk = self.pet.chosen.get(STAGE_ADULT) or self.pet.egg_type
            form = FORM_NAMES.get(fk, str(fk).upper())
        t = self.font_small.render(f"Form: {form}", True, c["text"])
        self.surface.blit(t, (rw(22), rh(90)))
        # stats = [("Hunger", self.pet.hunger, True),
        #          ("Happy", self.pet.happiness, False),
        #          ("Energy", self.pet.energy, False),
        #          ("Health", self.pet.health, False),
        #          ("Discipline", self.pet.discipline, False),
        #          ("Weight", self.pet.weight, False)]
        stats = [("Hunger", self.pet.hunger, True),
                ("Happy", self.pet.happiness, False),
                ("Energy", self.pet.energy, False),
                ("Health", self.pet.health, False),
                ("Discipline", self.pet.discipline, False)]
        # Gewicht separat als Text:
        y_w = rh(130 + len(stats) * 16)
        t = self.font.render("Weight:", True, c["text"])
        self.surface.blit(t, (rw(22), y_w))
        t = self.font.render(f"{self.pet.weight:.1f}", True, c["text"])
        self.surface.blit(t, (rw(110), y_w))
        for i, (label, val, inverted) in enumerate(stats):
            y = rh(130 + i * 16)
            t = self.font.render(label + ":", True, c["text"])
            self.surface.blit(t, (rw(22), y))
            border = rs(1)
            bx, by, bw, bh = rw(110), y, rw(88), rh(10)
            pygame.draw.rect(self.surface, c["fg"], (bx, by, bw, bh), border)
            pct = (100.0 - val) / 100.0 if inverted else val / 100.0
            inner_w = bw - 2 * border
            inner_h = bh - 2 * border
            fill = max(0, min(inner_w, int(round(inner_w * pct))))
            if fill > 0:
                pygame.draw.rect(self.surface, c["fg"],
                                 (bx + border, by + border, fill, inner_h))
            t = self.font.render(f"{int(val)}", True, c["text"])
            self.surface.blit(t, (rw(200), y))
        y = rh(248)
        x_pos = rw(22)
        if self.pet.sick:
            t = self.font.render("[SICK]", True, c["text"])
            self.surface.blit(t, (x_pos, y))
            x_pos += rw(55)
        if self.pet.sleeping:
            t = self.font.render("[SLEEP]", True, c["text"])
            self.surface.blit(t, (x_pos, y))
            x_pos += rw(60)
        if self.pet.poops > 0:
            t = self.font.render(f"[POOPx{self.pet.poops}]", True, c["text"])
            self.surface.blit(t, (x_pos, y))
            x_pos += rw(75)
        if not getattr(self, 'notif_permitted', True):
            t = self.font.render("[NO NOTIF]", True, c["text"])
            self.surface.blit(t, (x_pos, y))

    def draw_death(self):
        c = self.get_colors()
        r = rrect(40, 80, 160, 120)
        pygame.draw.rect(self.surface, c["box_bg"], r)
        pygame.draw.rect(self.surface, c["box_border"], r, rs(2))
        t = self.font_huge.render("R.I.P.", True, c["text"])
        self.surface.blit(t, t.get_rect(center=(VW // 2 + rw(2), rh(92))))
        t = self.font_big.render(self.pet.name, True, c["text"])
        self.surface.blit(t, t.get_rect(center=(VW // 2, rh(120))))
        t = self.font.render(f"Lived {int(self.pet.death_age)} seconds", True, c["text"])
        self.surface.blit(t, t.get_rect(center=(VW // 2, rh(145))))
        t = self.font.render("Press B to restart", True, c["text"])
        self.surface.blit(t, t.get_rect(center=(VW // 2, rh(170))))

    def draw_offline_report(self):
        self.draw_world()
        c = self.get_colors()
        rep = self.offline_report or {}
        r = rrect(20, 50, 200, 195)
        pygame.draw.rect(self.surface, c["box_bg"], r)
        pygame.draw.rect(self.surface, c["box_border"], r, rs(2))

        def center(txt, font, y):
            t = font.render(txt, True, c["text"])
            self.surface.blit(t, t.get_rect(center=(VW // 2, rh(y))))
        center("WELCOME BACK", self.font_big, 70)
        center(f"Away for {self._fmt_absence(self.offline_report['secs'])}", self.font, 100)
        lines = []
        if rep.get("new_poops", 0) > 0:
            lines.append(f"+{rep['new_poops']} poops  :(")
        if rep.get("became_sick"):
            lines.append("Got sick!")
        elif rep.get("sick"):
            lines.append("Still sick")
        if rep.get("stage_up"):
            lines.append("EVOLVED!")
        if int(rep.get("hunger", 0)) > 80:
            lines.append("Very hungry!")
        if not lines:
            lines.append("All fine :)")
        y = rh(130)
        for ln in lines:
            center(ln, self.font, y)
            y += rh(16)

    def draw_debug_hud(self):
        if DEBUG_SPEED <= 1 or not self.pet:
            return
        if self.pet.state in (STATE_DEAD, STATE_GHOST):
            return
        c = self.get_colors()
        times = {STAGE_EGG: HATCH_TIME, STAGE_BABY: BABY_TIME,
                 STAGE_CHILD: CHILD_TIME, STAGE_TEEN: TEEN_TIME}
        if self.pet.choice_pending:
            info = "CHOICE pending"
        elif self.pet.state == STATE_HATCHING:
            info = f"HATCH phase {self.pet.hatch_phase}/4"
        elif self.pet.stage in times:
            info = f"{self.pet.stage.upper()} {int(self.pet.stage_timer)}/{times[self.pet.stage]}s"
        else:
            info = (f"{self.pet.stage.upper()}  F:{self.pet.feed_count}"
                    f" P:{self.pet.play_count} C:{self.pet.clean_count}")
        info += f"  dk:{int(self.pet._dark_pct() * 100)}%"
        t = self.font_small.render(f"[x{DEBUG_SPEED}] {info}", True, c["text"])
        self.surface.blit(t, rp(8, 264))

    def draw(self):
        if self.mode == "name":
            self.draw_name_input()
        elif self.mode == "egg":
            self.draw_egg_select()
        elif self.mode == "choice":
            self.draw_choice()
        elif self.mode == "minigame" and self.minigame:
            self.minigame.draw(self)
        elif self.mode == "offline":
            self.draw_offline_report()
        elif self.mode == "game":
            self.draw_world()
            self.draw_pet()
            self.draw_pet_msg()
            self.draw_status_bars()
            self.draw_debug_hud()
            if self.pet and self.pet.state == STATE_DEAD:
                self.draw_death()
            elif self.submenu_open:
                self.draw_submenu()
            elif self.menu_open:
                self.draw_menu()
        elif self.mode == "status":
            self.draw_world()
            self.draw_pet()
            self.draw_status_bars()
            self.draw_status_screen()
        if getattr(self, "_quit_hold_t", 0.0) > 0.25 and self.mode == "game":
            frac = min(1.0, self._quit_hold_t / 2.0)
            bw = rw(60)
            bx = VW // 2 - bw // 2
            pygame.draw.rect(self.surface, self.get_colors()["fg"],
                             (bx, rh(244), int(bw * frac), rs(2)))
        self.draw_buttons()
        self.present()

    def handle_name_input(self, btn):
        if btn == 0:
            self.name_cursor = (self.name_cursor + 1) % (len(self.alphabet) + 1)
        elif btn == 1:
            if self.name_cursor == len(self.alphabet):      # START
                if len(self.name_input) >= 1:
                    self.mode = "egg"
            elif len(self.name_input) < 8:
                self.name_input += self.alphabet[self.name_cursor]
        elif btn == 2:
            if len(self.name_input) > 0:
                self.name_input = self.name_input[:-1]
            else:
                self.name_input = random.choice(
                    ["PUDDI", "BUBBL", "MELON", "BOBA", "TOFU", "MUFFI", "PIXEL", "NIBBL", "CHIP",
                    "GLITCH", "LUNA", "NOVA", "STAR", "COMET", "ORBIT", "RAT", "BLOOM", "PUSS",
                    "GIMBLE", "ZAPPO", "SQUID", "BERNHARD", "PETER", "HANS", "BERND", "SEPPEL",
                    "FLUFFY", "YANI", "GORDON", "HARRY", "ELIF", "MOMO", "TAMA", "PIXI", "BABO",
                    "KIKI", "ZAZU", "ZIPPO", "ALFI", "FRIEDA", "WUMBUS", "PINKY", "HENRY", "PUPSI",
                    "WABBL", "KLECKS", "BLOOP", "KNOPF", "KRUMEL", "FLOCKI", "POPPI", "MOPPEL",
                    "MOPSEL", "BLINKY", "ZIPPI", "MURMEL", "QUACKI", "PLOPP", "BEEP", "KNUFFI",
                    "TAPSI", "TABBY", "WUSCHEL", "PLUESCH", "ZOTTEL", "FUZZEL", "FUZZ", "BLASIUS",
                    "POPO", "REX", "SPEEDY","HASSO","AZZARD", "BEAN", "GUMMI", "COCO", "DONUT", "WAFFL",
                    "BERRY", "MINT", "YOGI", "QUARK", "VOID", "OTTO", "DIETER", "KURT", "UWE", "KLAUS",
                    "REINHARD", "WOLFGANG", "HANS", "DIETER", "BYTE", "BIT", "HEX", "DATA", "SCAN",
                    "VECTO", "CHROMA", "MODEM", "LOGIC", "MAC", "WOBBL", "BOING", "PING", "PIPPI",
                    "WUBI", "BOP", "PLOPPY", "PUFF", "WOLLY", "FLUFFY"])

    def handle_egg_select(self, btn):
        if btn == 0:
            self.egg_sel = (self.egg_sel - 1) % len(self.egg_types)
        elif btn == 1:
            self.pet = Pet(self.name_input, self.egg_types[self.egg_sel])
            self._last_branch = (self.pet.branch_key, self.pet.stage)
            self.mode = "game"
            self.save()
        elif btn == 2:
            self.egg_sel = (self.egg_sel + 1) % len(self.egg_types)

    def try_wish(self):
        w = self.world
        if not w.shooting_star:
            return False
        w.shooting_star = None
        w.wish_fx = 2.5
        w.star_timer = random.uniform(20, 185)
        if self.pet:
            self.pet.happiness = min(100.0, self.pet.happiness + 10)
        print("[wish] Wunsch erfuellt! Happiness +10")
        self._play_clap()
        return True

    def do_petting(self):
        if not self.pet:
            return False
        if (self.pet.state in (STATE_DEAD, STATE_GHOST, STATE_HATCHING)
                or self.pet.choice_pending is not None
                or self.pet.sleeping
                or self.pet_cooldown > 0):
            return False
        if self.pet_window_t > 0 and self.pet_strokes >= 3:
            return False
        if self.pet_window_t <= 0:
            self.pet_window_t = 20.0
            self.pet_strokes = 0
        self.pet_strokes += 1
        self.pet.happiness = min(100.0, self.pet.happiness + 4)
        self.pet_cooldown = 0.5
        self.petting = 0.9
        self._play_kiss()
        return True

    def handle_choice(self, btn):
        if not self.choice_options:
            self.mode = "game"
            return
        if btn == 0:
            self.choice_sel = 0
        elif btn == 2:
            self.choice_sel = min(1, len(self.choice_options) - 1)
        elif btn == 1:
            key = self.choice_options[self.choice_sel][0]
            if (CHOICE_REQUIRE_RULE and key in BRANCH_RULES
                    and not BRANCH_RULES[key](self.pet)):
                return
            nxt = self.pet.choice_pending["next"]
            self.pet._advance_stage(nxt, key)
            if nxt == STAGE_BABY and self.kikiriki_sound:
                try:
                    self.kikiriki_sound.play()
                except Exception:
                    pass
            self.mode = "game"

    def handle_game(self, btn):
        if not self.pet:
            return
        if self.pet.state == STATE_DEAD:
            if btn == 1:
                self.reset_game()
            return
        if self.pet.state == STATE_GHOST:
            if self.menu_open or self.submenu_open:
                self.menu_open = False
                self.submenu_open = False
            return
        if self.submenu_open:
            if btn == 0:
                self.submenu_sel = (self.submenu_sel + 1) % len(self.submenu_items)
            elif btn == 1:
                self.exec_submenu()
                if self.submenu_kind != "settings":   # Settings bleibt offen für weitere Toggles
                    self.submenu_open = False
            # elif btn == 2:
            #     self.submenu_open = False
            elif btn == 2:
                self.close_submenu()
        elif self.menu_open:
            if btn == 0:
                self.menu_sel = (self.menu_sel + 1) % len(self.menu_items)
            elif btn == 1:
                self.exec_menu()
                self.menu_open = False
            elif btn == 2:
                self.menu_open = False
        else:
            if btn == 0:
                self.menu_open = True
                self.menu_sel = 0
            elif btn == 1:
                if not self.try_wish() and not self.try_catch_butterfly():
                    self.mode = "status"
            elif btn == 2:
                if getattr(self.pet, "sleeping", False):
                    self._wake_up_pet()
                elif self.pet.poops > 0:
                    self.pet.clean()
                    if self.pup_sound is not None:
                        try:
                            self.channel1.play(self.pup_sound)
                        except Exception:
                            pass
                else:
                    self.do_petting()

    def handle_minigame(self, btn):
        if not self.minigame:
            self.mode = "game"
            return
        if self.minigame.finished:
            if btn == 1:
                if self.play_sound:
                    self.channel3.play(self.play_sound)
                self.minigame = None
                self.mode = "game"
            return
        self.minigame.handle(btn)

    def exec_menu(self):
        action = self.menu_items[self.menu_sel]
        if action == "Feed":
            if self.pet.feed():
                if self.jamjam_sound:
                    self.channel2.play(self.jamjam_sound)
            elif getattr(self.pet, 'sleeping', False):
                self.show_pet_msg("Zzz...", 1.5)
        elif action == "Play":
            self.submenu_kind = "games"
            self.submenu_items = self._games_items()
            self.submenu_open = True
            self.submenu_sel = 0

        elif action == "Settings":
            self.submenu_kind = "settings"
            self.submenu_items = self._settings_items()
            self.submenu_open = True
            self.submenu_sel = 0

        elif action == "Sleep":
            if self.world.room == "outdoor":
                self.show_pet_msg("Nooo!", 2.0)
            else:
                self.pet.toggle_sleep()
        elif action == "Medicine":
            if self.med_window_t > 0 and self.med_count >= 3:
                pass
            elif self.pet.give_medicine():
                if self.med_window_t <= 0:
                    self.med_window_t = 180.0
                    self.med_count = 0
                self.med_count += 1
                self._play_pills()
        elif action == "Clean":
            if self.pet.poops > 0:
                self.pet.clean()
                if self.pup_sound is not None:
                    try:
                        self.channel1.play(self.pup_sound)
                    except Exception:
                        pass
            else:
                self.show_pet_msg(random.choice(["?!", "o.O"]))
        elif action == "Light":
            if self.world.room == "outdoor":
                self.show_pet_msg(random.choice(["???", "I CAN'T DO THAT"]), 2.0)
            else:
                self.pet.light_on = not self.pet.light_on
        elif action == "Discipline":
            if (self.pet.age - getattr(self.pet, "_last_discipline", -1e9)
                    < LIMITS["discipline"]):
                self.pet.happiness = max(0.0, self.pet.happiness - 2)
                self.show_pet_msg("-.-'")
            else:
                self.pet.discipline_pet()
                self._play_whistle()
        elif action.startswith("Sound"):
            self.toggle_sound()
        elif action.startswith("Music"):
            self.toggle_music()
        elif action == "Out/In":
            self.world.room = ("outdoor" if self.world.room == "indoor" else "indoor")
            self.world.particles.clear()
            self.world.shooting_star = None
            if self.world.room == "outdoor":
                self.pet.light_on = True
        #elif action == "Notif-Test":
        #    self._schedule_pet_warning(40, "test")   # Variante B testen (Alarm in ~60s)
        #elif action == "Evolve-Test":
        #    self._schedule_alarm(10, "1. PseudoPet schlüpft!", "Test: Evolve-Notification in 10 Sekunden 🥚", ALARM_SLOT_EVOLVE)

    def _can_play_minigame(self):
        return (self.pet.state not in (STATE_DEAD, STATE_GHOST, STATE_HATCHING)
                and not self.pet.sleeping
                and self.pet.stage != STAGE_EGG
                and self.pet.choice_pending is None)

    def _minigame_timeout_active(self):
        return (self.pet.age
                - getattr(self.pet, "_last_minigame", -1e9)
                < LIMITS["minigame"])

    def exec_submenu(self):
        action = self.submenu_items[self.submenu_sel]
        # <<< NEU: Settings-Submenu abfangen, bevor die Spiele-Logik laeuft
        if self.submenu_kind == "settings":
            self._handle_settings(action)
            return
        if action == "Ball":
            play_limit = LIMITS.get("play", LIMITS.get("minigame", 60.0))
            on_timeout = (self.pet.age
                          - getattr(self.pet, "_last_play", -1e9) < play_limit)
            if (self.pet.state in (STATE_DEAD, STATE_GHOST, STATE_HATCHING)
                    or self.pet.stage == STAGE_EGG
                    or getattr(self.pet, "sleeping", False)):
                pass
            elif on_timeout:
                self.show_pet_msg("BORED!")
            else:
                self.pet._last_play = self.pet.age
                self.pet.play()
                self.start_roll(dur=1.2, direction=random.choice((-1, 1)))
                if self.play_sound:
                    self.channel3.play(self.play_sound)
        elif action == "Defense":
            if self._minigame_timeout_active():
                self.show_pet_msg("BORED!")
            elif self._can_play_minigame():
                self.minigame = MiniGameDefense(self.pet)
                self.minigame.shot_sounds = [s for s in (self.peng_sound,
                                                         self.pow_sound,
                                                         self.boom_sound)
                                             if s is not None]
                self.mode = "minigame"
        elif action == "SnackDrop":
            if self._minigame_timeout_active():
                self.show_pet_msg("BORED!")
            elif self._can_play_minigame():
                self.minigame = MiniGameSnack(self.pet)
                self.minigame.item_sounds = {"sock": self.peng_sound,
                                             "heart": self.pow_sound,
                                             "apple": self.boom_sound}
                self.mode = "minigame"

        elif action == "Fishing":
            if MiniGameFish is None:
                self.show_pet_msg("NO FISH!")
            elif self._minigame_timeout_active():
                self.show_pet_msg("BORED!")
            elif self._can_play_minigame():
                self.minigame = MiniGameFish(self.pet)
                self.minigame.bite_sound = self.peng_sound
                self.minigame.catch_sound = self.pow_sound
                self.minigame.junk_sound = self.boom_sound
                self.mode = "minigame"

        elif action == "Pong: AI":
            if self._minigame_timeout_active():
                self.show_pet_msg("BORED!")
            elif self._can_play_minigame():
                self.minigame = MiniGamePong(self.pet, mode="ai")
                self.mode = "minigame"

        elif action == "Pong: Host":
            if self._can_play_minigame():
                if not HAS_WEBSOCKETS:
                    self.show_pet_msg("NO WEBSOCKETS!")
                else:
                    self.minigame = MiniGamePong(self.pet, mode="host")
                    self.mode = "minigame"

        elif action == "Pong: Join":
            if self._can_play_minigame():
                if not HAS_WEBSOCKETS:
                    self.show_pet_msg("NO WEBSOCKETS!")
                else:
                    self.minigame = MiniGamePong(self.pet, mode="client")
                    self.mode = "minigame"

    def _handle_settings(self, label):
        if label.startswith("Sound"):
            self.toggle_sound()           # statt: self.sound_on = not self.sound_on
        elif label.startswith("Music"):
            self.toggle_music()           # statt: selbst togglen + start_bgm()
        elif label.startswith("Notifications"):
            self._toggle_notifications()
        self.submenu_items = self._settings_items()
        self.save()


    def _wake_up_pet(self):
        p = self.pet
        p.sleeping = False
        p.light_on = True
        p.calling = False
        if getattr(self, "kikiriki_sound", None) is not None:
            try:
                self.kikiriki_sound.play()
            except Exception:
                pass

    def handle_input(self, btn):
        if self.mode == "name":
            self.handle_name_input(btn)
        elif self.mode == "egg":
            self.handle_egg_select(btn)
        elif self.mode == "choice":
            self.handle_choice(btn)
        elif self.mode == "game":
            self.handle_game(btn)
        elif self.mode == "status":
            if btn in (1, 2):
                self.mode = "game"
                self.menu_open = False
                self.submenu_open = False
        elif self.mode == "minigame":
            self.handle_minigame(btn)
        elif self.mode == "offline":
            self.mode = "game"

    def to_virtual(self, pos):
        s = getattr(self, "present_scale", None)
        if s:
            x = int((pos[0] - self.display_x - self.present_off_x) / s)
            y = int((pos[1] - self.display_y - self.present_off_y) / s)
        else:
            x = (pos[0] - self.display_x) * VW // self.display_w
            y = (pos[1] - self.display_y) * VH // self.display_h
        return (max(0, min(VW - 1, x)),
                max(0, min(VH - 1, y)))

    def _button_zones(self):
        y = rh(245)
        h = rh(318) - y
        return [pygame.Rect(0, y, rw(81), h),
                pygame.Rect(rw(81), y, rw(77), h),
                pygame.Rect(rw(158), y, VW - rw(158), h)]

    def handle_touch(self, pos):
        mx, my = self.to_virtual(pos)
        for i, rect in enumerate(self._button_zones()):
            if rect.collidepoint((mx, my)):
                self.mouse_hold_btn = i
                self.handle_input(i)
                return
        self.mouse_hold_btn = None

    def save(self):
        if not self.pet:
            return
        pet_data = self.pet.to_dict()
        data = {"pet": pet_data, "saved_at": time.time(), "version": 4,
                "away_since": getattr(self, "_away_since", None),
                "room": self.world.room,
                "sound_on": self.sound_on,
                "music_on": self.music_on,
                "notifications_on": self.notifications_on,
                "last_notif": getattr(self, "_last_notif_time", 0.0)}
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self):
        if not os.path.exists(SAVE_FILE):
            return False
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            pet_data = data["pet"]
            if pet_data.get("state") == STATE_DEAD:
                self.delete_save()
                return False
            self._away_since = data.get("away_since")
            self.pet = Pet.from_dict(pet_data)
            self.world.particles.clear()
            room = data.get("room")
            if room in ("indoor", "outdoor"):
                self.world.room = room
                if room == "outdoor":
                    self.pet.light_on = True
            # <<< NEU: Sim-Voraussetzungen wiederherstellen
            self.pet.outdoor = (self.world.room == "outdoor")
            self.pet._world = self.world
            self.sound_on = bool(data.get("sound_on", True))
            self.music_on = bool(data.get("music_on", False))   # war True – Default soll aber AUS sein
            self.mode = "game"
            self.notifications_on = bool(data.get("notifications_on", True))
            saved_at = data.get("saved_at")
            self._last_notif_time = data.get("last_notif", 0.0)
            elapsed = (time.time() - saved_at) if saved_at else 0.0
            away = data.get("away_since")
            report_secs = (time.time() - away) if away else elapsed
            if (elapsed > 60
                    and self.pet.state not in (STATE_DEAD, STATE_GHOST)):
                gap = min(elapsed, OFFLINE_MAX)
                self.offline_report = self.pet.simulate_offline(gap)
                self.offline_report["secs"] = min(report_secs, OFFLINE_MAX)
                self.mode = "offline"
                print(f"[offline] {gap / 60:.0f} min simuliert")
                self.save()      # saved_at auffrischen -> keine Doppel-Sim
            return True
        except Exception as e:
            print(f"[load] Save-Fehler: {e}")
            return False

    def delete_save(self):
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)

    def try_load(self):
        if self.load():
            print("[PseudoPet] Save geladen!")
        else:
            print("[PseudoPet] Kein Save - neues Spiel")

    def _need_cooldown_ok(self):
        return time.time() - getattr(self, "_last_notif_time", 0.0) >= NOTIF_COOLDOWN

    def reset_game(self):
        self._cancel_pet_alarm()
        self._last_notif_time = 0.0
        self.delete_save()
        self.pet = None
        self.mode = "name"
        self.name_input = ""
        self.name_cursor = 0
        self.egg_sel = 0
        self.menu_open = False
        self.menu_sel = 0
        self.minigame = None
        self.world = World()
        self.offline_report = None
        self._wake_check_t = 0.0
        self._was_full_asleep = False
        self._was_sick = False
        self._sneeze_t = 0.0
        self.pet_msg = None
        self.pet_msg_t = 0.0
        self.submenu_open = False
        self.submenu_sel = 0
        self.last_save_time = 0.0
        self.evo_flash = 0.0
        self._last_branch = None
        self.evo_fx = None
        self._last_sprite_key = None
        self.butterfly = None
        self.butterfly_timer = random.uniform(30.0, 150.0)
        self.butterfly_fx = None

    def _predict_death_time(self):
        if not self.pet or self.pet.state in (STATE_DEAD, STATE_GHOST):
            return None, None
        p = self.pet
        decay = 0.0
        mercy = OFFLINE_MERCY
        stab  = 1.0 - STAGE_STABILITY.get(p.stage, 0.0)
        if p.hunger > STARVE_HUNGER:
            decay += HEALTH_DECAY_CRITICAL * stab * mercy
        if p.poops > 0:
            decay += POOP_HEALTH_DECAY * min(p.poops, POOP_HEALTH_CAP) * stab * mercy
        if p.sick:
            decay += SICK_HEALTH_DECAY * stab * mercy
        if p.energy < EXHAUST_ENERGY:
            decay += HEALTH_DECAY_CRITICAL * stab * mercy
        time_until_hunger = max(0, (STARVE_HUNGER - p.hunger) / HUNGER_DECAY_WAKE) if p.hunger < STARVE_HUNGER else 0
        if decay > 0:
            time_until_death = p.health / decay
            total_time = min(time_until_death, time_until_hunger + p.health / HEALTH_DECAY_CRITICAL)
            if total_time < DEATH_WARN_WINDOW:
                if p.sick:
                    return total_time, "sick"
                elif p.poops >= POOP_WARN:
                    return total_time, "poop"
                elif p.hunger > STARVE_HUNGER:
                    return total_time, "hungry"
                else:
                    return total_time, "happy"
        return None, None

    def _predict_evolve_time(self):
        if not self.pet or self.pet.state in (STATE_DEAD, STATE_GHOST):
            return None, None
        p = self.pet
        if p.choice_pending or p.state == STATE_HATCHING:
            return None, None
        stage_times = {
            STAGE_EGG:   (p.hatch_time, "hatch"),
            STAGE_BABY:  (p.baby_time,  "evolve"),
            STAGE_CHILD: (p.child_time, "evolve"),
            STAGE_TEEN:  (p.teen_time,  "evolve"),
        }
        entry = stage_times.get(p.stage)
        if entry is None:
            return None, None
        t_time, reason = entry
        remaining = t_time - p.stage_timer
        if remaining <= 0:
            return None, None
        return remaining, reason

    def _schedule_alarm(self, delay_secs, title, msg, req_code):
        if platform() != "android":
            return False
        if not getattr(self, "notifications_on", True):    # <<< GATE 2: ALLE Alarms
            return False
        try:
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            Intent = autoclass('android.content.Intent')
            PendingIntent = autoclass('android.app.PendingIntent')
            AlarmManager = autoclass('android.app.AlarmManager')
            SystemClock = autoclass('android.os.SystemClock')
            Bundle = autoclass('android.os.Bundle')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Receiver = autoclass('org.beezi.pseudopet.PetAlarmReceiver')
            context = PythonActivity.mActivity.getApplicationContext()
            i = Intent(context, Receiver)
            extras = Bundle()
            extras.putString("title", title)
            extras.putString("msg", msg)
            i.putExtras(extras)
            print("[notif] readback:", i.getStringExtra("title"),
                  "|", i.getStringExtra("msg"))
            pi = PendingIntent.getBroadcast(context, req_code, i,
                    PendingIntent.FLAG_CANCEL_CURRENT | PendingIntent.FLAG_IMMUTABLE)
            am = context.getSystemService(Context.ALARM_SERVICE)
            am.setAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP,
                    SystemClock.elapsedRealtime() + int(delay_secs) * 1000, pi)
            print(f"[notif] Alarm #{req_code} in {int(delay_secs)}s geplant")
            return True
        except Exception as e:
            print("[notif] Alarm-Fehler:", e)
            return False

    def _should_notify(self):
        if not getattr(self, 'notif_permitted', True):
            return False
        h = time.localtime().tm_hour
        if QUIET_HOUR_START <= h or h < QUIET_HOUR_END:
            return False
        last = getattr(self, '_last_notif_time', 0)
        return self._need_cooldown_ok()

    def _notify(self, title, msg):
        if not getattr(self, "notifications_on", True):
            return False
        try:
            if platform() == "android":
                android_notify(title, msg)
            else:
                from plyer import notification
                notification.notify(title=title, message=msg,
                                    app_name="PseudoPet", timeout=15)
            print(f"[notif] gesendet: {msg}")
            self._last_notif_time = time.time()   # ← Cooldown startet HIER
            return True
        except Exception as e:
            print(f"[notif] Fehler: {e}")
            return False

    def _toggle_notifications(self):
        self.notifications_on = not self.notifications_on
        if self.notifications_on:
            print("[notif] Notifications AKTIVIERT")
            if platform() == "android":
                try:
                    from android.permissions import check_permission
                    self.notif_permitted = check_permission(
                        "android.permission.POST_NOTIFICATIONS")
                except Exception:
                    self.notif_permitted = True
        else:
            print("[notif] Notifications DEAKTIVIERT - alle Alarms gecancelt")
            self._cancel_pet_alarm()

    def _schedule_pet_warning(self, secs, reason):
        warn_in = max(DEATH_WARN_MIN, int(secs) - DEATH_WARN_LEAD)
        msg = self._need_message(reason)
        title = self._notif_title()
        if not self._schedule_alarm(warn_in, title, msg, ALARM_SLOT_DEATH):
            self._notify(title, msg)

    def _schedule_evolve_warning(self):
        if platform() != "android":
            return
        if not getattr(self, "notif_permitted", True):
            return
        secs, reason = self._predict_evolve_time()
        if not secs:
            self._cancel_alarm_slot(ALARM_SLOT_EVOLVE)
            return
        if secs <= EVO_NOTIF_LEAD:
            msg = self._need_message(reason)
            title = NOTIF_HEADLINE.get(reason, NOTIF_HEADLINE["evolve"])
            self._notify(title, msg)
            self._last_notif_time = time.time()
            return
        warn_in = max(EVO_ALARM_MIN, int(secs) - EVO_NOTIF_LEAD)
        msg = self._need_message(reason)
        title = NOTIF_HEADLINE.get(reason, NOTIF_HEADLINE["evolve"])
        self._schedule_alarm(warn_in, title, msg, ALARM_SLOT_EVOLVE)

    def _notify_hungry(self):
        return self._notify(self._notif_title(), self._need_message("hungry"))

    def _notify_sick(self):
        return self._notify(self._notif_title(), self._need_message("sick"))

    def _notify_poop(self):
        return self._notify(self._notif_title(), self._need_message("poop"))

    def _notify_happy(self):
        return self._notify(self._notif_title(), self._need_message("happy"))

    def _notif_title(self):
        t = random.choice(NOTIFICATIONTITEL)
        return t.format(name=self.pet.name) if self.pet else t

    def _predict_hungry_time(self):
        p = self.pet
        if p.hunger >= HUNGER_WARN:
            return None
        stab = 1.0 - STAGE_STABILITY.get(p.stage, 0.0)
        if p.sleeping:
            rate = HUNGER_DECAY_SLEEP * stab * OFFLINE_MERCY
        else:
            rate = HUNGER_DECAY_WAKE * stab * OFFLINE_MERCY
        if rate <= 0:
            return None
        return (HUNGER_WARN - p.hunger) / rate

    def _predict_happy_time(self):
        p = self.pet
        if p.happiness <= HAPPY_WARN or p.sleeping:
            return None
        return (p.happiness - HAPPY_WARN) / (HAPPINESS_DECAY * OFFLINE_MERCY)

    def _predict_poop_time(self):
        p = self.pet
        if p.poops >= POOP_WARN or p.sleeping:
            return None
        if p.stage == STAGE_EGG or p.state == STATE_HATCHING:
            return None
        m = OFFLINE_MERCY
        stab = 1.0 - STAGE_STABILITY.get(p.stage, 0.0)
        wait = (POOP_WAIT_EXPECTED / max(0.5, stab)) * 1.6   # Varianz-Puffer
        gate_rest = max(0.0, (POOP_TIMER_GATE - p.poop_timer) / m)
        missing = POOP_WARN - p.poops
        return gate_rest + wait + ((POOP_TIMER_GATE / m) + wait) * (missing - 1)

    def _predict_sick_time(self):
        return None

    def _predict_next_need(self):
        p = self.pet
        if not p or p.state in (STATE_DEAD, STATE_GHOST) or p.choice_pending:
            return None
        best = None
        for fn, reason in ((self._predict_hungry_time, "hungry"),
                        (self._predict_poop_time,  "poop"),
                        (self._predict_happy_time, "happy")):
            secs = fn()
            if secs and secs > 0 and (best is None or secs < best[0]):
                best = (secs, reason)
        return best

    def _schedule_need_warning(self):
        if platform() != "android":
            return
        if not getattr(self, "notif_permitted", True):
            return
        res = self._predict_next_need()
        if not res:
            self._cancel_alarm_slot(ALARM_SLOT_NEED)
            return
        if not self._need_cooldown_ok():
            print(f"[notif] Need-Alarm unterdrueckt (Cooldown {NOTIF_COOLDOWN:.0f}s)")
            return
        secs, reason = res
        msg = self._need_message(reason)
        self._schedule_alarm(max(NEED_ALARM_MIN, int(secs)),
                            self._notif_title(), msg, ALARM_SLOT_NEED)
        # ← KEIN self._last_notif_time = time.time() mehr!

    def _cancel_pet_alarm(self):
        if platform() != "android":
            return
        try:
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            Intent = autoclass('android.content.Intent')
            PendingIntent = autoclass('android.app.PendingIntent')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Receiver = autoclass('org.beezi.pseudopet.PetAlarmReceiver')
            context = PythonActivity.mActivity.getApplicationContext()
            am = context.getSystemService(Context.ALARM_SERVICE)
            i = Intent(context, Receiver)
            for req_code in (ALARM_SLOT_DEATH, ALARM_SLOT_EVOLVE, ALARM_SLOT_NEED):
                pi = PendingIntent.getBroadcast(context, req_code, i,
                        PendingIntent.FLAG_NO_CREATE | PendingIntent.FLAG_IMMUTABLE)
                if pi is not None:
                    am.cancel(pi)
        except Exception as e:
            print("[notif] Cancel-Fehler:", e)

    def _send_test_notification(self):
        msg = "Test erfolgreich!" if LANG == "de" else "Test successful!"
        self._notify("PseudoPet", msg)

    def _pet_need_reason(self):
        p = self.pet
        if p.state in (STATE_DEAD, STATE_GHOST):
            return None
        if p.sick:          return "sick"
        if p.hunger > HUNGER_WARN: return "hungry"
        if p.poops >= POOP_WARN:  return "poop"
        if p.happiness < HAPPY_WARN or p.calling: return "happy"
        return None

    def _cancel_alarm_slot(self, req_code):
        if platform() != "android":
            return
        try:
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            Intent = autoclass('android.content.Intent')
            PendingIntent = autoclass('android.app.PendingIntent')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Receiver = autoclass('org.beezi.pseudopet.PetAlarmReceiver')
            context = PythonActivity.mActivity.getApplicationContext()
            i = Intent(context, Receiver)
            pi = PendingIntent.getBroadcast(context, req_code, i,
                    PendingIntent.FLAG_NO_CREATE | PendingIntent.FLAG_IMMUTABLE)
            if pi is not None:
                context.getSystemService(Context.ALARM_SERVICE).cancel(pi)
        except Exception as e:
            print("[notif] Slot-Cancel-Fehler:", e)

    def _schedule_death_warning(self):
            if not getattr(self, "notif_permitted", True):
                return
            secs, reason = self._predict_death_time()
            if secs and secs < DEATH_WARN_WINDOW:
                self._schedule_pet_warning(secs, reason)
            else:
                self._cancel_alarm_slot(ALARM_SLOT_DEATH)

    def close_submenu(self, to_menu=True):
        """Submenü schließen.
        Default: zurueck ins HAUPTMENÜ (beide Submenüs werden nur
        aus dem Hauptmenü geoeffnet, also ist das immer korrekt)."""
        self.submenu_open = False
        self.menu_open = bool(to_menu)

    def run(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.POST_NOTIFICATIONS,
                Permission.VIBRATE,
                Permission.WAKE_LOCK,
            ])
            print("[perm] Notification-Permission angefragt")
        except ImportError:
            print("[perm] Nicht auf Android - Permissions übersprungen")
        except Exception as e:
            print(f"[perm] Fehler beim Anfragen: {e}")
        running = True
        frame = 0
        print("[events] APP_BG:", APP_BG, "| APP_FG:", APP_FG,
            "| WINDOWFOCUSLOST:", getattr(pygame, "WINDOWFOCUSLOST", None))

        while running:
            dt = self.clock.tick(FPS) / 1000.0
            frame += 1
            if frame <= 2 or dt > 5.0:
                dt = min(dt, 1.0 / FPS)      # Startup/Resume: kein Live-Mega-dt
            if frame % 200 == 0:
                print(f"[loop] f{frame} active={pygame.display.get_active()} bg={self._in_background}")
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif AC_BACK is not None and event.key == AC_BACK:
                        if self.submenu_open:
                            self.submenu_open = False
                        elif self.menu_open:
                            self.menu_open = False
                        elif self.mode in ("status", "offline"):
                            self.mode = "game"
                        elif self.mode == "choice":
                            pass
                        elif self.mode == "minigame":
                            self.minigame = None
                            self.mode = "game"
                        elif self.mode == "game":
                            running = False
                    elif event.key in (pygame.K_a, pygame.K_LEFT):
                        self.handle_input(0)
                    elif event.key in (pygame.K_s, pygame.K_DOWN):
                        self.handle_input(1)
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        self.handle_input(2)
                    if event.key == pygame.K_F10:
                        self._send_test_notification()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.mouse_down = True
                        self.handle_touch(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.mouse_down = False
                        self.mouse_hold_btn = None
                elif event.type == APP_BG:
                    print("DEBUG: PseudoPet is now in BG-status")
                    self.mouse_down = False
                    self.mouse_hold_btn = None

                if WL is not None and event.type == WL:
                    print("[lifecycle] FOCUSLOST-Event | get_active:", pygame.display.get_active())
                    self._enter_background()
                if WG is not None and event.type == WG:
                    print("[lifecycle] FOCUSGAINED-Event")
                    self._enter_foreground()
                if APP_BG is not None and event.type == APP_BG:
                    self._enter_background()
                if APP_FG is not None and event.type == APP_FG:
                    self._enter_foreground()

            self._scroll_repeat(dt)
            if (self.mode == "game" and not self.menu_open
                    and not self.submenu_open):
                kp = pygame.key.get_pressed()
                c_held = bool(kp[pygame.K_d] or kp[pygame.K_RIGHT]
                              or (self.mouse_down and self.mouse_hold_btn == 2))
            else:
                c_held = False
            if c_held:
                self._quit_hold_t += min(dt, 0.25)
                if self._quit_hold_t >= 2.0:
                    running = False
            else:
                self._quit_hold_t = 0.0
            if dt > OFFLINE_DT_MIN and frame > 2:
                if self.pet and self.pet.state not in (STATE_DEAD, STATE_GHOST):
                    report = self.pet.simulate_offline(dt)     # Zustand: nur der echte Gap
                    if self._away_since is not None:
                        total = min(time.time() - self._away_since, OFFLINE_MAX)
                        report["secs"] = total                 # Report: volle Abwesenheit
                        report["hours"] = round(total / 3600, 1)
                    self.offline_report = report
                    if report["secs"] >= OFFLINE_MIN_REPORT:   # kein Popup bei Mini-Gaps
                        self.mode = "offline"
                    self._away_since = None
                    self.save()
                dt = 0.1
            elif dt > OFFLINE_DT_MIN:
                dt = 0.1
            self.fly_t += dt
            self.world._in_minigame = (self.mode == "minigame")
            self.world._ambient_muted = not self._ambient_sound_allowed()
            self.world.update(dt)
            self.update_butterfly(dt)
            self.update_evolution_fx(dt)
            if self.butterfly_fx is not None:
                self.butterfly_fx["t"] -= dt
                if self.butterfly_fx["t"] <= 0.0:
                    self.butterfly_fx = None
            if self.pet_cooldown > 0:
                self.pet_cooldown -= dt
            if self.med_window_t > 0:
                self.med_window_t -= dt
            if self.med_window_t <= 0:
                self.med_window_t = 0.0
                self.med_count = 0
            if self.pet_window_t > 0:
                self.pet_window_t -= dt
                if self.pet_window_t <= 0:
                    self.pet_window_t = 0.0
                    self.pet_strokes = 0
            if self.petting > 0:
                self.petting -= dt
            if getattr(self, "roll_t", 0) > 0:
                self.roll_t -= dt
                if self.roll_t <= 0:
                    self.roll_t = 0.0
            if self.evo_flash > 0:
                self.evo_flash -= dt
            if self.pet_msg_t > 0:
                self.pet_msg_t -= dt
                if self.pet_msg_t <= 0:
                    self.pet_msg = None

            if self.mode == "minigame" and self.minigame:
                self.minigame.update(dt)
            elif self.mode == "choice" and self.pet:
                self.pet.tick_anim(dt)
            elif self.pet and self.mode in ("game", "status"):
                self.pet.update(dt)
                self.world.apply_effects(self.pet, dt)
                if (self.pet.calling and not self.pet.sick
                        and not self.pet.poop_played
                        and self.pet.state != STATE_HATCHING):
                    # Beduerfnis-Ruf: kikiriki statt Furz-Sound
                    if self.kikiriki_sound is not None:
                        try:
                            self.kikiriki_sound.play()
                        except Exception:
                            pass
                    self.pet.poop_played = True
                if self.pet.sick:
                    if not self._was_sick:
                        self._was_sick = True
                        self._sneeze_t = 30.0
                        if self.hust_sound is not None:
                            try:
                                self.hust_sound.play()
                            except Exception:
                                pass
                    else:
                        self._sneeze_t -= dt
                        if self._sneeze_t <= 0.0:
                            self._sneeze_t = 30.0
                            if self.sneeze_sound is not None:
                                try:
                                    self.sneeze_sound.play()
                                    print("[sick] sneeze gespielt")
                                except Exception:
                                    pass
                else:
                    self._was_sick = False
                    self._sneeze_t = 0.0

                if (not self.pet.sleeping
                        and getattr(self, "roll_t", 0) <= 0
                        and self.pet.happiness >= 92
                        and self.pet.age - getattr(self.pet, "_last_roll", -1e9) > 25.0):
                    if random.random() < 0.12 * dt:
                        self.pet._last_roll = self.pet.age
                        self.start_roll(dur=1.3,
                                        direction=random.choice((-1, 1)),
                                        mode="tumble")

                if self.pet.just_hatched:
                    self.pet.just_hatched = False
                    if self.pet.choice_pending is None and self.kikiriki_sound:
                        try:
                            self.kikiriki_sound.play()
                        except Exception:
                            pass
                if self.pet is not None and getattr(self.pet, "just_woke", False):
                    self.pet.just_woke = False
                    if self.kikiriki_sound is not None:
                        try:
                            self.kikiriki_sound.play()
                        except Exception:
                            pass
            if (self.pet and self.pet.state in (STATE_DEAD, STATE_GHOST)
                    and (self.menu_open or self.submenu_open)):
                self.menu_open = False
                self.submenu_open = False

            if (self.pet and self.pet.choice_pending is not None
                    and self.mode == "game"):
                nxt = self.pet.choice_pending["next"]
                keys = self.pet.branch_group
                self.choice_options = [(k, EVOLUTION_BRANCHES[k][nxt]) for k in keys]
                self.choice_sel = 0
                self.mode = "choice"
            if self.pet:
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
                self._last_sprite_key = cur_sprite
            if self.pet and self.pet.state not in (STATE_DEAD, STATE_GHOST):
                self.last_save_time += dt
                if self.last_save_time >= AUTOSAVE_INTERVAL:
                    self.save()
                    self.last_save_time = 0.0
            self.draw()
        if self.pet and self.pet.state not in (STATE_DEAD, STATE_GHOST):
            self.save()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    Game().run()
