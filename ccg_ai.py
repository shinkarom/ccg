# mcts_ai.py

import random
import math
import time
from game_state import GameState
import game_logic
import pprint
import numpy as np
import collections
from rich import print

def deep_merge(base_dict, update_dict, create_new=False):
    """
    Recursively merges two dictionaries.

    :param base_dict: The dictionary to be updated.
    :param update_dict: The dictionary with new values.
    :param create_new: If True, returns a new dictionary. Otherwise, modifies base_dict in-place.
    :return: The merged dictionary.
    """
    # Create a new dictionary if requested, otherwise modify in-place
    target_dict = copy.deepcopy(base_dict) if create_new else base_dict

    for key, value in update_dict.items():
        # Use collections.abc.Mapping for broader dictionary-like type checking
        is_mapping = isinstance(target_dict.get(key), collections.abc.Mapping) and \
                     isinstance(value, collections.abc.Mapping)

        if is_mapping:
            # Recurse into the nested dictionary, ensuring it's a new copy if needed
            target_dict[key] = deep_merge(target_dict[key], value, create_new=create_new)
        else:
            # Overwrite the value
            target_dict[key] = copy.deepcopy(value) if create_new else value
            
    return target_dict

class CCG_AI:
    """
    A Monte Carlo-based AI for a Collectible Card Game (CCG).
    This AI uses a hybrid MCTS approach that performs UCB-Tuned searches
    within multiple "determinized" worlds to handle hidden information.
    """
    DEFAULT_OPTIONS = {
        "max_score_swing": 100.0,
        "time_limit_ms": float("inf"),
        "evaluation_limit": float("inf"),
        "exploration_weight": 1.41,
        "temperature": 0.1,
        "blunder_chance": 0.0,
        "certainty_exponent": 1.0,
        "variance_weight": 0.0,
    }
    
    def __init__(self, options: dict = None):
        """Initializes the MCTS AI with a given configuration."""
        self.options = self.DEFAULT_OPTIONS.copy()
        if options:
            self.set_options(options)
    
    def set_options(self, options: dict):
        """Updates the AI's configuration from a dictionary of options."""
        if not isinstance(options, dict):
            raise TypeError("options must be a dictionary.")
        deep_merge(self.options, options)
    
    def normalize_score_diff(self, my_score: float, opp_score: float) -> float:
        """Normalizes a score difference into a 0.0-1.0 reward for MCTS."""
        max_score_swing = self.options["max_score_swing"]
        score_difference = my_score - opp_score
        
        clamped_diff = max(-max_score_swing, min(max_score_swing, score_difference))
        reward = (clamped_diff / max_score_swing + 1) / 2
        return reward

    def _choose_move_with_temperature(self, move_stats: dict, temperature: float):
        """
        Internal helper to select a final move based on visit counts using a fast, power-scaling method.
        """
        if not move_stats: return None

        # Case 1: Greedy selection for zero temperature (or for deterministic personalities)
        if temperature < 0.01:
            return max(move_stats, key=lambda m: move_stats[m]["visits"])

        # Case 2: Power-scaled probabilistic selection
        moves = list(move_stats.keys())
        visits = [move_stats[m]["visits"] for m in moves]
        
        exponent = 1.0 / temperature
        weights = [v ** exponent for v in visits]

        if not any(weights):
            return max(move_stats, key=lambda m: move_stats[m]["visits"])

        return random.choices(moves, weights=weights, k=1)[0]
    
    def find_best_move(self, initial_state: 'GameState') -> tuple:
        """
        Finds the best move using a simplified hybrid MCTS.
        It creates multiple worlds and runs one continuous, UCT-guided search.
        """
        # --- 1. SETUP ---
        # Direct access is safe now that defaults are well-defined.
        if self.options["time_limit_ms"] != float("inf"):
            time_limit = self.options["time_limit_ms"] / 1000.0
        else:
            time_limit = float("inf")
        evaluation_limit = self.options["evaluation_limit"]
        exploration_constant_C = self.options["exploration_weight"]
        variance_weight = self.options["variance_weight"]
        certainty_exp = self.options["certainty_exponent"]

        legal_moves = initial_state.get_legal_moves()
        if not legal_moves: return None, 0
        if len(legal_moves) == 1: return legal_moves[0], 1

        # --- 2. MASTER STATISTICS ---
        master_move_stats = {
            move: {"visits": 0, "total_reward": 0.0, "total_squared_reward": 0.0}
            for move in legal_moves
        }
        
        start_time = time.time()
        total_evaluation_count = 0
        current_determinized_state = None
        player_index = initial_state.current_player_index
        # --- 3. MAIN SEARCH LOOP ---
        while True:
            if (time.time() - start_time) >= time_limit: 
                print((time.time() - start_time),time_limit)
                break
            if total_evaluation_count >= evaluation_limit: break
            current_determinized_state = initial_state.determinize(initial_state.current_player_index)

            # --- b. Select Move to Probe (using UCB-Tuned) ---
            best_move_to_probe = None
            max_ucb_score = -float('inf')

            for move, stats in master_move_stats.items():
                if stats["visits"] == 0:
                    ucb_score = float('inf')
                else:
                    avg_reward = stats["total_reward"] / stats["visits"]
                    avg_squared_reward = stats["total_squared_reward"] / stats["visits"]
                    variance = max(0, avg_squared_reward - (avg_reward ** 2))
                    exploration_bonus = math.sqrt((math.log(total_evaluation_count + 1) / stats["visits"]) * min(0.25, variance))
                    variance_bias = variance_weight * variance
                    ucb_score = avg_reward + variance_bias + exploration_constant_C * exploration_bonus

                if ucb_score > max_ucb_score:
                    max_ucb_score = ucb_score
                    best_move_to_probe = move
            
            # --- c. Perform the Probe ---
            state_after_move = current_determinized_state.process_action(best_move_to_probe)
            while not state_after_move.is_terminal():
                legal_moves = state_after_move.get_legal_moves()
                
                if not legal_moves:
                    break
                action = random.choice(legal_moves)  
               # print(f"applying {action}")  
                state_after_move = state_after_move.process_action(action)
              #  for i in state_after_move.players:
              #      print(f"player {i.number} has {i.health} health")
             #   print("after turn ",state_after_move.turn_number,"winner?",state_after_move.get_winner_index())
            
            reward = 1 if state_after_move.get_winner_index == player_index else 0
            
            certainty_exp = self.options["certainty_exponent"]
            if certainty_exp != 1.0:
                reward_from_center = reward - 0.5
                adjusted_reward = (math.copysign(abs(reward_from_center)**certainty_exp, reward_from_center)) + 0.5
                reward = adjusted_reward
            
            # --- d. Update MASTER Stats ---
            stats = master_move_stats[best_move_to_probe]
            stats["visits"] += 1
            stats["total_reward"] += reward
            stats["total_squared_reward"] += reward ** 2
            total_evaluation_count += 1

        # --- 4. FINAL DECISION ---
        if total_evaluation_count == 0:
            return random.choice(legal_moves), 0

        # First, find the best move according to the temperature setting.
        temperature = self.options["temperature"]
        best_move = self._choose_move_with_temperature(master_move_stats, temperature)
            
        # Then, after all work is done, check if the AI should make a blunder.
        if random.random() < self.options["blunder_chance"]:
            return random.choice(legal_moves), total_evaluation_count

        return best_move, total_evaluation_count