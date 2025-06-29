# game_state.py (Completely Rewritten for the Single-Player Deckbuilder)

import copy
import random
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING
from card_database import CARD_DB
from typing import List, Set
if TYPE_CHECKING:
    from phases import Phase

# --- The Unified Game State ---

@dataclass
class GameState:
    """
    A theme-agnostic, self-contained state for a single-player deckbuilder.
    This class holds all data for the game and knows how to resolve card effects.
    """
    
    # --- Permanent State ---
    victory_points: int = 0
    turn_number: int = 0
    
    # --- Resource Pools (Reset each turn) ---
    resource_primary: int = 0
    resource_secondary: int = 0
    
    # --- Card Piles ---
    deck: List[str] = field(default_factory=list)
    hand: List[str] = field(default_factory=list)
    discard_pile: List[str] = field(default_factory=list)
    play_area: List[str] = field(default_factory=list)
    trash_pile: List[str] = field(default_factory=list)
    # --- Supply (The Market) ---
    supply: List[str] = field(default_factory=list)
    supply_deck: List[str] = field(default_factory=list)
    staples: List[str] = field(default_factory=list)

    triggered_indices: Set[int] = field(default_factory=set)
    play_area_trash_indices: Set[int] = field(default_factory=set)

    # --- Game Flow ---
    current_phase: "Phase" = None

    def clone(self) -> 'GameState':
        """Creates a deep copy of the game state for safe simulation."""
        return copy.deepcopy(self)

    # --- Core Gameplay Methods ---

    def draw_card(self):
        """Draws a single card, reshuffling the discard pile if the deck is empty."""
        if not self.deck:
            if not self.discard_pile:
                return  # Cannot draw, both piles are empty
            
            # Reshuffle discard pile into deck
            self.deck = self.discard_pile
            self.discard_pile = []
            random.shuffle(self.deck)
        
        if self.deck:
            card_id = self.deck.pop(0)
            self.hand.append(card_id)

    def eval_effects(self, card_id: str):
        """
        Resolves the effects of a played card. This is the heart of the engine.
        """
        card_info = CARD_DB.get(card_id)
        if not card_info:
            print(f"Warning: Card ID '{card_id}' not found in database.")
            return

        # --- Resolve Primary Ability ---
        primary_effects = card_info.get("primary_ability", [])
        for effect in primary_effects:
            self._apply_effect(effect)

        # --- Check and Resolve Tag Bonus (e.g., Synergy/Ally) ---
        tag_bonus = card_info.get("tag_bonus")
        if tag_bonus:
            played_card_tag = card_info.get("tag")
            # Check other cards in the play area, excluding the one just played
            for other_card_id in self.play_area[:-1]:
                other_card_info = CARD_DB.get(other_card_id, {})
                if other_card_info.get("tag") == played_card_tag:
                    # Found a match, apply the bonus effects and stop looking
                    for effect in tag_bonus.get("effects", []):
                        self._apply_effect(effect)
                    break # Only need one match to trigger the bonus

    def _apply_effect(self, effect: dict):
        """A helper method to apply a single, atomic effect dictionary."""
        effect_type = effect.get("type")
        value = effect.get("value", 0)

        if effect_type == "ADD_RESOURCE_PRIMARY":
            self.resource_primary += value
        elif effect_type == "ADD_RESOURCE_SECONDARY":
            self.resource_secondary += value
        elif effect_type == "ADD_VICTORY_POINTS":
            self.victory_points += value
        elif effect_type == "DRAW_CARDS":
            for _ in range(value):
                self.draw_card()
        elif effect_type == "SELF_TRASH":
            # This effect can only happen from a card in play.
            if played_card_index != -1:
                self.play_area_trash_indices.add(played_card_index)
            else:
                print(f"Warning: SELF_TRASH effect called without a valid index.")
        elif effect_type == "TRASH_FROM_HAND":
            # The game state doesn't know how to ask the user which card to trash.
            # So, we tell the current phase to handle a 'TRASH_FROM_HAND' action.
            # We clone the state to avoid modifying it during this pseudo-action.
            temp_state = self.clone()
            next_phase = temp_state.current_phase.process_action(temp_state, ('TRASH_FROM_HAND', value))
            
            # Now, we manually update the *real* state's phase.
            # This is a bit of a hack, but it's the cleanest way to inject a
            # state change from within an effect resolution.
            self.current_phase = next_phase
        # Add more effect types here as needed (e.g., TRASH_CARD, etc.)
        else:
            print(f"Warning: Unknown effect type '{effect_type}'")

    # --- Game Flow & State Management ---

    def get_legal_moves(self) -> list:
        """Delegates getting legal moves to the current phase."""
        if self.is_terminal():
            return []
        return self.current_phase.get_legal_moves(self)    
        
    def process_action(self, action: tuple) -> 'GameState':
        """
        Processes an action by delegating to the current phase.
        This is the main way the game state advances.
        """
        new_state = self.clone()
        next_phase = new_state.current_phase.process_action(new_state, action)
        new_state.current_phase = next_phase
        
        # If the new phase has an on_enter method, call it.
        # This is how CleanupPhase automatically runs its logic.
        if hasattr(next_phase, 'on_enter'):
            next_phase.on_enter(new_state)

        return new_state

    def is_terminal(self) -> bool:
        """Checks if the game has reached a terminal state."""
        # Example win condition: reaching 50 VP
        if self.victory_points >= 50:
            return True
        # Example loss condition: supply deck is empty and supply row is empty
        if not self.supply_deck and not self.supply:
            return True
        # Example turn limit
        if self.turn_number > 40:
             return True
             
        return False
