import os
import time

# We need to import the type hints for our game objects
from game_state import GameState
from card_database import CARD_DB

class ConsoleUI:
    """Handles all console input and output for the game."""

    def clear_screen(self):
        """Clears the console screen for a clean display."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_welcome(self):
        """Prints the initial welcome message."""
        self.clear_screen()
        print("=============================================")
        print("         Welcome to the Python CCG!          ")
        print("=============================================")

    def get_game_mode(self) -> str:
        """Asks the user to select a game mode and returns the choice."""
        print("\n--- Game Modes ---")
        print("  [1] Player vs. Player") # New option
        print("  [2] Player vs. AI")
        print("  [3] AI vs. AI")         # Renumbered
        
        while True:
            mode = input("\nChoose a game mode (1, 2, or 3): ")
            if mode in ['1', '2', '3']:
                return mode
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")

    def render_game_state(self, state: GameState, current_pov_index: int):
        """
        Prints the game state to the console from the perspective of the
        current player (current_pov_index).
        """
        self.clear_screen()
        
        player = state.players[current_pov_index]
        opponent = state.players[1 - current_pov_index]
        
        # Determine player labels
        pov_string = f"PLAYER {current_pov_index + 1}'S"
        opp_string = f"PLAYER {1 - current_pov_index + 1}'S"

        print("="*50)
        print(f"--- {opp_string} SIDE ---")
        # ... (rest of rendering is unchanged) ...
        print("\n" + "-"*20 + " VS " + "-"*22 + "\n")
        print(f"--- {pov_string} SIDE ---")
        # ... (rest of rendering is unchanged) ...
        
        print("\nYour Hand:") # Use a generic "Your Hand"
        for i, card_id in enumerate(player.hand):
            card = CARD_DB.get(card_id, {})
            print(f"  [{i+1}] {card.get('name', 'Unknown')} (Cost: {card.get('cost', '?')}) - {card.get('text', '')}")
        
        print("="*50)
        
        turn_status = f"** PLAYER {state.current_player_index + 1}, IT'S YOUR TURN **"
            
        print(f"Turn {state.turn_number} | Phase: {state.current_phase.get_name()} | {turn_status}\n")
        
    def get_human_move(self, state: GameState) -> tuple:
        """Gets a move from a human player by displaying a numbered list of legal moves."""
        legal_moves = state.get_legal_moves()
        
        print("--- Choose Your Action ---")
        for i, move in enumerate(legal_moves):
            # --- CORRECTED LOGIC ---
            # This is now "dumb". It looks for a description string, otherwise just prints the raw tuple.
            # This will work now and will automatically support your future change.
            description = str(move) # Default to the raw tuple representation
            if len(move) > 2 and isinstance(move[2], str):
                description = move[2] # Use the provided description string
            
            print(f"[{i+1}] {description}")
        
        while True:
            try:
                choice = input("\nEnter the number of your move: ")
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(legal_moves):
                    return legal_moves[choice_idx]
                else:
                    print("Invalid number. Please try again.")
            except (ValueError, IndexError):
                print("Invalid input. Please enter a valid number from the list.")

    def display_ai_move(self, action: tuple, rollouts: int):
        """Announces the AI's move."""
        description = str(action)
        if len(action) > 2 and isinstance(action[2], str):
            description = action[2]
            
        print(f"\nAI is thinking... (completed {rollouts} simulations)")
        print(f"AI chose: {description}")
        time.sleep(1.5)

    def display_game_over(self, winner_index: int):
        """Prints the final game over message."""
        print("="*50)
        if winner_index == -2:
            print("!!! GAME OVER: IT'S A DRAW! !!!")
        else:
            print(f"!!! GAME OVER: Player {winner_index + 1} WINS! !!!")
        print("="*50)
