# card_database.py

"""
This file holds the master definitions for all cards in the game.
The key is an integer Card ID.
The value is a dictionary holding the card's static properties.

Effects are stored as data tuples, e.g., ('EFFECT_NAME', value), which the
game engine will know how to interpret. This is crucial for an MCTS AI,
as it doesn't need to execute arbitrary code during simulations.
"""

# We'll use simple, primitive types for all card properties.
CARD_DB = {
    # --- UNITS ---
    1: {
        'id': 1,
        'name': "Rock Golem",
        'type': 'UNIT',
        'cost': 1,
        'attack': 1,
        'health': 2,
        'keywords': set(),
        'text': "A basic, sturdy unit."
    },
    2: {
        'id': 2,
        'name': "Guard Golem",
        'type': 'UNIT',
        'cost': 3,
        'attack': 2,
        'health': 4,
        'keywords': {'TAUNT'},  # Taunt forces enemies to attack this unit.
        'text': "Taunt."
    },
    3: {
        'id': 3,
        'name': "Large Golem",
        'type': 'UNIT',
        'cost': 2,
        'attack': 1,
        'health': 3,
        'keywords': set(), 
        'text': "Improved Golem."
    },
    4: {
        'id': 4,
        'name': "Even Larger Golem",
        'type': 'UNIT',
        'cost': 4,
        'attack': 3,
        'health': 3,
        'keywords': set(), 
        'text': "Next Gen Golem."
    },

    # --- ACTIONS ---
    101: {
        'id': 101,
        'name': "Energy Surge",
        'type': 'ACTION',
        'cost': 1,
        'effect': ('DRAW_CARDS', 1),
        'text': "Draw a card."
    },
    102: {
        'id': 102,
        'name': "Direct Hit",
        'type': 'ACTION',
        'cost': 2,
        'effect': ('DEAL_DAMAGE', 3), # Deals 3 damage to a target.
        'text': "Deal 3 damage."
    }
}
