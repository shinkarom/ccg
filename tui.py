import os
import time
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from controller import GameController
from card_database import CARD_DB, get_card_line

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

class GameUI:
    """A comfortable REPL-style UI for the CCG using Rich and Prompt Toolkit."""

    def __init__(self, controller: GameController):
        self.controller = controller
        self.console = Console()
        self.session = PromptSession(auto_suggest=AutoSuggestFromHistory())

    def run(self):
        """The main game loop."""
        while True:
            clear_screen()
            
            ## MODIFIED: Fetch legal moves before displaying state and getting input
            legal_moves = []
            if not self.controller.game_state.is_terminal():
                legal_moves = self.controller.get_legal_moves()

            self._display_game_state(legal_moves)

            if self.controller.game_state.is_terminal():
                self._handle_game_over()
                if self.controller.game_state.is_terminal():
                    break
                else:
                    continue
            
            ## MODIFIED: The completer now only suggests meta-commands.
            meta_commands = ["help", "quit", "reset"]
            completer = WordCompleter(meta_commands, ignore_case=True)

            try:
                command_str = self.session.prompt(
                    "> ",
                    completer=completer,
                    complete_while_typing=True
                )
                self._handle_command(command_str.strip().lower(), legal_moves)
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[bold yellow]Quitting game.[/bold yellow]")
                break

    ## MODIFIED: Now takes legal_moves as an argument to display them.
    def _display_game_state(self, legal_moves: list):
        """Renders the entire game state, including available actions."""
        state = self.controller.game_state
        player = state.get_current_player()
        opponent = state.get_opponent()

        # --- Opponent, Player, and Hand Panels (Unchanged) ---
        opponent_panel = self._create_opponent_panel(opponent)
        player_panel = self._create_player_panel(player)
        hand_panel = self._create_hand_panel(player.hand)
        
        self.console.print(Rule(f"[bold]Turn {state.turn_number} - {player.name}'s Move[/bold]"))
        self.console.print(opponent_panel)
        self.console.print(player_panel)
        self.console.print(hand_panel)
        
        ## NEW: Create and print a dedicated table for actions.
        actions_table = self._create_actions_table(legal_moves)
        self.console.print(actions_table)

    ## --- Panel and Table Creation Helpers ---

    def _create_opponent_panel(self, opponent) -> Panel:
        opponent_table = self._create_board_table(opponent.board, is_opponent=True)
        opponent_stats = (
            f"Score: [bold]{opponent.score}[/] | "
            f"Resource: [bold]{opponent.resource}[/] | "
            f"Hand: [bold]{len(opponent.hand)}[/] | "
            f"Deck: [bold]{len(opponent.deck)}[/]"
        )
        return Panel(
            Group(Text.from_markup(opponent_stats), opponent_table),
            title=f"[red]Opponent: {opponent.name}[/red]", border_style="red"
        )

    def _create_player_panel(self, player) -> Panel:
        player_board_table = self._create_board_table(player.board)
        player_stats = (
            f"Score: [bold]{player.score}[/] | "
            f"Resource: [bold]{player.resource}[/] | "
            f"Hand: [bold]{len(player.hand)}[/] | "
            f"Deck: [bold]{len(player.deck)}[/]"
        )
        return Panel(
            Group(Text.from_markup(player_stats), player_board_table),
            title=f"[green]You: {player.name}[/green]", border_style="green"
        )

    def _create_hand_panel(self, hand: list) -> Panel:
        hand_table = self._create_hand_table(hand)
        return Panel(
            hand_table, title="[bold cyan]Your Hand[/bold cyan]", border_style="cyan"
        )
    
    ## NEW HELPER METHOD: Creates the table listing available moves.
    def _create_actions_table(self, legal_moves: list) -> Table:
        """Creates a Rich Table for the list of available actions."""
        table = Table(title="[bold]Available Actions[/bold]", show_header=True, header_style="bold magenta", box=None)
        table.add_column("Index", justify="center", width=5)
        table.add_column("Action", no_wrap=True)

        for i, move in enumerate(legal_moves, 1):
            table.add_row(f"[{i}]", move[0])
        
        if not legal_moves:
            table.add_row(Text("(No actions available)", style="dim", justify="center"))
            
        return table
        
    def _create_board_table(self, board: list, is_opponent=False) -> Table:
        # This method is unchanged
        table = Table(show_header=True, header_style="bold magenta", box=None)
        if not is_opponent:
            table.add_column("Status", width=7)
        table.add_column("Card Name", style="cyan", no_wrap=True)
        table.add_column("ATK/HP", justify="center")

        for i, unit in enumerate(board):
            if unit:
                card = CARD_DB.get(unit.card_id, {})
                stats = f"{unit.current_attack}/{unit.current_health}"
                if is_opponent:
                    table.add_row(card.get('name'), stats)
                else:
                    status = Text("Ready", style="green") if unit.is_ready else Text("Used", style="dim")
                    table.add_row(status, card.get('name'), stats)
            else:
                table.add_row(f"[{i+1}]", Text("(empty)", style="dim"))
        return table

    def _create_hand_table(self, hand: list) -> Table:
        # This method is unchanged
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Index", justify="center", width=5)
        table.add_column("Card", style="cyan", no_wrap=True)
        
        for i, card_id in enumerate(hand):
            table.add_row(f"[{i+1}]", get_card_line(card_id))
        
        if not hand:
            table.add_row(Text("(empty)", style="dim", justify="center"))
            
        return table

    ## MODIFIED: Major refactor to handle indexed input.
    def _handle_command(self, command_str: str, legal_moves: list):
        """Parses a command and executes it."""
        if command_str == "quit":
            raise EOFError
        elif command_str == "reset":
            self.console.print("[bold yellow]Restarting game...[/bold yellow]")
            self.controller.reset_game()
            time.sleep(1)
            return
        elif command_str == "help":
            self.console.print("[bold]Help:[/bold]\n- Type the number of the action you want to perform.\n- `quit`: Exit the game.\n- `reset`: Start a new game.")
            input("Press Enter to continue...")
            return

        # Try to process the command as a move index
        try:
            move_idx = int(command_str)
            # Check if the number is in the valid range of moves
            if 1 <= move_idx <= len(legal_moves):
                # Retrieve the move (adjusting for zero-based index)
                found_move = legal_moves[move_idx - 1]
                self.controller.process_action(found_move)
            else:
                # Number was valid, but out of range
                self.console.print(f"[bold red]Error: '{move_idx}' is not a valid move index.[/bold red]")
                time.sleep(1.5)
        except ValueError:
            # The input was not a number
            self.console.print(f"[bold red]Invalid command: '{command_str}'. Please enter a number.[/bold red]")
            time.sleep(1.5)

    def _handle_game_over(self):
        # This method is unchanged
        winner_idx = self.controller.game_state.get_winner()
        winner_name = self.controller.game_state.players[winner_idx].name if winner_idx is not None else "DRAW"
        self.console.print(Rule(f"[bold magenta]GAME OVER! Winner: {winner_name}[/bold magenta]"))
        
        completer = WordCompleter(["reset", "quit"], ignore_case=True)
        command = self.session.prompt("> Type 'reset' or 'quit': ", completer=completer)
        
        if command.lower() == 'reset':
            self.controller.reset_game()
