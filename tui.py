# ui.py (Rewritten for the Single-Player Deckbuilder)

import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.layout import Layout
from rich.live import Live
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

# Assuming controller.py and card_database.py are in the same directory
from controller import GameController 
from card_database import get_card_line

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

class GameUI:
    """A comfortable REPL-style UI for the single-player deckbuilder."""

    def __init__(self, controller: GameController):
        self.controller = controller
        self.console = Console()
        self.session = PromptSession(auto_suggest=AutoSuggestFromHistory())

    def run(self):
        """The main game loop."""
        while True:
            clear_screen()
            
            # Fetch legal moves before displaying state and getting input
            legal_moves = self.controller.get_legal_moves()

            self._display_game_state(legal_moves)

            if self.controller.game_state.is_terminal():
                self._handle_game_over()
                # The controller handles the reset, so we just continue the loop
                continue
            
            # The completer now only suggests meta-commands
            meta_commands = ["help", "quit", "reset"]
            completer = WordCompleter(meta_commands, ignore_case=True)

            try:
                command_str = self.session.prompt("> ", completer=completer)
                self._handle_command(command_str.strip().lower(), legal_moves)
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[bold yellow]Quitting game.[/bold yellow]")
                break

    def _display_game_state(self, legal_moves: list):
        """Renders the entire game state using a Rich Layout."""
        state = self.controller.game_state

        # --- Create all UI panels ---
        status_panel = self._create_status_panel(state)
        supply_panel = self._create_supply_panel(state.supply)
        play_area_panel = self._create_play_area_panel(state.play_area)
        hand_panel = self._create_hand_panel(state.hand)
        actions_panel = self._create_actions_panel(legal_moves)

        # --- Assemble layout ---
        # Top section: status and market
        top_layout = Layout(name="top")
        top_layout.split_row(status_panel, supply_panel)
        
        # Middle section: play area and hand
        middle_layout = Layout(name="middle")
        middle_layout.split_row(play_area_panel, hand_panel)

        # Main layout
        main_layout = Layout()
        main_layout.split_column(
            Layout(top_layout, name="header", size=7),
            Layout(middle_layout, name="body"),
            Layout(actions_panel, name="footer", size=12)
        )
        
        self.console.print(Rule(f"[bold]Coffee Shop Magnate - Day {state.turn_number}[/bold]"))
        self.console.print(main_layout)

    # --- Panel Creation Helpers ---

    def _create_status_panel(self, state) -> Panel:
        """Panel showing player resources and deck counts."""
        # Build a Text object programmatically instead of parsing a string
        status = Text()
        status.append("Cash ($):", style="bold yellow")
        status.append(f" {state.resource_primary}\n", style="bold")
        
        status.append("Buzz:", style="bold cyan")
        status.append(f" {state.resource_secondary}\n", style="bold")
        
        status.append("Prestige (PP):", style="bold magenta")
        status.append(f" {state.victory_points}\n\n", style="bold")
        
        status.append(f"Deck: {len(state.deck)} | Discard: {len(state.discard_pile)}", style="dim")

        return Panel(
            status,
            title="[green]Business Status[/green]",
            border_style="green"
        )

    def _create_supply_panel(self, supply: list) -> Panel:
        """Panel showing the cards available for purchase."""
        table = Table(show_header=False, box=None)
        for card_id in supply:
            table.add_row(get_card_line(card_id))
        
        return Panel(table, title="[yellow]Supplier Catalog[/yellow]", border_style="yellow")

    def _create_play_area_panel(self, play_area: list) -> Panel:
        """Panel showing cards played this turn."""
        table = Table(show_header=False, box=None)
        if not play_area:
            table.add_row(Text("(Empty)", style="dim"))
        else:
            for card_id in play_area:
                table.add_row(get_card_line(card_id, show_cost=False))
        
        return Panel(table, title="[bold]In Play[/bold]")

    def _create_hand_panel(self, hand: list) -> Panel:
        """Panel showing cards in the player's hand."""
        table = Table(show_header=False, box=None)
        if not hand:
             table.add_row(Text("(Empty)", style="dim"))
        else:
            for card_id in hand:
                table.add_row(get_card_line(card_id))
        
        return Panel(table, title="[bold cyan]Your Hand[/bold cyan]", border_style="cyan")

    def _create_actions_panel(self, legal_moves: list) -> Panel:
        """Panel listing all available, numbered actions."""
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Num", justify="center", style="bold", width=5)
        table.add_column("Action", no_wrap=True)

        for i, move in enumerate(legal_moves, 1):
            # move[0] is the rich-formatted Text object from phases.py
            table.add_row(f"[{i}]", move[0])
        
        if not legal_moves:
            table.add_row("", Text("(No actions available)", style="dim"))
            
        return Panel(table, title="[bold]Available Actions[/bold]")

    # --- User Input and Game Over Handling ---

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

        try:
            move_idx = int(command_str)
            if 1 <= move_idx <= len(legal_moves):
                found_move = legal_moves[move_idx - 1]
                self.controller.process_action(found_move)
            else:
                self.console.print(f"[bold red]Error: '{move_idx}' is not a valid action number.[/bold red]")
                time.sleep(1.5)
        except ValueError:
            self.console.print(f"[bold red]Invalid command: '{command_str}'. Please enter a number.[/bold red]")
            time.sleep(1.5)

    def _handle_game_over(self):
        final_score = self.controller.game_state.victory_points
        self.console.print(Rule(f"[bold magenta]GAME OVER! Final Prestige: {final_score}[/bold magenta]"))
        
        completer = WordCompleter(["reset", "quit"], ignore_case=True)
        command = self.session.prompt("> Type 'reset' or 'quit': ", completer=completer)
        
        if command.lower() == 'reset':
            self.controller.reset_game()
        else:
            # We raise EOFError to signal the main loop to exit
            raise EOFError
