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
            while i.deck and len(i.hand) < MAX_HAND_SIZE:
                i.draw_card()
        state.current_phase = MainPhase()
        state.current_phase.on_enter(state)

    def process_action(self, state, action: tuple) -> 'Phase':
        # Should never be called, as there are no legal moves.
        raise Exception("Cannot process action in an automatic phase.")


class MainPhase(Phase):
    def get_name(self): return "Main"
    
    def get_legal_moves(self, state) -> list:
        # This is your familiar "Develop or Deploy" logic
        playable = set()
        legal_moves = []
        player = state.players[state.current_player_index]
        opponent = state.players[1-state.current_player_index]
        first_slot = -1
        for hand_idx, card_id in enumerate(player.hand):
            if card_id in playable:
                continue
            card_info = CARD_DB[card_id]
            if player.resource >= card_info['cost']:
                if (card_info['type'] == 'UNIT'):
                    # KEY CHANGE: Generate a move for EACH empty slot
                    playable.add(card_id)
                    name = card_info["name"]
                    desc = f"Play [green]{name}[/green]"
                    legal_moves.append((desc,'PLAY_UNIT', hand_idx))
                elif card_info['type'] == 'ACTION':
                    playable.add(card_id)
                    name = card_info["name"]
                    desc = f"Play [green]{name}[/green]"
                    legal_moves.append((desc,'PLAY_ACTION', hand_idx))
             
        legal_moves.append(("Pass",'PASS', ))
        
        return legal_moves

    def process_action(self, state, action: tuple) -> 'Phase':
        """
        Processes a main phase action, then transitions to the next player's turn.
        """
        # --- 1. Apply the specific effect of the chosen action ---
        
        action_type = action[1]
        player = state.players[state.current_player_index]
        opponent = state.players[1-state.current_player_index]
        if action_type == 'PLAY_UNIT':
            
            # KEY CHANGE: Unpack the target slot index from the action
            hand_idx = action[2]
            card_id = player.hand.pop(hand_idx)
            card_info = CARD_DB[card_id]
            player.resource -= card_info['cost']
            eff = card_info.get("effects", [])
            if eff:
                state.eval_effects(eff, card_id)
            unit = UnitState(
                card_id=card_id,
                current_attack=card_info['attack'],
                current_health=card_info['health'],
                is_ready=False,
                keywords = card_info["keywords"]
            )
            # KEY CHANGE: Place the unit in the specified slot
            player.board.append(unit)
        elif action_type == 'PLAY_ACTION':
            ind = action[2]
            
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
        
            eff = card_info.get("effects", [])
            if eff:
                state.eval_effects(eff, card_id)
        
        elif action_type == "PASS":
            pass
        
        if state.turn_number %2 == 0:
            return CombatPhase()
        else:
            return UpkeepPhase()

class CombatPhase(Phase):
    def get_name(self):
        return "Combat"
        
    def on_enter(self, state: 'GameState'):
        """
        Resolves combat between players' boards.
        This version assumes player.board is a dynamic list of UnitState objects.
        """
        player1 = state.players[0]
        player2 = state.players[1]
        
        # --- 1. DAMAGE CALCULATION ---
        # Determine the length of the "front line" for combat.
        # It's the smaller of the two board sizes.
        combat_len = min(len(player1.board), len(player2.board))

        for i in range(combat_len):
            u1 = player1.board[i]
            u2 = player2.board[i]
            
            # Units deal damage to each other simultaneously.
            u1.current_health -= u2.current_attack
            u2.current_health -= u1.current_attack
        
        # Unopposed units deal damage directly to the opponent's score.
        # Check if player 1 has more units than player 2.
        if len(player1.board) > combat_len:
            for i in range(combat_len, len(player1.board)):
                player1.score += 2 # Or use a different value for direct damage
        
        # Check if player 2 has more units than player 1.
        if len(player2.board) > combat_len:
            for i in range(combat_len, len(player2.board)):
                player2.score += 2


        # --- 2. CLEANUP & SCORE ---
        # We build new lists containing only the survivors.

        survivors_p1 = []
        for unit in player1.board:
            if unit.current_health > 0:
                survivors_p1.append(unit)
            else:
                # The unit was defeated. Add to graveyard and score for opponent.
                player1.graveyard.append(unit.card_id)
                player2.score += 1
        
        survivors_p2 = []
        for unit in player2.board:
            if unit.current_health > 0:
                survivors_p2.append(unit)
            else:
                # The unit was defeated. Add to graveyard and score for opponent.
                player2.graveyard.append(unit.card_id)
                player1.score += 1

        # --- 3. UPDATE BOARD STATE ---
        # Replace the old boards with the new lists of survivors.
        player1.board = survivors_p1
        player2.board = survivors_p2

        # --- 4. TRANSITION TO NEXT PHASE ---
        state.current_phase = UpkeepPhase()
        state.current_phase.on_enter(state)
        
    def get_legal_moves(self, state) -> list:
        return []
        
    def process_action(self, state, action: tuple) -> 'Phase':
        raise Exception("Cannot process action in an automatic phase.")
        
        