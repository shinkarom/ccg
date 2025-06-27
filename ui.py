# ui.py

import os
import time

# Using try/except for type hinting allows the code to run even if modules are complex
try:
    from game_state import GameState, PlayerState, UnitCombatStatus
    from card_database import CARD_DB, get_card_line
except ImportError:
    pass

from rich import print
from rich.prompt import Prompt
from typing import Dict, Any, List, Optional

class ConsoleUI:
    """Handles all console input and output for the game."""

    def clear_screen(self):
        """Clears the console screen for a clean display."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_welcome(self, title: str):
        """Prints a customizable initial welcome message."""
        self.clear_screen()
        bar = "=" * (len(title) + 8)
        print(f"[#aabbcc]{bar}")
        print(f"[#aabbdd]    {title}    ")
        print(f"[#aabbee]{bar}")

    def _render_player_board(self, player_state: 'PlayerState', is_pov: bool):
        """Private helper to render one player's side of the board."""
        pov_label = "(YOU)" if is_pov else "(OPPONENT)"
        print(f"--- {player_state.name.upper()}'S SIDE {pov_label} ---")
        
        print(f"Score: {player_state.score:<3} | Hand: {len(player_state.hand):<2} | Deck: {len(player_state.deck):<2} | Discard: {len(player_state.graveyard):<2}")
        
        print("Board:")
        if not any(player_state.board):
            print("  (empty)")
        else:
            for i, unit in enumerate(player_state.board):
                if unit:
                    card = CARD_DB.get(unit.card_id, {})
                    if unit.combat_status == UnitCombatStatus.ATTACKING: status_char = "[bold red]>[/bold red]"
                    elif unit.combat_status == UnitCombatStatus.BLOCKING: status_char = "[bold blue]<[/bold blue]"
                    elif unit.is_ready: status_char = "[bold green]+[/bold green]"
                    else: status_char = "[dim]-[/dim]"
                    
                    print(f"  [{i+1}] {status_char} {card.get('name', 'Unknown')} ({unit.current_attack}/{unit.current_health})")
                else:
                    print(f"  [{i+1}] (empty slot)")
              
        if is_pov:
            print("Hand:")
            if not player_state.hand:
                print("  (empty)")
            else:
                for i, card_id in enumerate(player_state.hand):
                    print(f"  - {get_card_line(card_id)}")

    def render_game_state(self, state: 'GameState', pov_index: int):
        """Prints the game state to the console from a specific player's perspective."""
        self.clear_screen()
        opponent_index = 1 - pov_index
        p_pov = state.players[pov_index]
        p_opp = state.players[opponent_index]

        self._render_player_board(p_opp, is_pov=False)
        print("\n" + "[dim]" + "-"*20 + " VS " + "-"*22 + "[/dim]" + "\n")
        self._render_player_board(p_pov, is_pov=True)
        
        print("-" * 50)
        turn_status = f"Turn {state.turn_number} | Phase: {state.current_phase.get_name()} | Player {state.current_player_index + 1}'s Turn"
        print(f"[bold yellow]{turn_status}[/bold yellow]\n")

    def prompt_for_turn(self, player_name: str):
        """A simple prompt that waits for the player who has control."""
        Prompt.ask(f"\n--- Priority passes to [bold cyan]{player_name}[/bold cyan]. Press Enter to continue... ---")

    def get_human_choice(self, moves: List[Any], report: Dict[str, Any]) -> Optional[Any]:
        """
        Displays a sorted list of moves with analysis, and gets the user's choice.
        This is the primary interaction point for a human player.
        """
        print("\n--- CHOOSE YOUR ACTION ---")

        # --- 1. Sort the moves based on the analysis report ---
        # The lambda function looks up the win rate for each move's string representation.
        # .get(str(move), {}).get('win_rate', -1.0) is a safe way to handle moves not in the report.
        if report:
            sorted_moves = sorted(
                moves,
                key=lambda move: report[0].get(str(move), {}).get('win_rate', -1.0),
                reverse=True  # Highest win rate first
            )
        else:
            sorted_moves = moves # If no report, use the original order

        # --- 2. Display the sorted and formatted list of options ---
        for i, move in enumerate(sorted_moves):
            move_str = str(move)
            stats = report[0].get(move_str)
            
            # This is where the formatting happens, exactly as requested.
            if stats and stats['sims'] > 0:
                win_rate_str = f"{stats['win_rate']:.1%}"
                win_contrib_str = f"{stats['win_contribution']:.1%}"
                # The final formatted line:
                print(f"[[bold]{i+1}[/bold]] {move_str} [dim](WR: {win_rate_str}, WC: {win_contrib_str})[/dim]")
            else:
                # If no stats are available for this move, just print the move.
                print(f"[[bold]{i+1}[/bold]] {move_str}")

        # --- 3. Get valid input from the user ---
        while True:
            try:
                # Using Prompt for consistency, but input() also works.
                choice_str = Prompt.ask(f"\nEnter a number (1-{len(sorted_moves)}) or 'q' to quit", default="1")
                
                if choice_str.lower() in ['q', 'quit']:
                    return None # Signal to the controller to quit the game
                
                choice_idx = int(choice_str) - 1
                if 0 <= choice_idx < len(sorted_moves):
                    # Valid choice, return the actual move object.
                    return sorted_moves[choice_idx]
                else:
                    print(f"[red]Invalid number. Please enter a value between 1 and {len(sorted_moves)}.[/red]")
            except ValueError:
                print("[red]Invalid input. Please enter a number.[/red]")


    def ask_play_again(self) -> bool:
        """Asks the user if they want to play another game."""
        choice = Prompt.ask("\nPlay another game?", choices=["y", "n"], default="y")
        return choice == 'y'

    def display_game_over(self, state: 'GameState'):
        """Prints the final game over message by inspecting the state."""
        winner_index = state.get_winner()
        winner_name = ""

        if winner_index is not None and winner_index >= 0:
            winner_name = state.players[winner_index].name

        bar = "=" * 50
        print(f"\n[bold magenta]{bar}")
        if winner_index is not None and winner_index >= 0:
            print(f"!!! GAME OVER: {winner_name.upper()} WINS! !!!")
        else:
            print("!!! GAME OVER: IT'S A DRAW! !!!")
        print(f"{bar}[/bold magenta]")

