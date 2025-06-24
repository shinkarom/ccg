import random
import cardgen

def generate_quick_deck(deck_size: int = 30) -> list[int]:
    """
    Creates a random deck of a given size by picking cards from the CARD_DB.
    This is a simple replacement for a hardcoded deck list.
    """
    deck = []
    for _ in range(deck_size):
        c = cardgen.generate_card()
        deck.append(c)
    
    return deck