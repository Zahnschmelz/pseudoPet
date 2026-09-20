LIMITS = {
    "minigame": 15.0,       # Minigame-Cooldown (s)
    "discipline": 30.0,     # Disziplin-Abstand (s)
    "medicine": 20.0,       # Medizin-Fenster (s)
}

REPEAT_DELAY = 0.35     # A: halten/hold verzögerung
REPEAT_RATE  = 0.12     # A: halten/hold Rate
BLACK = (0, 0, 0)
WHITE = (238, 230, 220)
GRAY = (128, 128, 128)
DARK_GRAY = (32, 32, 32)
STAGE_EGG = "egg"
STAGE_BABY = "baby"
STAGE_CHILD = "child"
STAGE_TEEN = "teen"
STAGE_ADULT = "adult"
STAGE_PREMIUM = "premium"
STATE_IDLE = "idle"
STATE_EATING = "eating"
STATE_PLAYING = "playing"
STATE_SLEEPING = "sleeping"
STATE_SICK = "sick"
STATE_DEAD = "dead"
STATE_GHOST = "ghost"
STATE_HATCHING = "hatching"
OFFLINE_MERCY = 0.19    # offline multipier
OFFLINE_MAX = 24 * 3600 # 24h
OFFLINE_MIN_REPORT = 15.0   # Report erst ab dieser Abwesenheit anzeigen (sec)
OFFLINE_DT_MIN     = 7.0   # darunter: normaler Ruckler, kein Offline-Pfad (sec)

# ============================================================
# SPIEL-BALANCE — zentral einstellbar
# Raten = Punkte/Sekunde, Zeiten = Sekunden.
# Offline: update() multipliziert Raten mit OFFLINE_MERCY.
# ============================================================

# --- Grund-Raten ---
HUNGER_DECAY_WAKE    = 0.1      # Hunger-Wert steigt pro s (wach); 0 -> 77 dauert ~13 min
HUNGER_DECAY_SLEEP   = 0.04     # Hunger-Zuwachs im Schlaf (wirkt OHNE Offline-Mercy!)
HAPPINESS_DECAY      = 0.08     # Glück sinkt pro s (wach); 100 -> 30 dauert ~15 min
ENERGY_DECAY_WAKE    = 0.06     # Energie sinkt pro s (wach); 100 -> 20 dauert ~22 min
ENERGY_REGEN_SLEEP   = 0.25     # Energie WÄCHST im Schlaf (kein Decay!)
DISCIPLINE_DECAY     = 0.03     # Disziplin schwindet pro s; Ermahnung gibt +20
OVERFEED_THRESHOLD   = 25.0
OVERFEED_SICK_THRESHOLD = 5.0
OVERFEED_SICK_CHANCE = 0.10

# --- Heilung --- # Heilt nur, wenn: NICHT krank UND hunger < HEAL_HUNGER_MAX UND energy > HEAL_ENERGY_MIN
HEAL_HUNGER_MAX      = 50.0     # Regeneration nur solange Hunger DARUNTER
HEAL_ENERGY_MIN      = 50.0     # Regeneration nur solange Energie DARÜBER
HEAL_HAPPY_MIN       = 65.0     # ab diesem Glück greift die schnellere Rate
HEAL_RATE_WAKE       = 0.19     # +HP/s wach & unglücklich
HEAL_RATE_WAKE_HAPPY = 0.35     # +HP/s wach & glücklich
HEAL_RATE_SLEEP      = 0.25     # +HP/s schlafend & unglücklich
HEAL_RATE_SLEEP_HAPPY= 0.45     # +HP/s schlafend & glücklich

