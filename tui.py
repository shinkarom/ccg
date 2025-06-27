# tui.py (Backwards-Compatible Version)

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, RichLog
# We will explicitly use these containers for layout
from textual.containers import Vertical, Horizontal

# Import the controller and game state for type hinting
from controller import GameController
from game_state import PlayerState, UnitCombatStatus
from card_database import CARD_DB, get_card_line

class PlayerPane(Static):
    """A widget to display a single player's side of the board. (No changes needed here)"""
    def update_view(self, player_state: PlayerState, is_pov: bool):
        pov_label = "(YOU)" if is_pov else "(OPPONENT)"
        stats = f"Score: {player_state.score} | Res: {player_state.resource} | Hand: {len(player_state.hand)} | Deck: {len(player_state.deck)}"
        board_lines = []
        for i, unit in enumerate(player_state.board):
            if unit:
                card = CARD_DB.get(unit.card_id, {})
                if unit.is_ready: status = "[green]+[/green]"
                else: status = "[dim]-[/dim]"
                board_lines.append(f"  [{i+1}] {status} {card.get('name')} ({unit.current_attack}/{unit.current_health})")
        board_str = "\n".join(board_lines) if board_lines else "  (empty)"
        hand_lines = []
        if is_pov:
            for card_id in player_state.hand:
                hand_lines.append(f"  - {get_card_line(card_id)}")
        hand_str = "\n".join(hand_lines) if hand_lines else "  (empty)"
        self.update(f"[bold]{player_state.name.upper()} {pov_label}[/bold]\n{stats}\n\nBoard:\n{board_str}\n\nHand:\n{hand_str}")


class GameScreen(Screen):
    """The main screen where the game is played."""

    # We link the simplified CSS file
    CSS_PATH = "tui.css"

    def __init__(self, controller: GameController, **kwargs):
        self.controller = controller
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        """
        Compose the layout using nested containers.
        This is the backwards-compatible approach.
        """
        yield Header()
        
        # A main vertical container for the log, board, and actions
        with Vertical():
            yield RichLog(id="game-log")
            
            # A horizontal container for the two player panes
            with Horizontal(id="board-area"):
                yield PlayerPane(id="opponent-pane")
                yield PlayerPane(id="player-pane")

            # A vertical container for the action buttons at the bottom
            yield Vertical(id="action-area")
        
        yield Footer()

    # The on_mount, on_button_pressed, and update_display methods remain
    # exactly the same. The logic inside them doesn't change, only the
    # layout that they are modifying. I'm including them here for completeness.

    def on_mount(self) -> None:
        """Called when the screen is first mounted. Initial setup."""
        self.query_one("#game-log", RichLog).write("Game Started!")
        self.update_display()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles all button clicks and triggers game logic."""
        action_area = self.query_one("#action-area")
        action_area.disabled = True # Prevent double-clicks

        if hasattr(event.button, "move_data"):
            move = event.button.move_data
            self.query_one("#game-log", RichLog).write(f"Action: {move[0]}")
            self.controller.process_action(move)
            self.update_display()
        elif event.button.id == "play-again-button":
            self.controller.reset_game()
            self.query_one("#game-log", RichLog).clear()
            self.query_one("#game-log", RichLog).write("New Game Started!")
            self.update_display()
        elif event.button.id == "quit-button":
            self.app.exit()

    def update_display(self):
        """This is the new 'render' function. It updates all widgets."""
        state = self.controller.game_state
        pov_index = state.current_player_index
        
        self.query_one("#opponent-pane", PlayerPane).update_view(state.players[1 - pov_index], is_pov=False)
        self.query_one("#player-pane", PlayerPane).update_view(state.players[pov_index], is_pov=True)

        action_area = self.query_one("#action-area")
        action_area.remove_children()

        if state.is_terminal():
            winner_idx = state.get_winner()
            winner_name = state.players[winner_idx].name if winner_idx is not None else "DRAW"
            action_area.mount(Static(f"[bold magenta]GAME OVER! Winner: {winner_name}[/bold magenta]"))
            action_area.mount(Button("Play Again", variant="success", id="play-again-button"))
            action_area.mount(Button("Quit", variant="error", id="quit-button"))
        else:
            if state.current_player_index == pov_index:
                legal_moves = self.controller.get_legal_moves()
                for move in legal_moves:
                    button = Button(label=str(move[0]), variant="primary")
                    button.move_data = move
                    action_area.mount(button)
            else:
                action_area.mount(Static("Waiting for opponent..."))
        
        action_area.disabled = False
