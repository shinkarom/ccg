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

@dataclass
class GameState:
    """The complete, self-contained state of a game at any point in time."""
    players: List[PlayerState]
    current_player_index: int = -1
    turn_number: int = 1
    
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
        
    def get_score(self) -> (float, float):
        """
        Calculates a simple, "eyeball-style" score based on board presence
        and health. Higher score is better.
        Returns a tuple (p0_score, p1_score).
        """
        p0 = self.players[0]
        p1 = self.players[1]
        
        # --- Calculate Player 0's Score ---
        # 1. Threat Score (Board)
        p0_threat_score = 0
        for unit in p0.board:
            # The simple formula: (Attack * 2) + Health
            p0_threat_score += (unit.current_attack * 2) + unit.current_health
        
        # 2. Resilience Score (Health)
        p0_resilience_score = p0.health

        p0_total_score = p0_threat_score + p0_resilience_score

        # --- Calculate Player 1's Score ---
        # 1. Threat Score (Board)
        p1_threat_score = 0
        for unit in p1.board:
            p1_threat_score += (unit.current_attack * 2) + unit.current_health
            
        # 2. Resilience Score (Health)
        p1_resilience_score = p1.health

        p1_total_score = p1_threat_score + p1_resilience_score
        
        # --- Apply Decisive Win Bonus ---
        # This bonus ensures that a game-winning state is always valued highest.
        WINNER_BONUS = 1000
        
        if p1.health <= 0 and p0.health > 0:
            p0_total_score += WINNER_BONUS
        elif p0.health <= 0 and p1.health > 0:
            p1_total_score += WINNER_BONUS
            
        return p0_total_score, p1_total_score