# --- Gefahren ---
STARVE_HUNGER        = 77.0     # ab hier (hunger > X) verliert das Pet Gesundheit
EXHAUST_ENERGY       = 20.0     # darunter: Health-Verlust UND Krankheits-Risiko
HEALTH_DECAY_CRITICAL= 0.18     # HP-Verlust/s bei Verhungern/Erschöpfung; 100 HP -> 0 in ~9 min
POOP_HEALTH_DECAY    = 0.05     # HP-Verlust/s pro gewertetem Haufen...
POOP_HEALTH_CAP      = 3        # ...maximal so viele Haufen zählen (nur für HP)
POOP_HAPPINESS_DECAY = 0.15     # Glücksverlust/s pro Haufen (alle, ungecapped)
SICK_ENERGY          = 20.0     # unter dieser Energie wird das Pet anfällig
SICK_CHANCE          = 0.012    # ~1% pro Sekunde, solange Energie darunter
SICK_HEALTH_DECAY    = 0.055    # HP-Verlust/s solange krank
SICK_HAPPINESS_DECAY = 0.05     # Glücksverlust/s solange krank
# --- Outdoor-Krankheit (Regen) ---
OUTDOOR_SICK_INTERVAL = 17.0   # s Outdoor-Regen bis zum naechsten Wurf
OUTDOOR_SICK_CHANCE   = 0.05   # Chance pro Wurf (3 %)
SNOW_SICK_INTERVAL    = 15.0   # s Outdoor-Schnee bis zum naechsten Wurf
SNOW_SICK_CHANCE      = 0.07   # Chance pro Wurf (7 %)

OFFLINE_HEALTH_FLOOR = 14.0     # offline stirbt das Pet NICHT: HP -> 10 + wird krank
GHOST_TIME           = 12.0     # Sekunden als Geist, dann endgültig DEAD (Save wird gelöscht)

# --- Poop ---
POOP_TIMER_GATE      = 150.0    # Poop-Uhr läuft erst X s, bevor die Spawn-Chance startet
POOP_CHANCE          = 0.023    # Spawn-Chance pro s (2.3%) nach dem Gate
POOP_MAX             = 12       # maximal so viele Haufen gleichzeitig (werden gezeichnet)
POOP_WAIT_EXPECTED   = 1.0 / POOP_CHANCE # ~40s Erwartungswert

# --- Calling ---
CALL_HUNGER          = 75.0     # ruft, wenn Hunger DARÜBER steigt
CALL_HAPPINESS       = 25.0     # ruft, wenn Glück DARUNTER fällt
CALL_ENERGY          = 15.0     # ruft, wenn Energie DARUNTER fällt
CALL_DELAY           = 13.0     # Bedürfnis muss X s anliegen -> verhindert Flackern

# --- Notifications ---
HUNGER_WARN          = STARVE_HUNGER # Hunger-Schwelle für Warnung (bewusst = STARVE_HUNGER)
HAPPY_WARN           = 30.0     # liegt ÜBER CALL_HAPPINESS -> meldet, bevor das Pet zu rufen beginnt
POOP_WARN            = 3        # ab dem wievielten Haufen benachrichtigen
EVO_NOTIF_LEAD       = 55       # Sekunden VOR Schlüpfen/Evolution benachrichtigen
EVO_ALARM_MIN        = 3        # Mindest-Delay Evolve-Alarm
DEATH_WARN_LEAD      = 300      # 5 min vor kritischem Zustand
DEATH_WARN_MIN       = 60       # Todes-Warnung nie früher als X s geplant (Anti-Spam)
DEATH_WARN_WINDOW    = 1800.0   # nur planen, wenn Tod < 30 min droht
NEED_ALARM_MIN       = 10       # Mindest-Delay Need-Alarm (ersetzt das max(10, ...))
OFFLINE_CHUNK        = 10.0     # Sim-Schritt in simulate_offline
NOTIF_COOLDOWN       = 300.0    # 5 min: Mindestabstand fuer Need-Notifications

# --- Notification-Ruhezeit (_should_notify) ---
QUIET_HOUR_START     = 23        # ab 12 Uhr keine sofortigen Bedürfnis-Meldungen
QUIET_HOUR_END       = 6        # wieder ab 6 Uhr (Evolve-Alarm umgeht das bewusst)

# --- Alarm-Slots (PendingIntent-RequestCodes; pro Alarm-Typ EINDEUTIG nötig) ---
ALARM_SLOT_DEATH     = 4242     # Todes-Warnung
ALARM_SLOT_EVOLVE    = 4243     # Schlüpfen / Evolution
ALARM_SLOT_NEED      = 4244     # nächstes Bedürfnis

