# phases.py (Completely Rewritten for the Single-Player Deckbuilder)

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from card_database import CARD_DB, get_card_line # Assuming you have a helper for formatted card text
from rich.text import Text

if TYPE_CHECKING:
    from game_state import GameState

# --- Base Class (Unchanged) ---
class Phase(ABC):
    """An abstract base class for a phase in the game."""
    
    @abstractmethod
    def get_name(self) -> str:
        """Gets the phase name."""
        pass
    
    @abstractmethod
    def get_legal_moves(self, state: 'GameState') -> list:
        """Generates all legal moves for the player in this phase."""
        pass

    @abstractmethod
    def process_action(self, state: 'GameState', action: tuple) -> 'Phase':
        """Processes an action and returns the next phase of the game."""
        pass

    def on_enter(self, state: 'GameState'):
        """Optional: Code to run when the game enters this phase."""
        pass

# --- Concrete Phase Implementations for the Deckbuilder ---

class MainPhase(Phase):
    """
    The primary, interactive phase. Generates a single list of all legal moves.
    """
    def get_name(self) -> str:
        return "Main Phase"

    def get_legal_moves(self, state: 'GameState') -> list:
        """Generates a single, unified list of all possible actions."""
        legal_moves = []

        # 1. Generate moves for playing cards from hand
        for hand_idx, card_id in enumerate(state.hand):
            card_line = get_card_line(card_id, show_cost=False)
            desc = Text("Play ")
            desc.append(card_line)
            legal_moves.append((desc, ('PLAY_CARD', hand_idx)))

        # 2. Generate moves for buying cards from the supply
        for supply_idx, card_id in enumerate(state.supply):
            card_info = CARD_DB[card_id]
            if state.resource_primary >= card_info['cost']:
                card_line = get_card_line(card_id)
                desc = Text("Buy ")
                desc.append(card_line)
                legal_moves.append((desc, ('BUY_CARD', supply_idx)))
        
        # --- THE FIX IS HERE ---
        # 3. Generate moves for buying STAPLE cards
        for staple_idx, card_id in enumerate(state.staples):
            card_info = CARD_DB[card_id]
            if state.resource_primary >= card_info['cost']:
                card_line = get_card_line(card_id)
                desc = Text("Buy Staple: ") # Use different text for clarity
                desc.append(card_line)
                # Use a new action type to distinguish from a regular supply buy
                legal_moves.append((desc, ('BUY_STAPLE', staple_idx)))
        # --- END FIX ---

        # 4. Add the move to end the turn
        legal_moves.append((Text("End Turn", style="bold"), ('END_TURN',)))
        
        return legal_moves

    def process_action(self, state: 'GameState', action: tuple) -> 'Phase':
        """Processes a play, buy, or end_turn action."""
        action_type = action[0]

        if action_type == 'PLAY_CARD':
            hand_idx = action[1]
            card_id = state.hand.pop(hand_idx)
            state.play_area.append(card_id)
            state.eval_effects(card_id)
            return self

        elif action_type == 'BUY_CARD':
            supply_idx = action[1]
            card_id = state.supply[supply_idx]
            card_info = CARD_DB[card_id]
            state.resource_primary -= card_info['cost']
            state.discard_pile.append(card_id)

            if state.supply_deck:
                new_card_id = state.supply_deck.pop(0)
                state.supply[supply_idx] = new_card_id
            else:
                state.supply.pop(supply_idx)
            return self

        # --- THE FIX IS HERE ---
        elif action_type == 'BUY_STAPLE':
            staple_idx = action[1]
            card_id = state.staples[staple_idx]
            card_info = CARD_DB[card_id]

            # Perform the transaction
            state.resource_primary -= card_info['cost']
            state.discard_pile.append(card_id)
            
            # CRUCIALLY: Do NOT remove the staple. They are infinitely available.
            return self
        # --- END FIX ---

        elif action_type == 'END_TURN':
            return CleanupPhase()
        
        raise ValueError(f"Unknown action in MainPhase: {action}")


class CleanupPhase(Phase):
    """
    An automatic phase that cleans up the turn and sets up the next one.
    This is the "engine" of the deckbuilder loop.
    """
    def get_name(self): 
        return "Cleanup"
    
    def get_legal_moves(self, state: 'GameState') -> list:
        # No player decisions are made in this phase.
        return []

    def on_enter(self, state: 'GameState'):
        """This phase's logic runs automatically upon entry."""
        
        # 1. Move all cards from play area and hand to the discard pile.
        state.discard_pile.extend(state.play_area)
        state.play_area.clear()
        
        state.discard_pile.extend(state.hand)
        state.hand.clear()

        # 2. Reset turn-based resources.
        state.resource_primary = 0
        state.resource_secondary = 0
        
        # 3. Draw 5 new cards for the next turn.
        for _ in range(5):
            state.draw_card()
            
        # 4. Increment turn number.
        state.turn_number += 1

        # 5. Automatically transition to the next MainPhase.
        state.current_phase = MainPhase()
        state.current_phase.on_enter(state) # Though MainPhase.on_enter does nothing currently

    def process_action(self, state: 'GameState', action: tuple) -> 'Phase':
        # Should never be called, as there are no legal moves.
        raise Exception("Cannot process action in an automatic phase.")
