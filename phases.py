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
        
        for i, card_id in enumerate(state.play_area):
            # Check if this card's trigger has already been used this turn
            if i in state.triggered_indices:
                continue

            card_info = CARD_DB[card_id]
            trigger_info = card_info.get("trigger_ability")
            
            # Check if the card has a trigger and if we can afford it
            if trigger_info and state.resource_secondary >= trigger_info['cost_value']:
                card_name = card_info['name']
                cost = trigger_info['cost_value']
                # Create a clear description for the UI
                desc = Text(f"Trigger {card_name} (Cost: {cost} Buzz)")
                legal_moves.append((desc, ('TRIGGER_ABILITY', i)))

        # 4. Add the move to end the turn
        legal_moves.append((Text("End Turn", style="bold"), ('END_TURN', None)))
        
        return legal_moves

    def process_action(self, state: 'GameState', action: tuple) -> 'Phase':
        """Processes a play, buy, or end_turn action."""
        # This is a much safer way to handle the action tuple.
        action_type = action[0]

        if action_type == 'PLAY_CARD':
            hand_idx = action[1]
            card_id = state.hand.pop(hand_idx)
            state.eval_effects(card_id)
            state.play_area.append(card_id)
            return self

        elif action_type == 'BUY_CARD':
            supply_idx = action[1]
            card_id = state.supply[supply_idx]
            card_info = CARD_DB[card_id]
            state.resource_primary -= card_info['cost']
            state.discard_pile.append(card_id)
            if state.supply_deck:
                state.supply[supply_idx] = state.supply_deck.pop(0)
            else:
                state.supply.pop(supply_idx)
            return self

        elif action_type == 'BUY_STAPLE':
            staple_idx = action[1]
            card_id = state.staples[staple_idx]
            card_info = CARD_DB[card_id]
            state.resource_primary -= card_info['cost']
            state.discard_pile.append(card_id)
            return self
            
        elif action_type == 'TRIGGER_ABILITY':
            play_area_idx = action[1]
            card_id = state.play_area[play_area_idx]
            card_info = CARD_DB[card_id]
            trigger_info = card_info["trigger_ability"]
            state.resource_secondary -= trigger_info['cost_value']
            state.triggered_indices.add(play_area_idx)
            for effect in trigger_info["effects"]:
                state._apply_effect(effect, played_card_index=play_area_idx)
            return self

        elif action_type == 'TRASH_FROM_HAND':
             return TrashCardPhase(origin_phase=self)

        elif action_type == 'END_TURN':
            # This action has no second element, but that's fine now.
            return CleanupPhase()
        
        # This will only be reached if an unknown action type is passed.
        raise ValueError(f"Unknown action type in MainPhase: {action_type}")

class TrashCardPhase(Phase):
    """
    A special, temporary phase entered to resolve a "trash a card" effect.
    """
    def __init__(self, origin_phase: Phase):
        # We store the phase we came from so we can return to it.
        self.origin_phase = origin_phase

    def get_name(self) -> str:
        return "Trashing Card"

    def get_legal_moves(self, state: 'GameState') -> list:
        """The only legal moves are choosing a card from hand to trash."""
        legal_moves = []
        for i, card_id in enumerate(state.hand):
            card_line = get_card_line(card_id, show_cost=False)
            desc = Text("Trash ")
            desc.append(card_line)
            legal_moves.append((desc, ('TRASH_CARD', i)))
        
        # Optionally, add a "Cancel" action
        legal_moves.append((Text("Cancel Trashing", style="bold dim"), ('CANCEL_TRASH',)))
        return legal_moves

    def process_action(self, state: 'GameState', action: tuple) -> 'Phase':
        action_type, idx = action[0], action[1] if len(action) > 1 else None

        if action_type == 'TRASH_CARD':
            # Move the chosen card from hand to the trash pile
            card_to_trash = state.hand.pop(idx)
            state.trash_pile.append(card_to_trash)
        
        # Whether we trashed or cancelled, we return to the phase we came from.
        return self.origin_phase


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
        
        new_play_area = []
        # Sort indices in reverse to avoid messing up subsequent indices when popping.
        indices_to_trash = sorted(list(state.play_area_trash_indices), reverse=True)

        for i in indices_to_trash:
            # Pop the card from its index and add it to the trash pile.
            trashed_card = state.play_area.pop(i)
            state.trash_pile.append(trashed_card)
        
        # 1. Move all cards from play area and hand to the discard pile.
        state.discard_pile.extend(state.play_area)
        state.play_area.clear()
        
        state.discard_pile.extend(state.hand)
        state.hand.clear()
        
        state.triggered_indices.clear()
        
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