# --- Tageszeit ---
HOUR_DAY_START       = 7        # 07:00 -> Tag
HOUR_DAY_END         = 18       # 18:00 -> Abenddunkel
HOUR_NIGHT_START     = 20       # 20:00 -> Nacht
HOUR_NIGHT_END       = 5        # 05:00 -> Morgendunkel

HATCH_CHOICES = {
    "dot":    ("spike", "flame"),
    "stripe": ("stripe", "leaf"),
    "clean":  ("clean", "aqua"),
}

EGG_GROUPS = {
    "dot":    (("spike", "flame"), ("imp",   "volt")),
    "stripe": (("stripe", "leaf"), ("nova",  "nimbus")),
    "clean":  (("clean",  "aqua"), ("blop",  "plush")),
}

DARK_THRESHOLD = 0.60
DARK_ADULT_MIN = 60.0

CHOICE_REQUIRE_RULE = False


BRANCH_RULES = {
    "flame": lambda p: p.play_count  >= 8 and p.energy > 50,
    "leaf":  lambda p: p.feed_count  >= 10 and p.weight < 46,
    "aqua":  lambda p: p.clean_count >= 6 and p.sick_count == 0,
}
FORM_NAMES = {
    "dot": "SPIKE", "spike": "SPIKE", "stripe": "STRIPE", "clean": "CLEAN",
    "flame": "FLAME", "leaf": "LEAF", "aqua": "AQUA", "dark": "DARK",
    "imp": "IMP", "volt": "VOLT", "nova": "NOVA", "nimbus": "NIMBUS",
    "blop": "BLOP", "plush": "PLUSH",
}

EVOLUTION_BRANCHES = {
    "dot": {
        STAGE_BABY: "spike_baby", STAGE_CHILD: "spike_child",
        STAGE_TEEN: "spike_teen", STAGE_ADULT: "spike_adult",
        STAGE_PREMIUM: "spike_premium",
    },
    "stripe": {
        STAGE_BABY: "stripe_baby", STAGE_CHILD: "stripe_child",
        STAGE_TEEN: "stripe_teen", STAGE_ADULT: "stripe_adult",
        STAGE_PREMIUM: "stripe_premium",
    },
    "clean": {
        STAGE_BABY: "clean_baby", STAGE_CHILD: "clean_child",
        STAGE_TEEN: "clean_teen", STAGE_ADULT: "clean_adult",
        STAGE_PREMIUM: "clean_premium",
    },
    "dark": {
        STAGE_BABY: "dark_baby", STAGE_CHILD: "dark_child",
        STAGE_TEEN: "dark_teen", STAGE_ADULT: "dark_adult",
        STAGE_PREMIUM: "dark_premium",
    },
    "flame": {
        STAGE_BABY: "flame_baby", STAGE_CHILD: "flame_child",
        STAGE_TEEN: "flame_teen", STAGE_ADULT: "flame_adult",
        STAGE_PREMIUM: "flame_premium",
    },
    "leaf": {
        STAGE_BABY: "leaf_baby", STAGE_CHILD: "leaf_child",
        STAGE_TEEN: "leaf_teen", STAGE_ADULT: "leaf_adult",
        STAGE_PREMIUM: "leaf_premium",
    },
    "aqua": {
        STAGE_BABY: "aqua_baby", STAGE_CHILD: "aqua_child",
        STAGE_TEEN: "aqua_teen", STAGE_ADULT: "aqua_adult",
        STAGE_PREMIUM: "aqua_premium",
    },
    "imp": {
        STAGE_BABY: "imp_baby", STAGE_CHILD: "imp_child",
        STAGE_TEEN: "imp_teen", STAGE_ADULT: "imp_adult",
        STAGE_PREMIUM: "imp_premium",
    },
    "volt": {
        STAGE_BABY: "volt_baby", STAGE_CHILD: "volt_child",
        STAGE_TEEN: "volt_teen", STAGE_ADULT: "volt_adult",
        STAGE_PREMIUM: "volt_premium",
    },
    "nova": {
        STAGE_BABY: "nova_baby", STAGE_CHILD: "nova_child",
        STAGE_TEEN: "nova_teen", STAGE_ADULT: "nova_adult",
        STAGE_PREMIUM: "nova_premium",
    },
    "nimbus": {
        STAGE_BABY: "nimbus_baby", STAGE_CHILD: "nimbus_child",
        STAGE_TEEN: "nimbus_teen", STAGE_ADULT: "nimbus_adult",
        STAGE_PREMIUM: "nimbus_premium",
    },
    "blop": {
        STAGE_BABY: "blop_baby", STAGE_CHILD: "blop_child",
        STAGE_TEEN: "blop_teen", STAGE_ADULT: "blop_adult",
        STAGE_PREMIUM: "blop_premium",
    },
    "plush": {
        STAGE_BABY: "plush_baby", STAGE_CHILD: "plush_child",
        STAGE_TEEN: "plush_teen", STAGE_ADULT: "plush_adult",
        STAGE_PREMIUM: "plush_premium",
    },
}

