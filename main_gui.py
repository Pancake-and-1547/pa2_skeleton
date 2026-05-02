"""GUI entry point."""

from pathlib import Path
import os
import sys

import pygame

from gui.level import Level
from gui.paths import asset_path
from gui.settings import SCREEN_HEIGHT, SCREEN_WIDTH


class Game:
    def __init__(self, map_path: str = "map.txt") -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        pygame.display.set_caption("COMP1023 PA2 Game GUI")

        base_dir = Path(__file__).resolve().parent
        icon_path = asset_path("image", "icon.bmp")
        if icon_path.exists():
            pygame.display.set_icon(pygame.image.load(str(icon_path)))

        requested_map = Path(map_path)
        full_map_path = requested_map if requested_map.is_absolute() else (base_dir / requested_map)
        if full_map_path.exists():
            map_layout = full_map_path.read_text(encoding="utf-8")
        else:
            print("Warning: map file not found, using default layout.")
            map_layout = (
                "####################\n"
                "#..................#\n"
                "#..................#\n"
                "#........A.........#\n"
                "#..................#\n"
                "#########*##########"
            )

        self.level = Level(map_layout)

    def run(self) -> None:
        while True:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            dt = self.clock.tick() / 1000
            self.level.run(dt, events)
            pygame.display.update()


def run_game(path: str = "map.txt") -> None:
    """Apply platform display fixes and launch the GUI."""
    os.environ["SDL_IME_SHOW_UI"] = "1"
    os.environ["SDL_VIDEO_ALLOW_HIGH_DPI"] = "1"

    if os.name == "nt":
        import ctypes

        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except AttributeError:
            pass

    Game(path).run()


if __name__ == "__main__":
    run_game()
