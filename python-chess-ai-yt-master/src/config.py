import pygame
import os

from sound import Sound
from theme import Theme

_HERE = os.path.dirname(os.path.abspath(__file__))

class Config:

    def __init__(self):
        self.themes = []
        self._add_themes()
        self.idx = 0
        self.theme = self.themes[self.idx]
        self.font = pygame.font.SysFont('monospace', 18, bold=True)
        self.move_sound = Sound(
            os.path.join(_HERE, 'assets', 'sounds', 'move.wav'))
        self.capture_sound = Sound(
            os.path.join(_HERE, 'assets', 'sounds', 'capture.wav'))

    def change_theme(self):
        self.idx += 1
        self.idx %= len(self.themes)
        self.theme = self.themes[self.idx]

    def _add_themes(self):
        green = Theme((234, 235, 200), (119, 154, 88), (244, 247, 116), (172, 195, 51), '#C86464', '#C84646')
        brown = Theme((235, 209, 166), (165, 117, 80), (245, 234, 100), (209, 185, 59), '#C86464', '#C84646')
        blue  = Theme((229, 228, 200), (60, 95, 135), (123, 187, 227), (43, 119, 191), '#C86464', '#C84646')
        gray  = Theme((120, 119, 118), (86, 85, 84), (99, 126, 143), (82, 102, 128), '#C86464', '#C84646')
        miku  = Theme((220, 245, 243), (57,  197, 187), (167, 235, 210), (32,  178, 160), '#C86464', '#C84646')

        self.themes = [green, brown, blue, gray, miku]