# NAME FIX
EVOLUTION_BRANCHES["spike"] = EVOLUTION_BRANCHES["dot"]


# ============================================================
# SPRACHE / LANGUAGE  — alles außer "de" -> Englisch
# ============================================================
LANG_FALLBACK = "en"   # wird genutzt, falls Erkennung fehlschlägt

MESSAGES_DE = {
    "hungry": [
        "{name} hat sooo viel Hunger... 🍎",
        "{name} denkt ans Essen... 🤤",
        "Fütter {name}, sonst wird's traurig!",
        "{name}s Magen knurrt ganz laut! 🥣",
        "Food-Emergency! {name} braucht dringend was zu beißen! 🚨",
        "Kein Food für {name}? Oh no, Hunger-Modus aktiviert! 😱",
    ],
    "sick": [
        "{name} fühlt sich gar nicht gut... 🤒",
        "Medizin für {name} wäre jetzt super!",
        "{name} fühlt sich ein bisschen matschig... 🤒",
        "Hilfe! {name} braucht dringend Medizin! 🆘💊",
        "Schnell! {name} fühlt sich gar nicht gut! 🤒⚠️",
    ],
    "poop": [
        "Ih! {name} sitzt im Dreck 💩",
        "{name} braucht ein sauberes Zuhause! 💩",
        "{name} hat Kaka gemacht 🧻",
        "{name} hat ein kleines Geschenk hinterlassen! 💩",
        "Oh, ein kleiner Kaka-Moment für {name}! 💩",
        "{name}: \"hab Kaka und Pipi geamcht!\" 🚽",
        "Es riecht nach {name}... Oh nein! 👃💩",
        "💩-Alert! {name} hat mal wieder geliefert!",
    ],
    "happy": [
        "{name} wartet auf dich ❤️",
        "Kommst du bald zurück zu {name}?",
        "{name} vermisst dich gerade total! 🥺",
        "Hey! {name} wartet auf ein bisschen Action! 🎮",
        "{name} ist lonely... Zeit für ein bisschen Quality-Time! 👋",
    ],
    "hatch": [
        "{name} ist gleich da! Das Ei wackelt schon... 🥚✨",
        "Ganz kurz noch – {name} schlüpft! 🐣",
        "Psst! {name} macht sich auf den Weg... 🥚",
        "Das Ei vibriert schon... {name} ist fast da! 🥚💥",
        "Crack! {name} bricht gleich aus dem Ei aus! 🐣",
        "Ready or not, {name} kommt gleich zur Welt! 🐣✨",
    ],
    "evolve": [
        "{name} strahlt – die Entwicklung beginnt gleich! ✨ Komm schnell!",
        "Komm zurück! {name} verwandelt sich gleich! ✨",
        "{name} steht an der Schwelle zum nächsten Schritt! ✨",
        "Level up! {name} wird gerade ganz anders... ✨",
        "Achtung! {name} bekommt gerade ein krasses Upgrade! 🚀✨",
        "{name} überschlägt sich... Evolution läuft! 🧬✨",
    ],
}

NOTIFICATIONTITEL_DE = [
    "PseudoPet braucht dich!",
    "{name} braucht dich!",
    "Kommst du bald zurück?",
    "{name} wartet auf dich!",
    "Psst... {name} denkt an dich!",
    "Zeit für PseudoPet!",
    "Hallo von {name}! 👋",
]

