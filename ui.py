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

    def render_game_state(self, state: GameState, pov_player_index: int):
        """
        Prints the game state to the console.
        - If human_player_index is a valid index, it renders from that player's perspective.
        - If human_player_index is -1 (AI vs AI), it renders a neutral, top-down view.
        """
        self.clear_screen()
        
        # --- CORRECTED: Determine Perspective and Labels ---
        if pov_player_index != -1: # PvP or PvE mode
            p_pov = state.players[pov_player_index]
            p_opp = state.players[1 - pov_player_index]
            pov_string = "YOUR"
            opp_string = "OPPONENT'S"
        else: # Neutral AI vs AI view
            p_pov = state.players[0]
            p_opp = state.players[1]
            pov_string = "PLAYER 1'S"
            opp_string = "PLAYER 2'S"

        print("="*50)
        print(f"--- {opp_string} SIDE (Player {p_opp.number}) ---") # Assuming PlayerState has an ID
        print(f"HP: {p_opp.health:<3} | Resources: {p_opp.resource:<2} | Hand: {len(p_opp.hand):<2} | Deck: {len(p_opp.deck):<2}")
        print("Board:")
        for i,unit in enumerate(p_opp.board):
            if unit:
                card = CARD_DB.get(unit.card_id, {})
                r = "+" if unit.is_ready else "-"
                print(f" [{i+1}] {r} {card.get('name', 'Unknown')} ({unit.current_attack}/{unit.current_health})")
            else:
                print(f" [{i+1}] ---")
        
        print("\n" + "-"*20 + " VS " + "-"*22 + "\n")

        print(f"--- {pov_string} SIDE (Player {p_pov.number}) ---")
        print("Board:")
        for i,unit in enumerate(p_pov.board):
            if unit:
                card = CARD_DB.get(unit.card_id, {})
                r = "+" if unit.is_ready else "-"
                print(f" [{i+1}] {r} {card.get('name', 'Unknown')} ({unit.current_attack}/{unit.current_health})")
            else:
                print(f" [{i+1}] ---")

        print("\nHand (for Player {}):".format(pov_player_index + 1))
        player_with_pov = state.players[pov_player_index]
        for i, card_id in enumerate(player_with_pov.hand):
            card = CARD_DB.get(card_id, {})
            print(f"  [{i+1}] {card.get('name', 'Unknown')} (Cost: {card.get('cost', '?')})")
        print(f"HP: {p_pov.health:<3} | Resources: {p_pov.resource:<2} | Hand: {len(p_pov.hand):<2} | Deck: {len(p_pov.deck):<2}")
        print("="*50)
        
        # --- CORRECTED: Turn Status Logic ---
        turn_status = f"Player {state.current_player_index + 1}'s Turn"
        if pov_player_index != -1:
            if state.current_player_index == pov_player_index:
                turn_status = "** YOUR TURN **"
            else:
                turn_status = "OPPONENT'S TURN"
            
        print(f"Turn {state.turn_number} | Phase: {state.current_phase.get_name()} | {turn_status}\n")

    def prompt_for_priority(self, player_number: int):
        """A generic prompt that waits for the player who has control."""
        input(f"\n--- Player {player_number}, you have priority. --- \nPress Enter to continue...")
        
    def get_human_move(self, state: GameState) -> tuple:
        """
        Gets a move from a human player. Also parses input to differentiate
        between move selections and non-move commands, leaving command
        implementation to the developer.
        """
        legal_moves = state.get_legal_moves()

        # --- The Command Loop ---
        while True:
            # Display the list of available moves
            print("--- Choose Your Action ---")
            for i, move in enumerate(legal_moves):
                # This part correctly handles future descriptions in the move tuple
                description = str(move)
                if len(move) > 2 and isinstance(move[2], str):
                    description = move[2]
                print(f"[{i+1}] {description}")
            
            print("\nType a number to make a move, or type a command.")
            user_input = input("> ").strip()

            # --- Check if the input is a number (a move selection) ---
            if user_input.isdigit():
                try:
                    choice_idx = int(user_input) - 1
                    if 0 <= choice_idx < len(legal_moves):
                        # Valid move number. Return the action tuple.
                        return legal_moves[choice_idx]
                    else:
                        print("Invalid move number. Please try again.")
                        # Continue the loop to re-prompt
                        continue
                except ValueError:
                    # This case is unlikely given isdigit() but is safe to have.
                    pass # Fall through to command handling

            # --- If not a number, treat it as a command ---
            # The input is now considered a command to be parsed and handled.
            # This is where you will add your own command logic.
            
            parts = user_input.lower().split()
            command = parts[0]

            if command == "quit":
                print("Quitting game.")
                return ('QUIT_GAME',) # Return a special tuple to be handled by the main loop.

            # Default case for unrecognized commands
            else:
                print(f"Unknown command: '{user_input}'")
                # Continue the loop to re-prompt
                
    def display_ai_move(self, action: tuple, rollouts: int):
        """Announces the AI's move."""
        description = str(action)
        if len(action) > 2 and isinstance(action[2], str):
            description = action[2]
            
        print(f"\nAI is thinking... (completed {rollouts} simulations)")
        print(f"AI chose: {description}")
        time.sleep(1.5)
        
    def display_ai_suggestion(self, action: tuple, rollouts: int):
        """Announces the AI's move."""
        description = str(action)
        if len(action) > 2 and isinstance(action[2], str):
            description = action[2]
            
        print(f"After {rollouts} rollouts Advisor suggests: {description}")

    def display_game_over(self, winner_index: int):
        """Prints the final game over message."""
        print("="*50)
        if winner_index == -2:
            print("!!! GAME OVER: IT'S A DRAW! !!!")
        else:
            print(f"!!! GAME OVER: Player {winner_index + 1} WINS! !!!")
        print("="*50)
