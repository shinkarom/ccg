# controller.py
from game_state import GameState
import game_logic
from deckgen import generate_quick_deck

class GameController:
    """
    Manages the game state and orchestrates game logic.
    It does NOT handle any UI or direct user input. It is the "Controller"
    in the MVC pattern, manipulated by the Textual "View".
    """
    def __init__(self, player_names: list[str]):
        self.player_names = player_names
        self.game_state = self._setup_game()

    def _setup_game(self) -> GameState:
        """Creates the initial game state for a session. (Unchanged logic)"""
        deck1 = generate_quick_deck(40)
        deck2 = generate_quick_deck(40)
        return game_logic.init_game(decks=[deck1, deck2], player_names=self.player_names)

    def get_legal_moves(self) -> list:
        """A simple pass-through to the game state for the UI to use."""
        return self.game_state.get_legal_moves()

    def process_action(self, action: tuple):
        """
        Processes a single action and updates the game state.
        This is the primary method the UI will call.
        """
        if self.game_state.is_terminal() or action is None:
            return

        # The core logic from your old run_game loop
        self.game_state = self.game_state.process_action(action)

        # IMPORTANT: Handle auto-passes and chained actions
        # After a player acts, the game might auto-pass priority. We loop here
        # until the game requires human input again.
        while not self.game_state.is_terminal():
            legal_moves = self.get_legal_moves()
            # If there's only one move (like "End Turn" or drawing a card)
            # and it doesn't require player choice, we could auto-execute.
            # For now, we'll stop if any moves are available for the player.
            if legal_moves:
                break # Break the loop to wait for human input
            else:
                # This should not happen if your game logic auto-passes correctly,
                # but is good defensive programming.
                # In a real game, this might be a self.game_state.pass_priority() call.
                continue

    def reset_game(self):
        """Re-initializes the game state for a "Play Again" scenario."""
        self.game_state = self._setup_game()
