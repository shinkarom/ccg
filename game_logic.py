# game_logic.py (Heavily Updated)

from game_state import GameState, UnitState,PlayerState
from card_database import CARD_DB
from abc import ABC, abstractmethod
from phases import UpkeepPhase
import random

def init_game(decks,opts={}):
    players = []
    for i in decks:
        p = PlayerState()
        p.resource = 0
        p.deck = i
        random.shuffle(p.deck)
        players.append(p)
    state = GameState(players=players)
    state.current_phase = UpkeepPhase()
    state.current_phase.on_enter(state)
    return state

def get_legal_moves(state: GameState) -> list:
    return state.current_phase.get_legal_moves(state)

def apply_action(state: GameState, action: tuple) -> GameState:
    """The main entry point for applying an action. Delegates to the current phase."""
    new_state = state.clone()
    # The phase object itself calculates and sets the next phase.
    next_phase = new_state.current_phase.process_action(new_state, action)
    if new_state.current_phase != next_phase:
        new_state.current_phase = next_phase
        new_state.current_phase.on_enter(new_state) # Trigger on_enter for the new phase
    return new_state
