# ui.py (Vertical Layout with a dedicated "Your Hand" Panel)

import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

# Assuming controller.py and card_database.py are in the same directory
from controller import GameController 
from card_database import CARD_DB, get_card_line

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

class GameUI:
    """A simple and robust UI for the single-player deckbuilder."""

    def __init__(self, controller: GameController):
        self.controller = controller
        self.console = Console()
        self.session = PromptSession(auto_suggest=AutoSuggestFromHistory())

    def run(self):
        """The main game loop."""
        while True:
            clear_screen()
            
            legal_moves = self.controller.get_legal_moves()
            self._display_game_state(legal_moves)
            if self.controller.game_state.is_terminal():
                self._handle_game_over()
                continue
            
            # --- UPDATE THIS LINE ---
            meta_commands = ["help", "quit", "reset", "deck", "discard"]
            # --- END UPDATE ---

            completer = WordCompleter(meta_commands, ignore_case=True)
            try:
                command_str = self.session.prompt("> ", completer=completer)
                self._handle_command(command_str.strip().lower(), legal_moves)
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[bold yellow]Quitting game.[/bold yellow]")
                break

    # --- UPDATE THIS METHOD ---
    def _display_game_state(self, legal_moves: list):
        """Renders the game state as a simple vertical list of panels."""
        state = self.controller.game_state
        phase_name = state.current_phase.get_name()
        # --- Create all UI panels ---
        status_panel = self._create_status_panel(state)
        supply_panel = self._create_supply_panel(state)
        hand_panel = self._create_hand_panel(state.hand) # Create the hand panel
        play_area_panel = self._create_play_area_panel(state.play_area)
        actions_panel = self._create_actions_panel(legal_moves)

        # --- Print panels one after another in a logical order ---
        self.console.print(Rule(f"[bold]Coffee Shop Magnate - Day {state.turn_number} - {phase_name}[/bold]"))
        self.console.print(status_panel)
        self.console.print(supply_panel)
        self.console.print(hand_panel) # Display the hand panel
        self.console.print(play_area_panel)
        self.console.print(actions_panel)

    # --- Panel Creation Helpers ---

    def _create_status_panel(self, state) -> Panel:
        """Panel showing player resources and deck counts."""
        status = Text()
        status.append("Cash ($):", style="bold yellow")
        status.append(f" {state.resource_primary}\n", style="bold")
        status.append("Buzz:", style="bold cyan")
        status.append(f" {state.resource_secondary}\n", style="bold")
        status.append("Prestige (PP):", style="bold magenta")
        status.append(f" {state.victory_points}\n\n", style="bold")
        status.append(f"Deck: {len(state.deck)} | Discard: {len(state.discard_pile)} | Hand: {len(state.hand)}", style="dim")
        return Panel(status, title="[green]Business Status[/green]", border_style="green")

    def _create_supply_panel(self, state) -> Panel:
        """Panel showing the cards currently in the supply."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        
        for card_id in state.supply:
            is_affordable = state.resource_primary >= CARD_DB[card_id]['cost']
            line = get_card_line(card_id)
            if not is_affordable:
                line.stylize("dim")
            table.add_row(line)
        
        return Panel(table, title="[yellow]Supplier Catalog[/yellow]", border_style="yellow")

    # --- ADD THIS METHOD ---
    def _create_hand_panel(self, hand: list) -> Panel:
        """A dedicated panel to display the cards in the player's hand."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        
        if not hand:
            table.add_row(Text("(Empty)", style="dim"))
        else:
            for card_id in hand:
                # We don't need to show cost for cards in hand
                table.add_row(get_card_line(card_id, show_cost=False))
                
        return Panel(table, title="[bold cyan]Your Hand[/bold cyan]", border_style="cyan")

    def _create_play_area_panel(self, play_area: list) -> Panel:
        """Panel showing cards played this turn."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        if not play_area:
            table.add_row(Text("(Empty)", style="dim"))
        else:
            for card_id in play_area:
                table.add_row(get_card_line(card_id, show_cost=False))
        return Panel(table, title="[bold]In Play[/bold]")

    def _create_actions_panel(self, legal_moves: list) -> Panel:
        """The main interactive panel listing all numbered, legal moves."""
        table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 1))
        table.add_column("Num", justify="center", style="bold", width=5)
        table.add_column("Action", no_wrap=False)

        for i, move in enumerate(legal_moves, 1):
            table.add_row(f"[{i}]", move[0])
        
        if not legal_moves:
            table.add_row("", Text("(No actions available)", style="dim"))
            
        return Panel(table, title="[bold]Available Actions[/bold]")

    # --- User Input and Game Over Handling (Unchanged) ---
    
    def _show_pile(self, pile: list, pile_name: str):
        """Displays the contents of a given card pile in a panel."""
        self.console.print(Rule(f"Viewing {pile_name}"))
        
        if not pile:
            self.console.print(Text(f"The {pile_name} is empty.", style="dim", justify="center"))
            input("\nPress Enter to continue...")
            return

        # We can create a simple table to list the cards
        table = Table(box=None, show_header=False)
        # Count occurrences of each card
        card_counts = {}
        for card_id in pile:
            card_counts[card_id] = card_counts.get(card_id, 0) + 1
        
        # Display each unique card and its count
        for card_id, count in sorted(card_counts.items(), key=lambda item: CARD_DB[item[0]]['name']):
            count_str = f"{count}x"
            line = get_card_line(card_id)
            table.add_row(f"[bold green]{count_str}[/bold green]", line)
            
        self.console.print(table)
        input("\nPress Enter to continue...")

    # --- UPDATE THIS METHOD ---
    def _handle_command(self, command_str: str, legal_moves: list):
        """Parses a command and executes it."""
        # --- Handle all meta commands first ---
        if command_str == "quit": raise EOFError
        
        if command_str == "reset":
            self.console.print("[bold yellow]Restarting game...[/bold yellow]")
            self.controller.reset_game()
            time.sleep(1)
            return

        if command_str == "help":
            self.console.print("[bold]Help:[/bold]\n- Type the number of the action to perform.")
            self.console.print("- `deck`: View your deck.")
            self.console.print("- `discard`: View your discard pile.")
            self.console.print("- `quit`: Exit the game.")
            self.console.print("- `reset`: Start a new game.")
            input("Press Enter to continue...")
            return

        # --- ADD THIS NEW LOGIC ---
        if command_str == "deck":
            self._show_pile(self.controller.game_state.deck, "Deck")
            # After showing the pile, we don't process a move, so we just return
            # The main loop will then redraw the screen with the same state
            return
            
        if command_str == "discard":
            self._show_pile(self.controller.game_state.discard_pile, "Discard Pile")
            return
        # --- END NEW LOGIC ---

        # --- Handle numbered actions as before ---
        try:
            move_idx = int(command_str) - 1
            if 0 <= move_idx < len(legal_moves):
                found_move_tuple = legal_moves[move_idx][1]
                self.controller.process_action(found_move_tuple)
            else:
                self.console.print(f"[bold red]Error: '{command_str}' is not a valid action number.[/bold red]")
                time.sleep(1.5)
        except (ValueError, IndexError):
            self.console.print(f"[bold red]Invalid command: '{command_str}'.[/bold red]")
            time.sleep(1.5)

    def _handle_game_over(self):
        final_score = self.controller.game_state.victory_points
        self.console.print(Rule(f"[bold magenta]GAME OVER! Final Prestige: {final_score}[/bold magenta]"))
        
        completer = WordCompleter(["reset", "quit"], ignore_case=True)
        command = self.session.prompt("> Type 'reset' or 'quit': ", completer=completer)
        
        if command.lower() == 'reset':
            self.controller.reset_game()
        else:
            raise EOFError
