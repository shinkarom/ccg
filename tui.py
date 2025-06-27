# tui.py (Corrected Command-Line Style Version)

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, RichLog, Input
from textual.binding import Binding
from textual import on

from controller import GameController
from card_database import CARD_DB, get_card_line

class GameScreen(Screen):
    """The main screen where the game is played, styled as a command-line interface."""

    BINDINGS = [
        Binding(key="ctrl+c", action="quit", description="Quit Game"),
    ]
    CSS_PATH = "tui.css"

    def __init__(self, controller: GameController, **kwargs):
        self.controller = controller
        # RENAMED to avoid conflict with the built-in 'log' property.
        self.game_log: RichLog | None = None
        self.command_input: Input | None = None
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="game-log", wrap=True, highlight=True)
        yield Input(placeholder="Type a command and press Enter...", id="command-input")
        yield Footer()

    def on_mount(self) -> None:
        # RENAMED: Cache the widgets with their new attribute names.
        self.game_log = self.query_one(RichLog)
        self.command_input = self.query_one(Input)

        self.game_log.write("[bold cyan]Welcome to the CCG![/bold cyan]")
        self.game_log.write("Type 'help' for a list of commands.")
        self.update_display()
        
        self.command_input.focus()

    def _generate_state_string(self) -> str:
        # This method remains unchanged internally.
        state = self.controller.game_state
        pov_index = state.current_player_index
        opponent = state.players[1 - pov_index]
        player = state.players[pov_index]
        lines = ["\n" + "="*50]
        lines.append(f"[bold red]OPPONENT: {opponent.name}[/bold red]")
        lines.append(f"  Score: {opponent.score} | Res: {opponent.resource} | Hand: {len(opponent.hand)} | Deck: {len(opponent.deck)}")
        lines.append("  Board:")
        if not opponent.board:
            lines.append("    (empty)")
        else:
            for i, unit in enumerate(opponent.board):
                if unit:
                    card = CARD_DB.get(unit.card_id, {})
                    lines.append(f"    [{i+1}] {card.get('name')} ({unit.current_attack}/{unit.current_health})")
                else:
                    lines.append(f"    [{i+1}] (empty)")
        lines.append("-" * 50)
        lines.append(f"[bold green]YOU: {player.name}[/bold green]")
        lines.append(f"  Score: {player.score} | Res: {player.resource} | Hand: {len(player.hand)} | Deck: {len(player.deck)}")
        lines.append("  Board:")
        if not player.board:
            lines.append("    (empty)")
        else:
            for i, unit in enumerate(player.board):
                if unit:
                    card = CARD_DB.get(unit.card_id, {})
                    status = "[bold green]+[/bold green]" if unit.is_ready else "[dim]-[/dim]"
                    lines.append(f"    [{i+1}] {status} {card.get('name')} ({unit.current_attack}/{unit.current_health})")
                else:
                    lines.append(f"    [{i+1}] (empty)")    
        lines.append("  Hand:")
        if not player.hand:
            lines.append("    (empty)")
        else:
            for i, card_id in enumerate(player.hand):
                lines.append(f"    [{i+1}] {get_card_line(card_id)}")
        lines.append("="*50 + "\n")
        return "\n".join(lines)

    def update_display(self):
        """This is the new 'render' function. It prints state to the log."""
        state = self.controller.game_state
        state_string = self._generate_state_string()
        self.game_log.clear()
        self.game_log.write(state_string) # RENAMED

        if state.is_terminal():
            winner_idx = state.get_winner()
            winner_name = state.players[winner_idx].name if winner_idx is not None else "DRAW"
            self.game_log.write(f"[bold magenta]GAME OVER! Winner: {winner_name}[/bold magenta]") # RENAMED
            self.game_log.write("Type 'reset' to play again, or 'quit' to exit.") # RENAMED
            self.command_input.placeholder = "Type 'reset' or 'quit'" # RENAMED
        else:
            is_my_turn = (state.current_player_index == state.current_player_index)
            if is_my_turn:
                self.game_log.write("[bold]Your turn. Available commands:[/bold]") # RENAMED
                legal_moves = self.controller.get_legal_moves()
                for i,move in enumerate(legal_moves):
                    self.game_log.write(f"  [{i+1}] {move[0]}") # RENAMED
                self.command_input.placeholder = "Your move..." # RENAMED
            else:
                self.game_log.write("Waiting for opponent...") # RENAMED
                self.command_input.placeholder = "Waiting..." # RENAMED

    @on(Input.Submitted)
    def handle_command(self, event: Input.Submitted) -> None:
        """Handles commands entered into the Input widget."""
        command = event.value.strip().lower()
        self.command_input.clear() # RENAMED
        
        if not command:
            return

        self.game_log.write(f"> {command}") # RENAMED

        if command == "quit":
            self.app.exit()
            return
        if command == "reset":
            self.controller.reset_game()
            self.game_log.clear() # RENAMED
            self.game_log.write("[bold cyan]New Game Started![/bold cyan]") # RENAMED
            self.update_display()
            return
        if command == "help":
            self.game_log.write("--- Help ---\n'quit': Exit the game.\n'reset': Start a new game.\n'clear': Clear the log.\nTo play, type one of the available commands shown.") # RENAMED
            return
        if command == "clear":
            self.game_log.clear() # RENAMED
            return

        found_move = None
        if not self.controller.game_state.is_terminal():
            for i,move in enumerate(self.controller.get_legal_moves()):
                if command == str(i+1):
                    found_move = move
                    break
        
        if found_move:
            self.controller.process_action(found_move)
            self.update_display()
        else:
            self.game_log.write("[yellow]Invalid command. Type 'help' for options.[/yellow]") # RENAMED
