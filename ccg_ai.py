# mcts_ai.py

import random
import math
import time
from game_state import GameState
import game_logic
import pprint
import numpy as np

class CCG_AI:
    DEFAULT_OPTIONS = {
        "max_score_swing": 100.0,
        "time_limit_ms": 1000,
        "evaluation_limit": float("inf"),
        "time_limit_ms": float("inf"),
        "temperature": 1.0,
        "exploration_weight": 1.41,
        "blunder_chance": 0.0,
        "recon_depth": 10,
        "probes_per_world": 10,
        "temperature": 1.0,
    }
    
    def __init__(self, options: dict = None):
        """
        Initializes the MCTS AI using a dictionary of options.
        Any options not provided will fall back to DEFAULT_OPTIONS.
        """
        # Start with a copy of the defaults
        self.options = self.DEFAULT_OPTIONS.copy()
        
        # If custom options are provided, update the configuration
        if options:
            self.set_options(options)
    
    def set_options(self, options: dict):
        """
        Updates the AI's configuration from a dictionary of options.
        Allows for re-configuring an existing AI instance.
        
        Args:
            options (dict): A dictionary with keys matching those in
                            DEFAULT_OPTIONS to override current settings.
        """
        if not isinstance(options, dict):
            raise TypeError("options must be a dictionary.")
            
        # Update the current options with any new values provided
        self.options.update(options)
    
    def normalize_score_diff(self, my_score: float, opp_score: float) -> float:
        """
        Normalizes a score difference into a 0.0-1.0 reward for MCTS.
        """
        max_score_swing = self.options["max_score_swing"]
        score_difference = my_score - opp_score
        
        clamped_diff = max(-max_score_swing, min(max_score_swing, score_difference))
        shifted_diff = clamped_diff + max_score_swing
        reward = shifted_diff / (2 * max_score_swing)
        return reward

    def choose_final_move(self, move_stats, temperature):
        """
        Selects a final move based on visit counts using a fast, power-scaling method.

        Args:
            move_stats: The dictionary mapping moves to their stats (visits, rewards).
            temperature: The randomness parameter. 0 means pick the best, higher means more random.

        Returns:
            The chosen move.
        """
        if not move_stats:
            return None

        # --- Case 1: Temperature is zero (or close to it) -> Greedy selection ---
        if temperature < 0.01:
            return max(move_stats, key=lambda m: move_stats[m]["visits"])

        # --- Case 2: Temperature is positive -> Power-scaled probabilistic selection ---
        moves = list(move_stats.keys())
        visits = [move_stats[m]["visits"] for m in moves]

        # Calculate weights by raising visits to the power of (1 / temperature)
        # This is much faster than using exp()
        exponent = 1.0 / temperature
        weights = [v ** exponent for v in visits]

        # Check for a case where all weights are zero (can happen with very low visits and high temp)
        if not any(weights):
            # Fallback to the most visited move if all weights round to zero
            return max(move_stats, key=lambda m: move_stats[m]["visits"])

        # Choose a move based on the calculated weights
        chosen_move = random.choices(moves, weights=weights, k=1)[0]
        
        return chosen_move

    def run_recon_playout(self, start_state: 'GameState', depth_limit) -> 'GameState':
        """
        Runs a short, random playout from a given state to explore the near future.

        Returns:
            The GameState after the playout is complete.
        """      
        current_state = start_state.clone() # Work on a copy
        
        for _ in range(depth_limit):
            # If the game ends during the playout, stop immediately.
            if current_state.is_terminal():
                break

            legal_moves = current_state.get_legal_moves()
            if not legal_moves:
                break
            
            # Make a random move.
            # (This could be improved with a lightweight heuristic policy later if desired)
            action = random.choice(legal_moves)
            current_state = current_state.process_action(action)
            
        return current_state
    
    def choose_final_move(self, move_stats: dict, temperature: float):
        """
        Selects a final move based on visit counts using a temperature parameter.

        Args:
            move_stats: The dictionary mapping moves to their stats (visits, rewards).
            temperature: The randomness parameter. 0 means pick the best, higher means more random.

        Returns:
            The chosen move.
        """
        if not move_stats:
            return None

        # --- Case 1: Temperature is zero (or close to it) -> Greedy selection ---
        # This is the "Robot" personality. Always pick the move with the most visits.
        if temperature < 0.01:
            return max(move_stats, key=lambda m: move_stats[m]["visits"])

        # --- Case 2: Temperature is positive -> Probabilistic selection ---
        moves = list(move_stats.keys())
        visits = [move_stats[m]["visits"] for m in moves]

        # Apply temperature to the visit counts
        # We divide by temperature. High temp flattens the distribution, low temp sharpens it.
        scaled_visits = [v / temperature for v in visits]

        # Numerical Stability: Subtract the max value before exponentiating to prevent overflow
        # This doesn't change the final probabilities but makes the math safer.
        max_scaled_visit = max(scaled_visits)
        exp_visits = [math.exp(v - max_scaled_visit) for v in scaled_visits]

        # Create the probability distribution
        total_exp_visits = sum(exp_visits)
        probabilities = [ev / total_exp_visits for ev in exp_visits]

        # Choose a move based on the calculated probabilities
        # random.choices returns a list, so we take the first element.
        chosen_move = random.choices(moves, weights=probabilities, k=1)[0]
        
        return chosen_move
    
    def find_best_move(self, initial_state: 'GameState') -> tuple:
        """
        Finds the best move using a simplified hybrid MCTS.
        It creates multiple worlds (determinizations) and runs one continuous,
        UCT-guided search that persists across all of them.
        """
        # --- 1. SETUP ---
        time_limit = self.options.get("time_limit_ms", 0) / 1000.0 if self.options.get("time_limit_ms") else float('inf')
        evaluation_limit = self.options["evaluation_limit"]
        probes_per_world = self.options["probes_per_world"]
        exploration_constant_C = self.options["exploration_weight"]
        recon_depth_limit = self.options["recon_depth"]

        legal_moves = initial_state.get_legal_moves()
        if not legal_moves: return None, 0
        if len(legal_moves) == 1: return legal_moves[0], 1

        if random.random() < self.options["blunder_chance"]:
            return random.choice(legal_moves), 0

        # --- 2. MASTER STATISTICS (The only stats dictionary needed) ---
        master_move_stats = {
            move: {"visits": 0, "total_reward": 0.0, "total_squared_reward": 0.0}
            for move in legal_moves
        }
        
        start_time = time.time()
        total_evaluation_count = 0
        current_determinized_state = None

        # --- 3. MAIN SEARCH LOOP ---
        # Each iteration is one probe in a continuous search.
        while True:
            if (time.time() - start_time) >= time_limit: break
            if total_evaluation_count >= evaluation_limit: break
            
            # --- a. World Management ---
            # Create a new world (determinization) every 'probes_per_world' iterations.
            if total_evaluation_count % probes_per_world == 0:
                current_determinized_state = initial_state.determinize(initial_state.current_player_index)

            # --- b. Select Move to Probe (using UCB-Tuned on MASTER stats) ---
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
                    ucb_score = avg_reward + exploration_constant_C * exploration_bonus

                if ucb_score > max_ucb_score:
                    max_ucb_score = ucb_score
                    best_move_to_probe = move
            
            # --- c. Perform the Probe ---
            state_after_move = current_determinized_state.process_action(best_move_to_probe)
            final_recon_state = self.run_recon_playout(state_after_move, recon_depth_limit)
            
            p0_score, p1_score = final_recon_state.get_score()
            my_score, opp_score = (p0_score, p1_score) if initial_state.current_player_index == 0 else (p1_score, p0_score)
            reward = self.normalize_score_diff(my_score, opp_score)
            
            # Optional: Your certainty adjustment
            certainty_exp = self.options.get("certainty_exponent", 1.0)
            if certainty_exp != 1.0:
                reward_from_center = reward - 0.5
                adjusted_reward = (math.copysign(abs(reward_from_center)**certainty_exp, reward_from_center)) + 0.5
                reward = adjusted_reward
            
            # --- d. Update MASTER Stats directly ---
            stats = master_move_stats[best_move_to_probe]
            stats["visits"] += 1
            stats["total_reward"] += reward
            stats["total_squared_reward"] += reward ** 2
            total_evaluation_count += 1

        # --- 4. FINAL DECISION ---
        if total_evaluation_count == 0:
            return random.choice(legal_moves), 0

        temperature = self.options["temperature"]

        best_move = self.choose_final_move(master_move_stats, temperature)
            
        return best_move, total_evaluation_count