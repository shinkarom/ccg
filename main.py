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

def clear_screen():
    """Clears the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def render_game_state(state: GameState, human_player_index: int):
    """Prints the entire game state to the console in a readable format."""
    clear_screen()
    
    player = state.players[human_player_index]
    opponent = state.players[1 - human_player_index]
    is_my_turn = (state.current_player_index == human_player_index)

    print("="*50)
    print(f"--- OPPONENT'S SIDE (Player {1 - human_player_index + 1}) ---")
    print(f"HP: {opponent.health} | Resources: {opponent.resource} | Hand: {len(opponent.hand)}")
    print("Board:")
    for i, unit in enumerate(opponent.board):
        card = CARD_DB[unit.card_id]
        print(f" [{i+1}] {card['name']} ({unit.current_attack}/{unit.current_health})")
    
    print("\n" + "-"*50 + "\n")

    print(f"--- YOUR SIDE (Player {human_player_index + 1}) ---")
    print("Your Board:")
    for i, unit in enumerate(player.board):
        card = CARD_DB[unit.card_id]
        print(f" [{i+1}] {card['name']} ({unit.current_attack}/{unit.current_health})")
    print(f"HP: {player.health} | Resources: {player.resource}")

    print("\nYour Hand:")
    for i, card_id in enumerate(player.hand):
        card = CARD_DB[card_id]
        print(f"  [{i+1}] {card['name']} (Cost: {card['cost']}) - {card['text']}")
    
    print("="*50)
    turn_status = "YOUR TURN" if is_my_turn else "OPPONENT'S TURN"
    print(f"Turn {state.turn_number} | Phase: {state.current_phase.get_name()} | {turn_status}\n")

def get_human_move(state: GameState) -> tuple:
    """Gets a move from a human player by showing a numbered list of legal moves."""
    legal_moves = state.get_legal_moves()
    
    if not legal_moves:
        print("No legal moves available. This shouldn't happen, but ending turn.")
        return ('END_TURN',)

    print("--- Choose Your Action ---")
    for i, move in enumerate(legal_moves):
        print(f"[{i+1}] {move}")
    
    while True:
        try:
            choice = input("Enter the number of your move: ")
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(legal_moves):
                return legal_moves[choice_idx]
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

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
    # --- Main Menu ---
    print("Welcome to the Python CCG!")
    print("1: Player vs AI")
    print("2: AI vs AI")
    
    player_types = []
    human_player_index = 0
    while not player_types:
        mode = input("Choose a game mode (1 or 2): ")
        if mode == '1':
            player_types = ['HUMAN', 'AI']
        elif mode == '2':
            player_types = ['AI', 'AI']
            human_player_index = -1 # No human player
        else:
            print("Invalid choice.")
            
    # --- Game Setup ---
    game_state = game_logic.init_game([generate_quick_deck(40),generate_quick_deck(40)],{})
    ai_opts = {
        "time_limit_ms": 500,
    }
    ai_instances = {
        i: CCG_AI(ai_opts) for i, p_type in enumerate(player_types) if p_type == 'AI'
    }

    # --- Main Game Loop ---
    while True:
        # Check for win condition
        ind = game_state.get_winner_index()
        if ind > -1:
            print("="*50)
            print(f"!!! GAME OVER: Player {1-ind+1} WINS! !!!")
            print("="*50)
            exit()
        elif ind == -2:
            print("="*50)
            print(f"!!! GAME OVER: DRAW! !!!")
            print("="*50)
            exit()

        
        # Render the board
        if human_player_index == -1:
            # For AI vs AI, we can just print a simpler status
            print(f"Turn {game_state.turn_number}, Player {game_state.current_player_index+1}'s turn...")
        
        # Get action based on player type
        p_idx = game_state.current_player_index
        action = None
        if player_types[p_idx] == 'HUMAN':
            render_game_state(game_state, human_player_index)
            action = get_human_move(game_state)
        elif player_types[p_idx] == 'AI':
            print("AI is thinking...")
            ai = ai_instances[p_idx]
            action,rollouts = ai.find_best_move(game_state)
            print(f"After {rollouts} rollouts AI chose: {action}")
            time.sleep(1.5) # Pause to let the human read the AI's move
        
        # Apply the chosen action
        if action:
            game_state = game_state.process_action(action)
        else:
            print("Error: No action was chosen.")
            break
