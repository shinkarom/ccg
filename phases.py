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
        for i, card_id in enumerate(player.hand):
            card_info = CARD_DB[card_id]
            if player.resource >= card_info['cost']:
                if card_info['type'] == 'UNIT':
                    if len(player.board)<BOARD_SIZE-1:
                        legal_moves.append(('PLAY_UNIT', i))
                elif card_info['type'] == 'ACTION':
                    # Simplified targeting
                    legal_moves.append(('PLAY_ACTION', i))

        # --- Attacking with ready units ---
        if any(u for u in player.board if u is not None):
             legal_moves.append(('ATTACK_ALL',))
             
        #if not legal_moves:
        legal_moves.append(('PASS',))
            
        return legal_moves

    def process_action(self, state, action: tuple) -> 'Phase':
        """
        Processes a main phase action, then transitions to the next player's turn.
        """
        # --- 1. Apply the specific effect of the chosen action ---
        
        action_type = action[0]
        player = state.players[state.current_player_index]

        if action_type in ('PLAY_UNIT', 'PLAY_ACTION'):
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
            
            # c. Put the unit on the board if applicable.
            if action_type == 'PLAY_UNIT':
                u = UnitState(
                    card_id=card_id,
                    current_attack=card_info['attack'],
                    current_health=card_info['health'],
                    # Robustly handle optional keywords and create a copy to prevent aliasing.
                    keywords=card_info.get('keywords', set()).copy()
                )
                player.board.append(u)

        elif action_type == 'ATTACK_ALL':
            player = state.players[state.current_player_index]
            opponent = state.players[1 - state.current_player_index]

            # --- Step 1: Calculate total incoming damage from all ready attackers ---
            total_incoming_damage = 0
            for unit in player.board:
                if unit:
                    total_incoming_damage += unit.current_attack
                    unit.is_ready = False # Attacking exhausts them, this is correct.

            # --- Step 2: Opponent's board absorbs the damage ---
            # We iterate through the opponent's board to apply damage.
            # A copy is needed if we modify the list while looping, e.g. `for unit in opponent.board[:]:`
            # but here we just modify unit health, which is fine.
            for target_unit in opponent.board:
                if target_unit and total_incoming_damage > 0:
                    # The target unit takes damage up to its health
                    damage_to_deal = min(total_incoming_damage, target_unit.current_health)
                    
                    target_unit.current_health -= damage_to_deal
                    total_incoming_damage -= damage_to_deal # Reduce the damage pool

            # --- Step 3: Remove any units that died ---
            # We need to build a new board list to avoid mutation-during-iteration issues.
            new_opponent_board = []
            for unit in opponent.board:
                if unit: # Check if the slot had a unit
                    if unit.current_health > 0:
                        new_opponent_board.append(unit)
                    else:
                        # The unit died, put it in the graveyard
                        opponent.graveyard.append(unit.card_id)
                else:
                    new_opponent_board.append(None) # The slot was already empty
            
            r = len(new_opponent_board) - len(opponent.board)
            if r > 0:
                print(f"COMBAT REPORT: {r} units neutralized.")
            
            # Replace the old board with the new one
            opponent.board = new_opponent_board

            # --- Step 4: Any leftover damage hits the opponent's hero ---
            if total_incoming_damage > 0:
                opponent.health -= total_incoming_damage
            
        elif action_type == 'PASS':
            # This is a forced pass, so no action effect is applied.
            pass

        return UpkeepPhase()

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
                    i.hand.append(i.deck.pop()) 
        
        state.current_player_index = (state.current_player_index+1)%len(state.players)
        player = state.players[state.current_player_index]
        
        if state.turn_number != 1:
            while len(player.hand) < MAX_HAND_SIZE:
                player.hand.append(player.deck.pop())         
        
        player.resource = min(10, player.resource + 1)
        # 2. Set the next phase based on the result
        
        if len(player.hand) > MAX_HAND_SIZE:
            state.current_phase = DiscardPhase()
        else:
            state.current_phase = MainPhase()
        
        # Immediately run the on_enter for the new phase if it has one
        state.current_phase.on_enter(state)

    def process_action(self, state, action: tuple) -> 'Phase':
        # Should never be called, as there are no legal moves.
        raise Exception("Cannot process action in an automatic phase.")

