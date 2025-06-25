# game_logic.py (Heavily Updated)

from game_state import GameState, UnitState,PlayerState
from card_database import CARD_DB
from abc import ABC, abstractmethod
from phases import UpkeepPhase
import random
from rich import print

def init_game(decks,opts={}):
    players = []
    for j, i in enumerate(decks):
        p = PlayerState()
        p.resource = 0
        p.number = j+1
        players.append(p)
    state = GameState(players=players)
    for i in decks:
        state.deck.extend(i)
    state.current_phase = UpkeepPhase()
    state.current_phase.on_enter(state)
    return state
