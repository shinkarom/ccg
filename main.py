# main.py (New Version)
from textual.app import App
from rich.traceback import install

from controller import GameController
from tui import GameScreen

install(show_locals=False)

class CCGApp(App):
    """The main Textual application class."""
    
    def on_mount(self) -> None:
        """Set up the game and push the main game screen."""
        # Player configuration now happens here
        players = ["Player 1", "Player 2"]
        controller = GameController(player_names=players)
        self.push_screen(GameScreen(controller=controller))


if __name__ == "__main__":
    app = CCGApp()
    app.run()
    print("Thanks for playing!")
