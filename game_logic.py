# game_setup.py (Updated to be fully data-driven)

import random
from game_state import GameState
from card_database import CARD_DB
from phases import CleanupPhase

# --- Card Definitions ---
# We only need to define the starting deck composition here now.
STARTING_DECK_COMPOSITION = {
    "1": 8,  # 8x Quick Sale
    "2": 2   # 2x Friendly Smile
}

def init_game() -> GameState:
    """
    Initializes a new game, automatically finding staple cards from the database.
    """
    state = GameState()

    # --- THE NEW LOGIC IS HERE ---
    # 1. Dynamically identify all card pools by iterating through the database.
    staple_cards = []
    supply_pool = []
    for card_id, card_data in CARD_DB.items():
        if card_data.get("tag") == "STAPLE":
            staple_cards.append(card_id)
        # Card is a supply card if it's not a starting card and not a staple
        elif card_id not in STARTING_DECK_COMPOSITION:
            supply_pool.append(card_id)
    
    state.staples = staple_cards
    # --- END NEW LOGIC ---

    # 2. Build the player's starting deck.
    starting_deck = []
    for card_id, count in STARTING_DECK_COMPOSITION.items():
        starting_deck.extend([card_id] * count)
    state.deck = starting_deck
    random.shuffle(state.deck)

    # 3. Build and shuffle the supply deck from the calculated pool.
    state.supply_deck = supply_pool
    random.shuffle(state.supply_deck)

    # 4. Create the initial 5-card supply row.
    num_supply_cards = min(5, len(state.supply_deck))
    state.supply = [state.supply_deck.pop() for _ in range(num_supply_cards)]

    # 5. Start the game.
    state.current_phase = CleanupPhase()
    state.current_phase.on_enter(state)

    return state
