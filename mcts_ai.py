# mcts_ai.py

import random
import math
import time
from game_state import GameState
import game_logic
import pprint

RAVE_EQUIVALENCE = 350
SOLVER_ITERATIONS = 10

class MCTSNode:
    def __init__(self, game_state: 'GameState', parent=None, action=None):
        self.game_state = game_state
        self.parent = parent
        self.action = action
        self.children = []

        self.wins = 0.0
        self.visits = 0

        # RAVE stats are removed as they depend on simulations.
        
        self.untried_actions = self.game_state.get_legal_moves()
        random.shuffle(self.untried_actions)

    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0

    def expand(self) -> 'MCTSNode':
        action = self.untried_actions.pop()
        next_state = self.game_state.process_action(action)
        child_node = MCTSNode(next_state, parent=self, action=action)
        self.children.append(child_node)
        return child_node

    def best_child(self, exploration_weight=1.41):
        """Selects the best child using the standard UCB1 (UCT) formula."""
        best_score = -1
        best_children = []
        for child in self.children:
            if child.visits == 0:
                # Unvisited children have an infinite score and must be selected.
                return child

            # Standard UCT formula: exploitation + exploration
            exploit_score = child.wins / child.visits
            explore_score = exploration_weight * math.sqrt(math.log(self.visits) / child.visits)
            
            final_score = exploit_score + explore_score
            
            if final_score > best_score:
                best_score = final_score
                best_children = [child]
            elif final_score == best_score:
                best_children.append(child)
        return random.choice(best_children)

class MCTS_AI:
    def __init__(self, solver_iterations=50, time_limit_ms=1000):
        self.time_limit = time_limit_ms / 1000.0
        # This is a tunable parameter for normalizing the score difference.
        # It should be a reasonable estimate of a large, but not game-winning,
        # score advantage. A good starting point is 2x-3x a starting health total.
        self.MAX_SCORE_SWING = 100.0

    def normalize_score_diff(self, my_score: float, opp_score: float) -> float:
        """
        Normalizes a score difference into a 0.0-1.0 reward for MCTS.
        """
        score_difference = my_score - opp_score
        
        clamped_diff = max(-self.MAX_SCORE_SWING, min(self.MAX_SCORE_SWING, score_difference))
        shifted_diff = clamped_diff + self.MAX_SCORE_SWING
        reward = shifted_diff / (2 * self.MAX_SCORE_SWING)
        return reward

    def backpropagate(self, leaf_node: MCTSNode, reward_for_search_player: float):
        """
        A simplified backpropagation that takes a pre-calculated reward.
        It updates the path from the leaf node up to the root.
        """
        node = leaf_node
        while node is not None:
            # Determine the reward from the perspective of the player at the current node
            if node.game_state.current_player_index == leaf_node.game_state.current_player_index:
                current_reward = reward_for_search_player
            else:
                current_reward = 1.0 - reward_for_search_player

            # Update the node's statistics
            node.visits += 1
            node.wins += current_reward
            
            node = node.parent

    def find_best_move(self, initial_state: 'GameState') -> tuple:
        """
        Finds the best move using MCTS with a direct state evaluation function
        (`get_score`) instead of random simulations.
        """
        real_legal_moves = initial_state.get_legal_moves()
        if not real_legal_moves: return None, 0
        if len(real_legal_moves) == 1: return real_legal_moves[0], 1

        master_move_stats = {move: {"wins": 0.0, "visits": 0} for move in real_legal_moves}
        
        start_time = time.time()
        total_evaluation_count = 0

        while time.time() - start_time < self.time_limit:
            
            # Create a temporary tree for one search path
            determinate_state = initial_state.determinize(initial_state.current_player_index)
            solver_root = MCTSNode(game_state=determinate_state)
            
            total_evaluation_count += 1

            # --- SELECTION & EXPANSION ---
            node = solver_root
            while not node.game_state.is_terminal(): # Or another condition to stop descent
                if not node.is_fully_expanded():
                    # Expansion: Add a new child to the tree
                    node = node.expand()
                    break
                else:
                    # Selection: Choose the best child to explore further
                    node = node.best_child()
            
            # --- EVALUATION (Replaces Simulation) ---
            # Instead of a random playout, we directly ask the game state for its score.
            # This is the leaf node we will evaluate.
            p0_score, p1_score = node.game_state.get_score()

            # Determine which score belongs to the player whose turn it is
            if initial_state.current_player_index == 0:
                my_score, opp_score = p0_score, p1_score
            else:
                my_score, opp_score = p1_score, p0_score
            
            # Normalize the score difference into a 0.0-1.0 reward for MCTS
            reward = self.normalize_score_diff(my_score, opp_score)
            
            # --- BACKPROPAGATION ---
            # Update the temporary tree with the calculated reward.
            self.backpropagate(node, reward)
            
            # --- AGGREGATE RESULTS ---
            # (Note: This aggregation is now less critical than in a rollout-based MCTS,
            # but still useful. We only update the stats for the first move taken).
            if solver_root.children:
                first_move_node = solver_root.children[0]
                move = first_move_node.action
                if move in master_move_stats:
                     master_move_stats[move]["visits"] += first_move_node.visits
                     master_move_stats[move]["wins"] += first_move_node.wins

        # --- FINAL DECISION ---
        if total_evaluation_count == 0:
            return random.choice(real_legal_moves), 0

        # Choose the move that led to the highest average score (win rate).
        # We check for visits > 0 to avoid division by zero.
        best_move = max(
            master_move_stats,
            key=lambda m: (master_move_stats[m]["wins"] / master_move_stats[m]["visits"])
            if master_move_stats[m]["visits"] > 0 else -1
        )
        
        return best_move, total_evaluation_count