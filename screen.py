# screen.py — Design-Aufloesung + Skalierungs-Helfer
import pygame

DW, DH = 240, 320
VW, VH = DW, DH

def rw(x):  return int(round(x * VW / DW))
def rh(y):  return int(round(y * VH / DH))
def rs(n):  return max(1, int(round(n * VH / DH)))
def rp(x, y):   return (rw(x), rh(y))
def rrect(x, y, w, h): return pygame.Rect(rw(x), rh(y), rw(w), rh(h))
def rwf(x): return x * VW / DW
def rhf(y): return y * VH / DH
