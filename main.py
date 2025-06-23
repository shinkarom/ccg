# main.py (Print-Based Console Version)

import os
import random
import time

# Our core game logic and AI
from game_state import GameState, PlayerState
from phases import UpkeepPhase
from card_database import CARD_DB
import game_logic
from ccg_ai import CCG_AI
from ui import ConsoleUI

def generate_quick_deck(deck_size: int = 30) -> list[int]:
    """
    Creates a random deck of a given size by picking cards from the CARD_DB.
    This is a simple replacement for a hardcoded deck list.
    """
    # Get all possible card IDs from your database.
    all_card_ids = list(CARD_DB.keys())
    
    # Randomly choose `deck_size` cards from the list, with replacement.
    # 'choices' is perfect for this, as it allows duplicates naturally.
    deck = random.choices(all_card_ids, k=deck_size)
    
    return deck

if __name__ == "__main__":
    ui = ConsoleUI()
    
    # --- Main Menu ---
    ui.display_welcome()
    mode = ui.get_game_mode()
    
    # --- Mode Setup ---
    if mode == '1': # Player vs Player
        player_types = ['HUMAN', 'HUMAN']
    elif mode == '2': # Player vs AI
        player_types = ['HUMAN', 'AI']
    else: # mode == '3', AI vs AI
        player_types = ['AI', 'AI']
            
    # --- Game Setup ---
    game_state = game_logic.init_game([generate_quick_deck(40), generate_quick_deck(40)])
    
    # AI instances are only created if needed
    ai_instances = {
        i: CCG_AI({"time_limit_ms": 500}) 
        for i, p_type in enumerate(player_types) if p_type == 'AI'
    }

    # --- Main Game Loop ---
    while True:
        winner_index = game_state.get_winner_index()
        if winner_index != -1:
            # For PvP, we need to know whose perspective to render the final state from
            final_pov = 0 if game_state.current_player_index == 1 else 1
            ui.render_game_state(game_state, final_pov)
            ui.display_game_over(winner_index)
            break

        current_player_idx = game_state.current_player_index
        action = None

        # --- Get move based on player type ---
        if player_types[current_player_idx] == 'HUMAN':
            # For PvP, announce the turn change and wait for the next player
            if player_types[0] == 'HUMAN' and player_types[1] == 'HUMAN':
                input(f"\nPlayer {current_player_idx + 1}, your turn is ready. Press Enter to continue...")

            ui.render_game_state(game_state, current_player_idx)
            action = ui.get_human_move(game_state)
        else: # AI's turn
            # Render from the perspective of the human opponent, if one exists
            human_opponent_idx = 1 - current_player_idx if 'HUMAN' in player_types else -1
            if human_opponent_idx != -1:
                 ui.render_game_state(game_state, human_opponent_idx)
            else: # AI vs AI
                 print(f"Turn {game_state.turn_number}, Player {current_player_idx+1}'s turn...")


            ai = ai_instances[current_player_idx]
            action, rollouts = ai.find_best_move(game_state)
            ui.display_ai_move(action, rollouts)
        
        # Apply the chosen action
        if action:
            game_state = game_state.process_action(action)
        else:
            print("Error: No action was chosen. Exiting.")
            break