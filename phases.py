from card_database import CARD_DB
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from game_state import GameState, UnitState, UnitCombatStatus
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

        for attacker_slot_idx, attacker in enumerate(player.board):
            if attacker and attacker.is_ready:
                legal_moves.append(('DECLARE_ATTACK', attacker_slot_idx))
             
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

        elif action_type == 'DECLARE_ATTACK':
            attacker_slot_idx = action[1]
            
            # Safety check
            attacker = player.board[attacker_slot_idx]
            if not attacker:
                 raise ValueError("Attempted to attack with an empty slot.")

            attacker.combat_status = UnitCombatStatus.ATTACKING

            original_attacker_idx = state.current_player_index
            
            # Give priority to the defender
            state.current_player_index = 1 - original_attacker_idx
            
            # Transition to the new phase, passing the necessary context
            return DeclareDefenderPhase(
                attacking_player_idx=original_attacker_idx,
                attacker_slot_idx=attacker_slot_idx
            )
        
        elif action_type == "PASS":
            return UpkeepPhase()

        return self

class DeclareDefenderPhase(Phase):
    """
    A temporary phase where the defending player chooses how to handle an incoming attack.
    """
    def __init__(self, attacking_player_idx: int, attacker_slot_idx: int):
        # We need to remember who initiated the attack
        self.attacking_player_idx = attacking_player_idx
        self.attacker_slot_idx = attacker_slot_idx
        
    def get_name(self):
        return "Declare Defender"

    def get_legal_moves(self, state) -> list:
        """Generates the choices for the defender."""
        legal_moves = []
        defender = state.players[state.current_player_index] # The current player IS the defender

        # Option 1: Block with any of your units
        for blocker_slot_idx, unit in enumerate(defender.board):
            if unit: # Can only block with existing units
                legal_moves.append(('ASSIGN_BLOCKER', blocker_slot_idx))

        # Option 2: Take the damage directly
        legal_moves.append(('TAKE_DAMAGE',))

        return legal_moves

    def process_action(self, state, action: tuple) -> 'Phase':
        action_type = action[0]
        
        # Get the attacker and defender from the context stored in the phase and state
        attacker_player = state.players[self.attacking_player_idx]
        defender_player = state.players[1 - self.attacking_player_idx] # The opponent of the attacker
        
        attacker = attacker_player.board[self.attacker_slot_idx]
        blocker = None
        
        if not attacker:
            # Safety check: if the attacker was somehow removed, the attack fizzles.
            print("Attack fizzled: Attacker is no longer on the board.")
            state.current_player_index = self.attacking_player_idx
            return MainPhase()
        elif action_type == 'ASSIGN_BLOCKER':
            blocker_slot_idx = action[1]
            blocker = defender_player.board[blocker_slot_idx]
            
            if blocker:
                blocker.combat_status = UnitCombatStatus.BLOCKING
            
            # Retaliatory combat
            blocker.current_health -= attacker.current_attack
            attacker.current_health -= blocker.current_attack
            
            # Check for deaths
            if attacker.current_health <= 0:
                attacker_player.graveyard.append(attacker.card_id)
                attacker_player.board[self.attacker_slot_idx] = None
            if blocker.current_health <= 0:
                defender_player.graveyard.append(blocker.card_id)
                defender_player.board[blocker_slot_idx] = None

        elif action_type == 'TAKE_DAMAGE':
            defender_player.health -= attacker.current_attack

        attacker.combat_status = UnitCombatStatus.IDLE
        if blocker:
            blocker.combat_status = UnitCombatStatus.IDLE

        # Mark the attacker as exhausted for the rest of their turn
        if attacker:
            attacker.is_ready = False
            
        # KEY: Return control to the original attacker
        state.current_player_index = self.attacking_player_idx
        return MainPhase()