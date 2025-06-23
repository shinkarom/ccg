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
    
    ui.display_welcome()
    mode = ui.get_game_mode()
    
    # --- Mode Setup ---
    if mode == '1':   # PvP
        player_types = ['HUMAN', 'HUMAN']
    elif mode == '2': # PvE
        player_types = ['HUMAN', 'AI']
    else:             # AvA
        player_types = ['AI', 'AI']
            
    human_player_index = player_types.index('HUMAN') if 'HUMAN' in player_types else -1
            
    # --- Game Setup ---
    game_state = game_logic.init_game([generate_quick_deck(40), generate_quick_deck(40)])
    
    # AI instances are only created if needed
    ai_instances = {
        i: CCG_AI({"time_limit_ms": 500}) 
        for i, p_type in enumerate(player_types) if p_type == 'AI'
    }

    # --- Main Game Loop ---
    previous_player_idx = -1 

    while True:
        # 1. Check for Game Over.
        winner_index = game_state.get_winner_index()
        if winner_index != -1:
            # Determine final POV for rendering
            pov_index_at_end = human_player_index if mode == '2' else previous_player_idx
            ui.render_game_state(game_state, pov_index_at_end)
            ui.display_game_over(winner_index)
            break
        
        current_player_idx = game_state.current_player_index
        
        # 2. Universal "Press Enter" prompt driven by priority change.
        if current_player_idx != previous_player_idx:
            ui.prompt_for_priority(current_player_idx + 1)
        
        previous_player_idx = current_player_idx
        
        # 3. --- THE CORRECTED, MODE-AWARE RENDERING LOGIC ---
        pov_to_render = -1
        if mode == '1' or mode == '3': # PvP or AvA
            # In these modes, we always render from the current player's perspective.
            pov_to_render = current_player_idx
        else: # mode == '2', Player vs. AI
            # In PvE, we ALWAYS render from the human's perspective.
            pov_to_render = human_player_index
            
        ui.render_game_state(game_state, pov_to_render)
        # --- END OF CORRECTED LOGIC ---
        
        # 4. Get the action from the correct player type.
        action = None
        if player_types[current_player_idx] == 'HUMAN':
            action = ui.get_human_move(game_state)
        else: # AI's turn
            ai = ai_instances[current_player_idx]
            action, rollouts = ai.find_best_move(game_state)
            # We don't need to re-render here, just announce the move.
            ui.display_ai_move(action, rollouts)
        
        # 5. Apply the action to get the new state.
        if action:
            if action == ("QUIT_GAME",):
                break;
            
            game_state = game_state.process_action(action)
        else:
            print("Error: No action was chosen or available. Exiting.")
            break