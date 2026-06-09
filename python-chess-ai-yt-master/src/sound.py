import pygame
import os

class Sound:
    def __init__(self, path):
        self.path = path
        try:
            pygame.mixer.init()
            self.sound = pygame.mixer.Sound(path)
        except Exception:
            self.sound = None  # missing file = silent, no crash

    def play(self):
        if self.sound:
            self.sound.play()