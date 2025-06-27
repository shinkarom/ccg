# main.py (Full-Fledged Game Architecture, PvP Focus)

from enum import Enum, auto
from rich import print
from rich.traceback import install

# --- Core Game Logic and AI ---
# Using the new analyzer, and assuming your other modules are in place.
from game_state import GameState
import game_logic
from ui import ConsoleUI
from deckgen import generate_quick_deck

# --- Application State Management (Kept for future expansion) ---
class AppState(Enum):
    STARTING = auto()
    IN_GAME = auto()
    EXITING = auto()

# --- Player Abstraction (Simplified for now) ---
# We no longer need PlayerType enum, as it's always HUMAN for now.
class Player:
    """A simple container for player information."""
    def __init__(self, name: str):
        self.name = name
        # In the future, this could hold player-specific stats, deck choices, etc.

# --------------------------------------------------------------------------
# GameRunner - Encapsulates a single game session (Largely Unchanged)
# --------------------------------------------------------------------------
class GameRunner:
    """
    Manages the execution of a single game from start to finish.
    It is configured by the GameApplication.
    """
    def __init__(self, ui: ConsoleUI, players: list[Player]):
        self.ui = ui
        self.players = players
        self.game_state = self._setup_game()

    def _setup_game(self) -> GameState:
        """Creates the initial game state for the session."""
        print("Setting up a new PvP game...")
        # For now, generate two identical decks. This can be expanded to use config.
        deck1 = generate_quick_deck(40)
        deck2 = generate_quick_deck(40)
        
        player_names = [p.name for p in self.players]
        initial_state = game_logic.init_game(decks=[deck1, deck2], player_names=player_names)
        print("[green]Game setup complete![/green]\n")
        return initial_state

    def run_game(self):
        """Contains the main game loop, returning when the game is over."""
        previous_player_idx = -1

        while not self.game_state.is_terminal():
            current_player_idx = self.game_state.current_player_index
            current_player_name = self.players[current_player_idx].name

            if current_player_idx != previous_player_idx:
                self.ui.prompt_for_turn(current_player_name)
            previous_player_idx = current_player_idx
            
            # Render from the current player's perspective
            self.ui.render_game_state(self.game_state, pov_index=current_player_idx)
            
            legal_moves = self.game_state.get_legal_moves()
            if not legal_moves:
                continue # Assume game logic handles auto-pass

            if len(legal_moves) == 1:
                action = legal_moves[0]
                print(f"Only one legal move. Automatically performing: [cyan]{action[0]}[/cyan]")
            else:
                action = self.ui.get_human_choice(legal_moves)

            # --- Apply Action ---
            if action is None: # User chose to quit from the UI prompt
                print("Returning to main menu...")
                return # Game is quit, return control to GameApplication
            
            self.game_state = self.game_state.process_action(action)
            print("-" * 50)

        # --- Game Over ---
        # The loop has ended, so the game is over.
        self.ui.render_game_state(self.game_state, pov_index=0) # Show final state
        self.ui.display_game_over(self.game_state)

# --------------------------------------------------------------------------
# GameApplication - The main application controller (Simplified Lobby)
# --------------------------------------------------------------------------
class GameApplication:
    """
    Controls the overall application flow. For now, it bypasses the lobby
    and starts a PvP game directly.
    """
    def __init__(self):
        self.ui = ConsoleUI()
        self.state = AppState.STARTING

    def run(self):
        """The main application loop."""
        self.ui.display_welcome("CCG Project")

        while self.state != AppState.EXITING:
            if self.state == AppState.STARTING:
                # Instead of a lobby, we immediately transition to a game.
                self.state = AppState.IN_GAME
            
            elif self.state == AppState.IN_GAME:
                self.start_pvp_game()
                # After the game, ask the user if they want to play again.
                if self.ui.ask_play_again():
                    self.state = AppState.IN_GAME # Loop back to start another game
                else:
                    self.state = AppState.EXITING # Exit the application
    
    def start_pvp_game(self):
        """Configures and runs a single PvP game session."""
        
        # 1. Configure Players for PvP
        # This is where we hardcode the PvP setup.
        # In the future, a lobby would gather this info.
        players = [
            Player(name="Player 1"),
            Player(name="Player 2")
        ]

        # 3. Create and run the game session
        runner = GameRunner(self.ui, players)
        runner.run_game() # This will block until the game is over or quit.
        

if __name__ == "__main__":
    # Enable rich tracebacks for easier debugging
    install(show_locals=False)
    
    # The entry point remains extremely simple and clean
    app = GameApplication()
    app.run()
    
    print("\nThanks for playing!")

