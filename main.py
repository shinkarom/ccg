# main.py (New Version)
from textual.app import App
from rich.traceback import install

from controller import GameController
from tui import GameUI

install(show_locals=False)

if __name__ == "__main__":
    game_controller = GameController(["Arin", "Zanthar"])
    ui = GameUI(game_controller)
    ui.run()
