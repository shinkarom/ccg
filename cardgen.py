from card_database import CARD_DB
import random

def generate_card():
    all_card_ids = list(CARD_DB.keys())
    return random.choice(all_card_ids)