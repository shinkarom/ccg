# game_state.py

import copy
import random
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Tuple
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from phases import Phase, UpkeepPhase

@dataclass
class UnitState:
    """Represents a single unit on the board."""
    card_id: int
    current_attack: int
    current_health: int
    keywords: Set[str] = field(default_factory=set)

@dataclass
class PlayerState:
    """Represents all data for one player."""
    health: int = 20
    resource: int = 0
    
    # We store card IDs (integers) not full card objects, to keep the state light.
    deck: List[int] = field(default_factory=list)
    hand: List[int] = field(default_factory=list)
    graveyard: List[int] = field(default_factory=list)
    
    # The board is a fixed-size list, which simplifies AI logic.
    board: List[UnitState] = field(default_factory=list)
    
    def draw_card(self):
        """
        Draws one card, adding it to the hand.
        If the deck is empty, shuffles the graveyard to form a new deck
        before drawing. Does nothing if hand is full or no cards are available.
        """
        # A global constant for max hand size is good practice
        MAX_HAND_SIZE = 7 # Or whatever you have defined

        if len(self.hand) >= MAX_HAND_SIZE:
            # Can't draw if hand is full.
            return

        # --- THE CORE NEW LOGIC ---
        if not self.deck:
            # Deck is empty! Check the graveyard.
            if not self.graveyard:
                # No cards in deck OR graveyard. Cannot draw.
                return
            
            # Reshuffle the graveyard into the deck.
            print(f"Player's deck is empty. Reshuffling {len(self.graveyard)} cards from graveyard.")
            self.deck = self.graveyard
            self.graveyard = [] # The graveyard is now empty
            random.shuffle(self.deck)
        # --- END OF NEW LOGIC ---
        
        # Draw the top card from the deck and add it to the hand.
        card_id = self.deck.pop(0) # pop(0) takes from the "top" of the deck
        self.hand.append(card_id)

