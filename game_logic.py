# game_logic.py (Heavily Updated)

from game_state import GameState, UnitState,PlayerState
from card_database import CARD_DB
from abc import ABC, abstractmethod
from phases import UpkeepPhase
import random
from rich import print

def init_game(decks,opts={},player_names: list[str] = None):
    players = []
    for j, i in enumerate(decks):
        p = PlayerState()
        p.resource = 0
        p.deck = i
        p.number = j+1
        random.shuffle(p.deck)
        players.append(p)
    state = GameState(players=players)
    state.current_phase = UpkeepPhase()
    state.current_phase.on_enter(state)
    return state
