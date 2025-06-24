# card_database.py
from rich import print
import json
"""
This file holds the master definitions for all cards in the game.
The key is an integer Card ID.
The value is a dictionary holding the card's static properties.

Effects are stored as data tuples, e.g., ('EFFECT_NAME', value), which the
game engine will know how to interpret. This is crucial for an MCTS AI,
as it doesn't need to execute arbitrary code during simulations.
"""

def load_card_database(filepath: str):
    """
    Loads card definitions from a JSON file.
    """
    card_database = {}
    with open(filepath, 'r') as f:
        data = json.load(f)

    for card_id, card_data in data.items():
        card_database[card_id] = card_data
        
    return card_database

# We'll use simple, primitive types for all card properties.
CARD_DB = load_card_database("card_database.json")