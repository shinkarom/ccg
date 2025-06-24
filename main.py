# main.py (Print-Based Console Version)

import os
import random
import time
from enum import Enum, auto
from rich import print

# Our core game logic and AI
from game_state import GameState, PlayerState
from phases import UpkeepPhase
import game_logic
from ccg_ai import CCG_AI
from ui import ConsoleUI
from deckgen import generate_quick_deck

class GameMode(Enum):
    PVP = '1'
    PVE = '2'
    AVA = '3'

class PlayerType(Enum):
    HUMAN = auto()
    AI = auto()

# --- Application State Management ---
class AppState(Enum):
    LOBBY = auto()
    IN_GAME = auto()
    EXITING = auto()

# --- Centralized Configuration (from previous step) ---
CONTROLLER_AI_CONFIG = {"time_limit_ms": 500} # The AI that plays for itself
ADVISOR_AI_CONFIG = {"time_limit_ms": 250}   # A faster AI for quick suggestions
MODE_PLAYER_SETUP = {
    GameMode.PVP: [PlayerType.HUMAN, PlayerType.HUMAN],
    GameMode.PVE: [PlayerType.HUMAN, PlayerType.AI],
    GameMode.AVA: [PlayerType.AI, PlayerType.AI],
}

class Player:
    def __init__(self, player_type, ai_instance=None):
        self.type = player_type
        self.ai = ai_instance

    def is_human(self):
        return self.type == PlayerType.HUMAN

# --------------------------------------------------------------------------
# NEW CLASS 1: GameRunner - Encapsulates a single game session
# --------------------------------------------------------------------------
class GameRunner:
    """
    Manages the execution of a single game from start to finish.
    It is configured by the GameApplication and doesn't know about lobbies.
    """
    def __init__(self, ui, players, pov_provider):
        self.ui = ui
        self.players = players
        self.get_pov_for_render = pov_provider

    def run_game(self):
        """Contains the main game loop."""
        d = generate_quick_deck(40)
        game_state = game_logic.init_game([d.copy(), d.copy()])
        previous_player_idx = -1

        while True:
            # 1. Check for Game Over
            winner_index = game_state.get_winner_index()
            if winner_index != -1:
                pov_index_at_end = self.get_pov_for_render(previous_player_idx)
                self.ui.render_game_state(game_state, pov_index_at_end)
                self.ui.display_game_over(winner_index)
                return  # Game is over, return control to the application

            current_player_idx = game_state.current_player_index
            
            # 2. Universal "Press Enter" prompt
            if current_player_idx != previous_player_idx:
                self.ui.prompt_for_priority(current_player_idx + 1)
            previous_player_idx = current_player_idx
            
            # 3. Render from the correct POV
            pov_to_render = self.get_pov_for_render(current_player_idx)
            self.ui.render_game_state(game_state, pov_to_render)
            
            current_player = self.players[current_player_idx]
            action = None

            r = game_state.get_legal_moves()
            if len(r) == 1:
                print(f"Automaticaly performing {r[0]}")
                game_state = game_state.process_action(r[0])
                continue

            if current_player.is_human():
                # --- Human Player's Turn Sequence ---
                # a. Get and display the advisor's suggestion automatically.
                print("Advisor is analyzing the board...")
                advisor_ai = current_player.ai
                suggested_action, rollouts = advisor_ai.find_best_move(game_state)
                self.ui.display_ai_suggestion(suggested_action, rollouts)
                
                # b. NOW, prompt the human for their actual move.
                action = self.ui.get_human_move(game_state)

            else: # AI Player's Turn Sequence
                print(f"Player {current_player_idx + 1} (AI) is thinking...")
                action, rollouts = current_player.ai.find_best_move(game_state)
                self.ui.display_ai_move(action, rollouts)
            
            # 5. Apply Action
            if action:
                if action == ("QUIT_GAME",):
                    print("Returning to lobby...")
                    return # Game is quit, return control
                game_state = game_state.process_action(action)
            else:
                print("Error: No action was chosen or available. Exiting game.")
                return


# --------------------------------------------------------------------------
# NEW CLASS 2: GameApplication - The main application controller
# --------------------------------------------------------------------------
class GameApplication:
    """
    Controls the overall application flow, including the lobby and game sessions.
    """
    def __init__(self):
        self.ui = ConsoleUI()
        self.state = AppState.LOBBY
        self.game_settings = {} # Will hold the configuration from the lobby

    def run(self):
        """The main application loop."""
        while self.state != AppState.EXITING:
            if self.state == AppState.LOBBY:
                self.run_lobby()
            elif self.state == AppState.IN_GAME:
                self.start_game()
                # After the game, we can decide where to go.
                # For now, we go back to the lobby.
                self.state = AppState.LOBBY 

    def run_lobby(self):
        """
        This is where you'd handle creating a new game, joining one, etc.
        For now, it just configures and starts one game.
        """
        self.ui.display_welcome()
        
        # In a real lobby, this would be a loop where you select options
        # and see other players. The "get_game_mode" is the first step.
        mode_input = self.ui.get_game_mode()
        if not mode_input: # User might want to quit from the lobby
            self.state = AppState.EXITING
            return

        try:
            mode = GameMode(mode_input)
        except ValueError:
            print(f"Invalid mode '{mode_input}'. Please try again.")
            return # Stay in the lobby state

        players = []
        # --- Use the lobby selection to configure the next game ---
        player_types = MODE_PLAYER_SETUP[mode]
        for p_type in player_types:
            # Choose the correct AI configuration based on the player type
            config = CONTROLLER_AI_CONFIG if p_type == PlayerType.AI else ADVISOR_AI_CONFIG
            ai_instance = CCG_AI(config)
            players.append(Player(p_type, ai_instance))

        # Determine the POV rendering strategy based on the mode
        human_player_index = next((i for i, p in enumerate(players) if p.is_human()), -1)
        if mode == GameMode.PVE:
            pov_provider = lambda current_idx: human_player_index
        if mode == GameMode.AVA:
            pov_provider = lambda current_idx: -1
        else:
            pov_provider = lambda current_idx: current_idx
            
        # Store the complete configuration and change the application state
        self.game_settings = {
            "players": players,
            "pov_provider": pov_provider
        }
        self.state = AppState.IN_GAME
        
    def start_game(self):
        """Creates and runs a game session using the current settings."""
        if not self.game_settings:
            print("Error: Cannot start game, no settings configured.")
            self.state = AppState.LOBBY
            return
        
        # Create a GameRunner with the settings chosen in the lobby
        runner = GameRunner(
            self.ui,
            self.game_settings["players"],
            self.game_settings["pov_provider"]
        )
        runner.run_game() # This will block until the game is over
        

if __name__ == "__main__":
    from rich.traceback import install
    install(show_locals=False)
    # The entry point is now extremely simple!
    app = GameApplication()
    app.run()
    print("Thanks for playing!")