@dataclass
class GameState:
    """The complete, self-contained state of a game at any point in time."""
    players: List[PlayerState]
    current_player_index: int = -1
    turn_number: int = 0
    
    current_phase: "Phase" = None
    
    def clone(self) -> 'GameState':
        """
        Creates a deep copy of the game state.
        This is the most critical function for an MCTS AI, allowing it to
        safely explore future moves without altering the real game state.
        """
        return copy.deepcopy(self)
        
    def get_legal_moves(self) -> list:
        """
        Gets legal moves by delegating to the current phase.
        The main loop will call this.
        """
        return self.current_phase.get_legal_moves(self)    
        
    def process_action(self, action: tuple) -> 'GameState':
        """
        Processes an action by delegating to the current phase and returns
        the new, resulting game state. This is the new primary interface
        for advancing the game.
        """
        # 1. Clone the current state to work on a new copy.
        new_state = self.clone()

        # 2. Ask the current phase to process the action on this new state.
        #    This will modify the `new_state` and return the next phase object.
        next_phase = new_state.current_phase.process_action(new_state, action)

        # 3. Assign the new phase to our new state object.
        new_state.current_phase = next_phase
        
        # 4. If the new phase has an on_enter method, call it.
        #    This is how automatic phases like Upkeep will trigger.
        if hasattr(next_phase, 'on_enter'):
            next_phase.on_enter(new_state)

        # 5. Return the fully updated new state.
        return new_state
        
    def get_winner_index(self) -> int:
        """
        Determines if there is a winner and returns their index.
        
        Returns:
            0: If Player 1 has won.
            1: If Player 2 has won.
            -1: If the game is still ongoing.
            -2: If the game is a draw.
        """
        p1 = self.players[0]
        p2 = self.players[1]

        # Check for health-based win/loss conditions
        p1_has_lost = (p1.health <= 0)
        p2_has_lost = (p2.health <= 0)

        if p1_has_lost and p2_has_lost:
            return -2 # Draw condition
        if p1_has_lost:
            return 1 # Player 2 wins
        if p2_has_lost:
            return 0 # Player 1 wins

        # You could add other conditions here, such as fatigue from an empty deck.
        # For example, if a "drew_from_empty_deck" flag was set on the player state:
        # p1_fatigued = p1.drew_from_empty_deck
        # p2_fatigued = p2.drew_from_empty_deck
        # if p1_fatigued: return 1
        # if p2_fatigued: return 0

        # If no win/loss conditions are met, the game continues.
        return -1
        
    def determinize(self, player_index: int) -> 'GameState':
        """
        Creates a plausible, perfect-information state from the perspective of
        the given player_index. This version correctly shuffles decks separately
        to preserve deck counts.
        """
        # 1. Start with a deep copy.
        determined_state = self.clone()
        
        # 2. Get references to the players in the new state.
        p_self = determined_state.players[player_index]
        p_opp = determined_state.players[1 - player_index]
        
        # --- Part A: Determine the Opponent's Hand ---

        # 3. Pool the cards that could possibly be in the opponent's hand.
        #    This is the opponent's actual hand + their deck.
        opponent_hand_pool = []
        opponent_hand_pool.extend(p_opp.hand)
        opponent_hand_pool.extend(p_opp.deck)
        random.shuffle(opponent_hand_pool)
        
        # 4. Clear the opponent's hand and deck to re-deal.
        p_opp.hand = []
        p_opp.deck = []

        # 5. Re-deal the opponent's hand from their shuffled pool.
        opponent_hand_size = len(self.players[1 - player_index].hand)
        for _ in range(opponent_hand_size):
            if opponent_hand_pool:
                p_opp.hand.append(opponent_hand_pool.pop(0))
        
        # 6. The rest of the opponent's pool becomes their new shuffled deck.
        p_opp.deck = opponent_hand_pool
        
        # --- Part B: Shuffle the AI's Own Deck ---
        
        # 7. The AI's hand is KNOWN and is not touched.
        #    We just need to shuffle the contents of its deck.
        random.shuffle(p_self.deck)

        return determined_state
        
    def is_terminal(self) -> bool:
        """
        Checks if the game has reached a terminal state (i.e., a winner has been decided).
        
        This is a convenience wrapper around get_winner_index().
        """
        return self.get_winner_index() != -1
        
    def _calculate_single_player_score(self, player_index: int, weights: dict) -> float:
        """
        Calculates a raw, un-normalized score for a single player based on a given weight dictionary.
        This is the core evaluation helper.
        """
        if not weights: return 0.0

        player = self.players[player_index]
        total_score = 0.0
        
        # --- Resilience Score (Health) ---
        total_score += player.health * weights["health"]

        # --- Threat Score (Board) ---
        board_attack_w = weights["board_attack"]
        board_health_w = weights["board_health"]

        for unit in player.board:
            total_score += (unit.current_attack * board_attack_w)
            total_score += (unit.current_health * board_health_w)
            
        # You could easily add more terms here, e.g., hand size
        # hand_size = len(player.hand)
        # total_score += hand_size * weights.get("hand_w", 0.0)
        
        return total_score    
        
    def get_score(self, eval_weights: dict) -> float:
        """
        Calculates a final, normalized score for MCTS using a personality profile.
        Supports both symmetrical (one dict) and asymmetrical (two dicts) evaluation.
        """
        if self.is_terminal():
            winner = self.get_winner_index()
            if winner == self.current_player_index: return 1.0  # I (current player) won
            if winner is not None: return -1.0 # I (current player) lost
            return 0.0

        my_player_index = self.current_player_index
        opp_player_index = 1 - my_player_index

        my_weights = eval_weights.get("my_eval", {})
        # A more concise way to handle the symmetrical case
        is_symmetrical = eval_weights.get("symmetrical", False)
        opp_weights = my_weights if is_symmetrical else eval_weights.get("opp_eval", {})

        # Step 3: Calculate subjective scores (this part is now more flexible)
        my_subjective_score = self._calculate_single_player_score(my_player_index, my_weights)
        opp_subjective_score = self._calculate_single_player_score(opp_player_index, opp_weights)
        
        raw_score = my_subjective_score - opp_subjective_score

        # Step 4: Normalization (unchanged)
        max_score_swing = eval_weights["max_score_swing"]
        clamped_score = max(-max_score_swing, min(max_score_swing, raw_score))
        normalized_score = clamped_score / max_score_swing
        
        return normalized_score