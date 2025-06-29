# game_setup.py (New and Improved)

import random
from game_state import GameState
from card_database import CARD_DB
from phases import MainPhase, CleanupPhase # Using the new phases

# Define the roles of each card based on the database
STARTING_DECK_COMPOSITION = {
    "1": 8,  # 8x Quick Sale
    "2": 2   # 2x Friendly Smile
}
STAPLE_CARD_IDS = ["10", "11"] # Bulk Coffee Beans, Loyal Customer

# Dynamically find all other cards to form the supply deck
ALL_CARD_IDS = set(CARD_DB.keys())
STARTING_CARD_IDS = set(STARTING_DECK_COMPOSITION.keys())
SUPPLY_CARD_IDS = list(ALL_CARD_IDS - STARTING_CARD_IDS - set(STAPLE_CARD_IDS))

def init_game() -> GameState:
    state = GameState()
    
    # Setup player's starting deck
    starting_deck = []
    for card_id, count in STARTING_DECK_COMPOSITION.items():
        starting_deck.extend([card_id] * count)
    state.deck = starting_deck
    random.shuffle(state.deck)
    
    # Setup staples
    state.staples = STAPLE_CARD_IDS
    
    # Setup the supply
    state.supply_deck = SUPPLY_CARD_IDS.copy()
    random.shuffle(state.supply_deck)
    num_supply_cards = min(5, len(state.supply_deck))
    state.supply = [state.supply_deck.pop() for _ in range(num_supply_cards)]

    # Start the game
    state.current_phase = CleanupPhase()
    state.current_phase.on_enter(state)

    return state