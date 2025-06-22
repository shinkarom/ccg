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
