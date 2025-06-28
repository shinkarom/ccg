# main.py (New Version)
from rich.traceback import install

from controller import GameController
from tui import GameUI

install(show_locals=False)

if __name__ == "__main__":
    game_controller = GameController(["Player 1", "Player 2"])
    ui = GameUI(game_controller)
    ui.run()
