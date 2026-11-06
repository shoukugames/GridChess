"""Music and sound effects. With no audio device the game simply stays silent."""
import pygame

from .paths import asset

MUSIC = {"title": "bgm_title.wav", "game": "bgm_game.wav"}
EFFECTS = ["click", "hover", "key", "move", "capture", "check", "castle", "promote", "error",
           "tick", "timeout", "win", "lose", "draw", "start", "new_record", "cpu"]
VOLUME = {"hover": 0.22, "key": 0.35, "tick": 0.5, "click": 0.55, "move": 0.8, "cpu": 0.7}


class Audio:
    def __init__(self, settings):
        self.settings = settings
        self.ok = False
        self.sounds = {}
        self.current = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 1024)
            pygame.mixer.set_num_channels(24)
            for name in EFFECTS:
                snd = pygame.mixer.Sound(asset("audio", name + ".wav"))
                snd.set_volume(VOLUME.get(name, 0.8))
                self.sounds[name] = snd
            self.ok = True
        except (pygame.error, FileNotFoundError, OSError) as error:
            print(f"Audio disabled: {error}")

    def play(self, name):
        if self.ok and self.settings.get("sfx", True) and name in self.sounds:
            self.sounds[name].play()

    def music(self, which):
        if not self.ok:
            return
        if not self.settings["bgm"]:
            pygame.mixer.music.fadeout(500)
            self.current = None
            return
        if which == self.current:
            return
        self.current = which
        try:
            pygame.mixer.music.load(asset("audio", MUSIC[which]))
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1, fade_ms=2000)
        except pygame.error as error:
            print(f"Music unavailable: {error}")

    def toggle_bgm(self, which):
        self.settings["bgm"] = not self.settings["bgm"]
        self.current = None
        self.music(which)
