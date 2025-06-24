from card_database import CARD_DB
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from game_state import GameState, UnitState
if TYPE_CHECKING:
    from game_state import GameState

MAX_HAND_SIZE = 7
# The maximum number of units a player can have on the board.
# A fixed size is important for a predictable state structure.
BOARD_SIZE = 7

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

class DiscardPhase(Phase):
    
    def get_name(self): return "Discard"
    
    def get_legal_moves(self, state) -> list:
        legal_moves = []
        player = state.players[state.current_player_index]
        for i in range(len(player.hand)):
            legal_moves.append(('DISCARD_CARD', i))
        return legal_moves

    def process_action(self, state, action: tuple) -> 'Phase':
        # Apply the discard action
        player = state.players[state.current_player_index]
        hand_index = action[1]
        card_to_discard = player.hand.pop(hand_index)
        player.graveyard.append(card_to_discard)

        if len(player.hand) > MAX_HAND_SIZE:
            return self # Stay in the DiscardPhase
        else:
            return MainPhase() # Transition to the MainPhase

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

        # 2. Individual Attack moves
        # The logic here remains the same, but the indices now refer to
        # stable slot positions, not shifting list indices.
        for attacker_slot_idx, attacker in enumerate(player.board):
            if attacker and attacker.is_ready:
                for defender_slot_idx, defender in enumerate(opponent.board):
                    if defender:
                        legal_moves.append(('ATTACK_UNIT', attacker_slot_idx, defender_slot_idx))
                legal_moves.append(('ATTACK_PLAYER', attacker_slot_idx))
             
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
                is_ready=False
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
            
            player.graveyard.append(card_id)

        elif action_type == 'ATTACK_UNIT':
            attacker_slot_idx, defender_slot_idx = action[1], action[2]
            attacker = player.board[attacker_slot_idx]
            defender = opponent.board[defender_slot_idx]
            
            defender.current_health -= attacker.current_attack
            attacker.current_health -= defender.current_attack
            attacker.is_ready = False

            # KEY CHANGE: When a unit dies, its slot becomes None.
            # The board is NOT resized.
            if attacker.current_health <= 0:
                player.graveyard.append(attacker.card_id)
                player.board[attacker_slot_idx] = None
            if defender.current_health <= 0:
                opponent.graveyard.append(defender.card_id)
                opponent.board[defender_slot_idx] = None
            
            return self
        
        elif action_type == 'ATTACK_PLAYER':
            attacker_slot_idx = action[1]
            attacker = player.board[attacker_slot_idx]
            
            opponent.health -= attacker.current_attack
            attacker.is_ready = False
        
        elif action_type == "PASS":
            return UpkeepPhase()

        return self

class UpkeepPhase(Phase):
    """A phase that runs automatically and transitions immediately."""
    def get_name(self): return "Upkeep"
    
    def get_legal_moves(self, state) -> list:
        # No player decisions are made in this phase.
        return []

    def on_enter(self, state):
        """This phase's logic runs automatically upon entry."""
        
        state.turn_number += 1
        for i in state.players:
            if state.turn_number == 1:
                while len(i.hand) < MAX_HAND_SIZE:
                    #i.hand.append(i.deck.pop()) 
                    i.draw_card()
        
        state.current_player_index = (state.current_player_index+1)%len(state.players)
        player = state.players[state.current_player_index]
        
        player.resource = min(10, player.resource+1)
        
        for unit in player.board: 
            if unit:
                unit.is_ready = True
        
        if len(player.hand) < MAX_HAND_SIZE:
            player.draw_card()
        if len(player.hand) > MAX_HAND_SIZE:
            state.current_phase = DiscardPhase()
        else:
            state.current_phase = MainPhase()
        
        # Immediately run the on_enter for the new phase if it has one
        state.current_phase.on_enter(state)

    def process_action(self, state, action: tuple) -> 'Phase':
        # Should never be called, as there are no legal moves.
        raise Exception("Cannot process action in an automatic phase.")