# feste Headlines (Evolve-Alarm) — waren bisher hart auf Deutsch in main.py
NOTIF_HEADLINE_DE = {
    "hatch":  "PseudoPet schlüpft!",
    "evolve": "PseudoPet entwickelt sich!",
}

MESSAGES_EN = {
    "hungry": [
        "{name} is sooo hungry... 🍎",
        "{name} is thinking about food... 🤤",
        "Feed {name}, or it'll get sad!",
        "{name}'s tummy is growling loudly! 🥣",
        "Food emergency! {name} urgently needs something to munch! 🚨",
        "No food for {name}? Oh no, hunger mode activated! 😱",
    ],
    "sick": [
        "{name} isn't feeling well at all... 🤒",
        "Some medicine for {name} would be great right now!",
        "{name} feels a bit mushy... 🤒",
        "Help! {name} urgently needs medicine! 🆘💊",
        "Quick! {name} isn't feeling well at all! 🤒️",
    ],
    "poop": [
        "Yuck! {name} is sitting in the dirt 💩",
        "{name} needs a clean home! 💩",
        "{name} made a poop 🧻",
        "{name} left a little present behind! 💩",
        "Oh, a little poop moment for {name}! 💩",
        "{name}: \"I did a poop and a wee!\" 🚽",
        "It smells like {name}... Oh no! 👃💩",
        "💩-Alert! {name} delivered again!",
    ],
    "happy": [
        "{name} is waiting for you ❤️",
        "Will you come back to {name} soon?",
        "{name} misses you so much right now! 🥺",
        "Hey! {name} is waiting for a bit of action! 🎮",
        "{name} is lonely... Time for some quality time! 👋",
    ],
    "hatch": [
        "{name} is almost here! The egg is already wiggling... 🥚✨",
        "Just a moment longer – {name} is hatching! 🐣",
        "Psst! {name} is on its way... 🥚",
        "The egg is already vibrating... {name} is almost here! 🥚💥",
        "Crack! {name} is about to break out of the egg! 🐣",
        "Ready or not, {name} is about to be born! 🐣✨",
    ],
    "evolve": [
        "{name} is glowing – the evolution starts any moment! ✨ Come quick!",
        "Come back! {name} is about to transform! ✨",
        "{name} is standing at the threshold of the next step! ✨",
        "Level up! {name} is changing into something new... ✨",
        "Watch out! {name} is getting an awesome upgrade right now! 🚀✨",
        "{name} is going crazy... Evolution in progress! 🧬✨",
    ],
}

NOTIFICATIONTITEL_EN = [
    "PseudoPet needs you!",
    "{name} needs you!",
    "Will you be back soon?",
    "{name} is waiting for you!",
    "Psst... {name} is thinking of you!",
    "Time for PseudoPet!",
    "Hello from {name}! 👋",
]

NOTIF_HEADLINE_EN = {
    "hatch":  "PseudoPet is hatching!",
    "evolve": "PseudoPet is evolving!",
}

# --- aktiver Textsatz (Default DE, main.py schaltet um) ---
MESSAGES = MESSAGES_DE
NOTIFICATIONTITEL = NOTIFICATIONTITEL_DE
NOTIF_HEADLINE = NOTIF_HEADLINE_DE



# ============================================================
# STAGE-STABILITY: aeltere Pets sind moderat stabiler.
# Wert = Bonus (0.05 = 5 % weniger Decay / Poop-Chance).
# Wirkt in Pet.update() auf: Hunger-Anstieg, Health-Decay
# (kritisch/poop/sick) und POOP_CHANCE. Offline-Sim inklusive.
# ============================================================
STAGE_STABILITY = {
    STAGE_EGG:     0.00,   # Ei: kein Bonus
    STAGE_BABY:    0.00,   # Baby: volle Pflege noetig
    STAGE_CHILD:   0.04,   # Child:  5 % stabiler
    STAGE_TEEN:    0.06,   # Teen:   9 % stabiler
    STAGE_ADULT:   0.08,   # Adult: 12 % stabiler
    STAGE_PREMIUM: 0.10,   # Premium: 15 % stabiler
}
