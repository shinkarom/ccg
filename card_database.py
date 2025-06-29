# card_database.py (Rewritten for the Deckbuilder)

import json
from rich.text import Text

"""
This file loads the master JSON database for all cards in the game.
It also provides helper functions for displaying card information in the UI.
"""

def load_card_database(filepath: str) -> dict:
    """Loads card definitions from a JSON file."""
    try:
        with open(filepath, 'r') as f:
            # Use the json module to load the data
            card_database = json.load(f)
        return card_database
    except FileNotFoundError:
        print(f"[bold red]Error: Card database file not found at '{filepath}'.[/bold red]")
        print("[bold red]Please ensure 'card_database.json' is in the same directory.[/bold red]")
        exit() # Exit the program if cards can't be loaded
    except json.JSONDecodeError:
        print(f"[bold red]Error: Could not parse '{filepath}'. Please check for JSON syntax errors.[/bold red]")
        exit()

# --- Global Card Database ---
# Load the database once when the module is imported.
CARD_DB = load_card_database("card_database.json")


# --- UI Helper Functions ---

def get_card_line(card_id: str, show_cost: bool = True) -> Text:
    """
    Generates a single, rich-formatted line representing a card with uniform styling.
    """
    if card_id not in CARD_DB:
        return Text(f"Unknown Card ID: {card_id}", style="bold red")

    info = CARD_DB[card_id]
    name = info.get("name", "Unnamed Card")
    cost = info.get("cost", 0)
    text = info.get("text", "")

    # Start building the Rich Text object
    card_text = Text()
    
    # --- THE CHANGE IS HERE ---
    # Apply a single, consistent style to all card names.
    # No more color-coding by tag. "bold white" is a great neutral choice.
    card_text.append(f"[{name}]", style="bold white")
    # --- END CHANGE ---

    # Add cost
    if show_cost:
        card_text.append(f" (Cost: {cost})", style="yellow")
    
    # Add descriptive text
    if text:
        card_text.append(f" - {text}", style="dim")

    return card_text

# You can keep this simple function if you just want the name
def get_card_name(card_id: str) -> str:
    """A simple helper to get just the card's name."""
    if card_id not in CARD_DB:
        return "Unknown Card"
    return CARD_DB[card_id].get("name", "Unnamed Card")
