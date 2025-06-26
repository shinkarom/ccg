import os
import time

# We need to import the type hints for our game objects
from game_state import GameState, UnitCombatStatus
from card_database import CARD_DB, get_card_line
from rich import print
from rich.prompt import Prompt

class ConsoleUI:
    """Handles all console input and output for the game."""

    def clear_screen(self):
        """Clears the console screen for a clean display."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_welcome(self):
        """Prints the initial welcome message."""
        self.clear_screen()
        print("[#aabbcc]=============================================")
        print("[#aabbdd]         Welcome to the Python CCG!          ")
        print("[#aabbee]=============================================")

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

    def _render_player_board(self, player_state: 'PlayerState', label: str, show_hand: bool):
        """
        Private helper method to render one player's side of the board.
        Encapsulates the duplicated logic.
        """
        print(f"--- {label} SIDE (Player {player_state.number}) ---")
        
        # We can also render the player's stats here for better grouping.
        # Note the hand size is public info, but the contents are not.
        print(f"HP: {player_state.health:<3} | Resource: {player_state.resource:<2} | Hand: {len(player_state.hand):<2}")
        
        print("Board:")
        for i, unit in enumerate(player_state.board):
            if unit:
                card = CARD_DB.get(unit.card_id, {})
                # Determine status character
                if unit.combat_status == UnitCombatStatus.ATTACKING:
                    status_char = ">"
                elif unit.combat_status == UnitCombatStatus.BLOCKING:
                    status_char = "<"
                elif unit.is_ready:
                    status_char = "+"
                else:
                    status_char = "-"
                
                print(f" [{i+1}] {status_char} {card.get('name', 'Unknown')} ({unit.current_attack}/{unit.current_health})")
            else:
                # Print empty slot
                print(f" [{i+1}] ")
              
        if show_hand:
            print("Hand:")        
            for i, card_id in enumerate(player_state.hand):
                print(f"  [{i+1}] {get_card_line(card_id)}")        

    def render_game_state(self, state: GameState, pov_player_index: int):
        """
        Prints the game state to the console using a helper method to stay DRY.
        """
        self.clear_screen()
        show_opp_hand = False
        # --- Determine Perspective and Labels ---
        if pov_player_index != -1: # Player-centric view (PvP or PvE)
            p_pov = state.players[pov_player_index]
            p_opp = state.players[1 - pov_player_index]
            pov_label = "YOUR"
            opp_label = "OPPONENT'S"
        else: # Neutral AI vs AI view
            show_opp_hand = True
            p_pov = state.players[0]
            p_opp = state.players[1]
            pov_label = "PLAYER 1'S"
            opp_label = "PLAYER 2'S"

        print("="*50)
        
        # --- CALL THE HELPER METHOD for the opponent ---
        self._render_player_board(p_opp, opp_label,show_opp_hand)
        
        print("\n" + "-"*20 + " VS " + "-"*22 + "\n")

        # --- CALL THE HELPER METHOD for the point-of-view player ---
        self._render_player_board(p_pov, pov_label,True)
        
        print("-" * 50)
        
        print("="*50)
        
        # --- Render Turn Status ---
        turn_status = f"Player {state.current_player_index + 1}'s Turn"
        if pov_player_index != -1:
            turn_status = "** YOUR TURN **" if state.current_player_index == pov_player_index else "OPPONENT'S TURN"
            
        print(f"Turn {state.turn_number} | Phase: {state.current_phase.get_name()} | {turn_status}\n")

    def prompt_for_priority(self, player_number: int):
        """A generic prompt that waits for the player who has control."""
        input(f"\n--- Priority passes to player {player_number}. --- \nPress Enter to continue...")
        
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
            user_input = Prompt.ask("> ").strip()

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
