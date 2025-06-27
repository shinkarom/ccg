import random
import time
import copy
from typing import Dict, Any, List, Optional, Tuple

# --- Configuration and Utilities ---

DEFAULT_OPTIONS = {
    "total_simulation_limit": 10000,
    "time_limit_ms": 5000,
}

# (deep_merge function remains the same)
def deep_merge(base_dict: dict, update_dict: dict) -> dict:
    for key, value in update_dict.items():
        if isinstance(base_dict.get(key), dict) and isinstance(value, dict):
            deep_merge(base_dict[key], value)
        else:
            base_dict[key] = value
    return base_dict

# --- Main Class ---

class MonteCarloAnalyzer:
    """
    A Monte Carlo simulation tool that analyzes all possible moves by distributing
    a total simulation budget evenly in a round-robin fashion.
    """

    def __init__(self, options: Optional[Dict[str, Any]] = None):
        self.options = copy.deepcopy(DEFAULT_OPTIONS)
        if options:
            self.set_options(options)

    def set_options(self, options: Dict[str, Any]):
        """Updates the analyzer's configuration from a dictionary of options."""
        if not isinstance(options, dict):
            raise TypeError("options must be a dictionary.")
        deep_merge(self.options, options)

    def analyze_moves(self, initial_state: 'GameState') -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        """
        Analyzes all legal moves using a total simulation budget.

        Returns:
            A tuple containing:
            1. The analysis report dictionary for all moves.
            2. A metadata dictionary with total simulations run and time elapsed.
        """
        # --- 1. SETUP FROM OPTIONS ---
        total_simulation_limit = self.options["total_simulation_limit"]
        time_limit_ms = self.options["time_limit_ms"]
        
        start_time = time.time()
        time_limit_sec = time_limit_ms / 1000.0 if time_limit_ms != float("inf") else float("inf")

        try:
            legal_moves = initial_state.get_legal_moves()
            if not legal_moves:
                return {}, {"sims_run": 0, "time_elapsed_ms": 0}
        except Exception as e:
            print(f"Error getting legal moves: {e}")
            return {}, {"sims_run": 0, "time_elapsed_ms": 0}
        
        num_moves = len(legal_moves)
        perspective_player = initial_state.current_player_index
        move_data_map = {str(move): {"move_obj": move, "wins": 0, "sims": 0} for move in legal_moves}
        
        # --- 2. TOTAL BUDGET SIMULATION LOOP ---
        sims_run_count = 0
        while sims_run_count < total_simulation_limit:
            if (time.time() - start_time) > time_limit_sec:
                # No need to print here, the metadata will tell the story
                break

            move_index = sims_run_count % num_moves
            move_obj = legal_moves[move_index]
            
            data = move_data_map[str(move_obj)]
            world_state = initial_state.determinize(perspective_player)
            next_state = world_state.process_action(data["move_obj"])
            winner = self._random_rollout(next_state)
            
            if winner == perspective_player:
                data["wins"] += 1
            data["sims"] += 1
            sims_run_count += 1
        
        time_elapsed_ms = (time.time() - start_time) * 1000

        # --- 3. POST-PROCESSING AND NORMALIZATION ---
        final_report = {}
        total_wins_across_all_moves = sum(stats["wins"] for stats in move_data_map.values())

        for move_str, stats in move_data_map.items():
            win_rate = stats["wins"] / stats["sims"] if stats["sims"] > 0 else 0.0
            win_contribution = stats["wins"] / total_wins_across_all_moves if total_wins_across_all_moves > 0 else 0.0

            final_report[move_str] = {
                "wins": stats["wins"],
                "sims": stats["sims"],
                "win_rate": win_rate,
                "win_contribution": win_contribution
            }
        
        # --- 4. CREATE METADATA AND RETURN ---
        analysis_metadata = {
            "sims_run": sims_run_count,
            "time_elapsed_ms": time_elapsed_ms,
            "limit_reached": "time" if time_elapsed_ms >= time_limit_ms else "simulations"
        }
                
        return final_report, analysis_metadata

    def _random_rollout(self, state: 'GameState') -> Optional[int]:
        """Plays a random game from the given state to the end."""
        current_state = state
        for _ in range(250):
            if current_state.is_terminal():
                return current_state.get_winner_index()
            
            possible_moves = current_state.get_legal_moves()
            if not possible_moves:
                return current_state.get_winner()

            random_move = random.choice(possible_moves)
            current_state = current_state.process_action(random_move)
        
        return None