# pixelfont.py — 3x5-Bitmap-Font als pygame.Font-Ersatz
import pygame

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
    "6": (0b011, 0b100, 0b111, 0b101, 0b111), "7": (0b111, 0b001, 0b001, 0b010, 0b010),
    "8": (0b111, 0b101, 0b111, 0b101, 0b111), "9": (0b111, 0b101, 0b111, 0b001, 0b110),
    " ": (    0,     0,     0,     0,     0), ".": (    0,     0,     0,     0, 0b010),
    "!": (0b010, 0b010, 0b010,     0, 0b010), ":": (    0, 0b010,     0, 0b010,     0),
    "=": (    0, 0b111,     0, 0b111,     0), "-": (    0,     0, 0b111,     0,     0),
    "+": (    0, 0b010, 0b111, 0b010,     0), "*": (0b101, 0b010, 0b101,     0,     0),
    ",": (    0,     0,     0, 0b010, 0b100), "?": (0b110, 0b001, 0b010,     0, 0b010),
    "%": (0b101, 0b001, 0b010, 0b100, 0b101), "♥": (0b101, 0b010, 0b101,     0,     0),
    "(": (0b010, 0b100, 0b100, 0b100, 0b010), "/": (0b001, 0b010, 0b010, 0b100, 0b100),
    ")": (0b010, 0b001, 0b001, 0b001, 0b010),"\\": (0b100, 0b010, 0b010, 0b001, 0b001),
    "<": (0b001, 0b010, 0b100, 0b010, 0b001), ">": (0b100, 0b010, 0b001, 0b010, 0b100),
    "_": (    0,     0,     0,     0, 0b111), "[": (0b111, 0b100, 0b100, 0b100, 0b111),
    "]": (0b111, 0b001, 0b001, 0b001, 0b111),
}

_UNK = (0, 0, 0, 0, 0b010)   # unbekanntes Zeichen -> kleiner Punkt
_UML = {"Ä": "AE", "Ö": "OE", "Ü": "UE", "[": "(", "]": ")",
        "ä": "AE", "ö": "OE", "ü": "UE", "ß": "SS"}

def normalize(text):
    out = []
    for ch in str(text):
        out.append(_UML.get(ch) or ch.upper())
    return "".join(out)

def text_w(text, scale=1):
    return (4 * len(normalize(text)) - 1) * scale

def draw_text(surf, txt, x, y, color, scale=1):
    """Direkt auf eine Surface zeichnen (ohne render-Umweg)."""
    x, y = int(x), int(y)
    for ch in normalize(txt):
        for r, bits in enumerate(FONT.get(ch, _UNK)):
            for c in range(3):
                if bits & (4 >> c):
                    surf.fill(color, (x + c * scale, y + r * scale, scale, scale))
        x += 4 * scale

class PixelFont:
    """Drop-in-Ersatz fuer pygame.font.SysFont.
    render(text, True, color) -> Surface (transparent, gecacht!).
    Gecachte Surfaces nur blitten, nicht veraendern."""
    def __init__(self, scale=1):
        self.scale = scale
        self.height = 5 * scale
        self._cache = {}

    def render(self, text, antialias=True, color=(255, 255, 255)):
        key = (str(text), tuple(color), self.scale)
        s = self._cache.get(key)
        if s is None:
            s = pygame.Surface((max(1, text_w(text, self.scale)), self.height),
                               pygame.SRCALPHA)
            draw_text(s, str(text), 0, 0, color, self.scale)
            self._cache[key] = s
        return s

    def size(self, text):
        return (max(1, text_w(text, self.scale)), self.height)

    def get_height(self):
        return self.height
