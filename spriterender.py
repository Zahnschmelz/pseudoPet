import pygame
from sprites import SPRITES

_SPRITE_CACHE = {}

def validate_sprites():
    ok = True
    for key, rows in SPRITES.items():
        widths = {len(r) for r in rows}
        if len(widths) > 1:
            print(f"[WARN] Sprite '{key}' ungleiche Zeilenlaengen: {sorted(widths)}")
            ok = False
    return ok

def _build_sprite_base(key, color):
    rows = SPRITES[key]
    h = len(rows)
    w = max(len(r) for r in rows)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in "X-*/\\":
                surf.set_at((x, y), color)
            elif ch == "O" and (x + y) % 2 == 0:
                surf.set_at((x, y), color)
    return surf

def make_sprite_surface(key, scale, color, rot=0, flipx=False, flipy=False):
    scale = max(1, int(round(scale)))
    rot = int(round(rot)) % 360
    ck = (key, scale, color, rot, bool(flipx), bool(flipy))
    if ck in _SPRITE_CACHE:
        return _SPRITE_CACHE[ck]

    base = _build_sprite_base(key, color)
    if flipx or flipy:
        base = pygame.transform.flip(base, flipx, flipy)
    if rot:
        base = pygame.transform.rotate(base, rot)

    surf = pygame.transform.scale(base, (base.get_width() * scale, base.get_height() * scale))
    _SPRITE_CACHE[ck] = surf
    return surf
