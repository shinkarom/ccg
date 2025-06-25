from card_database import CARD_DB
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from game_state import GameState, UnitState, UnitCombatStatus
from shared import *
import random
if TYPE_CHECKING:
    from game_state import GameState

from rich import print

# --- Base Class ---
class Phase(ABC):
    """An abstract base class for a phase in the game."""
    
    @abstractmethod
    def get_name(self) -> str:
        """Gets the phase name."""
        pass
    
    @abstractmethod
    def get_legal_moves(self, state) -> list:
        """Generates all legal moves for the current player in this phase."""
        pass

    @abstractmethod
    def process_action(self, state, action: tuple) -> 'Phase':
        """Processes an action and returns the next phase of the game."""
        pass

    def on_enter(self, state):
        """Optional: Code to run when the game enters this phase."""
        pass

# --- Concrete Phase Implementations ---

class UpkeepPhase(Phase):
    """A phase that runs automatically and transitions immediately."""
    def get_name(self): return "Upkeep"
    
    def get_legal_moves(self, state) -> list:
        # No player decisions are made in this phase.
        return []

    def on_enter(self, state):
        """This phase's logic runs automatically upon entry."""
        
        state.turn_number += 1
        state.current_player_index = (state.current_player_index+1)%len(state.players)
        player = state.players[state.current_player_index]
        
        player.resource = min(10, player.resource+1)
        
        for unit in player.board: 
            if unit:
                unit.is_ready = True
                
        for i in state.players:
            state.deck.extend(i.hand)
            i.hand.clear()
        random.shuffle(state.deck)
        for i in state.players:        
            while state.deck and len(i.hand) < MAX_HAND_SIZE:
                state.draw_card(i)
        state.current_phase = MainPhase()
        state.current_phase.on_enter(state)

    def process_action(self, state, action: tuple) -> 'Phase':
        # Should never be called, as there are no legal moves.
        raise Exception("Cannot process action in an automatic phase.")


class MainPhase(Phase):
    def get_name(self): return "Main"
    
    def get_legal_moves(self, state) -> list:
        # This is your familiar "Develop or Deploy" logic
        legal_moves = []
        player = state.players[state.current_player_index]
        opponent = state.players[1-state.current_player_index]
        for hand_idx, card_id in enumerate(player.hand):
            card_info = CARD_DB[card_id]
            if player.resource >= card_info['cost']:
                if card_info['type'] == 'UNIT':
                    # KEY CHANGE: Generate a move for EACH empty slot
                    for slot_idx, slot in enumerate(player.board):
                        if slot is None:
                            # The move now includes the target slot index
                            legal_moves.append(('PLAY_UNIT', hand_idx, slot_idx))
                elif card_info['type'] == 'ACTION':
                    legal_moves.append(('PLAY_ACTION', hand_idx))
             
        legal_moves.append(('PASS', ))
        
        return legal_moves

    def process_action(self, state, action: tuple) -> 'Phase':
        """
        Processes a main phase action, then transitions to the next player's turn.
        """
        # --- 1. Apply the specific effect of the chosen action ---
        
        action_type = action[0]
        player = state.players[state.current_player_index]
        opponent = state.players[1-state.current_player_index]
        if action_type == 'PLAY_UNIT':
            
            # KEY CHANGE: Unpack the target slot index from the action
            hand_idx, slot_idx = action[1], action[2]
            
            card_id = player.hand.pop(hand_idx)
            card_info = CARD_DB[card_id]
            player.resource -= card_info['cost']
            
            unit = UnitState(
                card_id=card_id,
                current_attack=card_info['attack'],
                current_health=card_info['health'],
                is_ready=False,
                keywords = card_info["keywords"]
            )
            # KEY CHANGE: Place the unit in the specified slot
            player.board[slot_idx] = unit
        elif action_type == 'PLAY_ACTION':
            ind = action[1]
            
            # --- VALIDATION PHASE ---
            # 1. Validate hand index.
            if ind >= len(player.hand):
                raise IndexError(f"MCTS Desync: Tried to play from hand index {ind}, but hand size is {len(player.hand)}. Hand: {player.hand}")
                
            card_id = player.hand[ind]
            # It's good practice to handle potential DB errors, though MCTS assumes a valid state.
            card_info = CARD_DB.get(card_id) 
            if not card_info:
                raise KeyError(f"MCTS Desync: Card ID '{card_id}' not found in CARD_DB.")

            # 2. Validate resource cost.
            if player.resource < card_info['cost']:
                raise ValueError(f"MCTS Desync: Tried to play card {card_id} with cost {card_info['cost']}, but player only has {player.resource} resources.")

            player.hand.pop(ind)
            
            # b. Pay cost and move to graveyard.
            player.resource -= card_info['cost']
            
            state.graveyard.append(card_id)
        
        elif action_type == "PASS":
            return CombatPhase()

        return CombatPhase()

class CombatPhase(Phase):
    def get_name(self):
        return "Combat"
        
    def on_enter(self, state):
        player1 = state.players[0]
        player2 = state.players[1]
        for i in range(BOARD_SIZE):
            u1 = player1.board[i]
            u2 = player2.board[i]
            if not u1 and not u2:
                continue
            if not u1:
                player1.health -= u2.current_attack
                continue
            if not u2:
                player2.health -= u1.current_attack
                continue
            u1.current_health -= u2.current_attack
            u2.current_health -= u1.current_attack
            if u1.current_health <= 0:
                state.graveyard.append(u1.card_id)
                player1.board[i] = None
            if u2.current_health <= 0:
                state.graveyard.append(u2.card_id)
                player2.board[i] = None
        
        state.current_phase = UpkeepPhase()
        state.current_phase.on_enter(state)
        
    def get_legal_moves(self, state) -> list:
        return []
        
    def process_action(self, state, action: tuple) -> 'Phase':
        raise Exception("Cannot process action in an automatic phase.")
        
        