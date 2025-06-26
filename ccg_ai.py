import random
import math
import time
import copy # <-- Added missing import
import collections.abc
from rich import print

# Assuming GameState, game_logic are defined elsewhere as in your original code.

DEFAULT_OPTIONS = {
    "max_score_swing": 100.0,
    "time_limit_ms": float("inf"),
    "evaluation_limit": float("inf"),
    "nodes_per_world": 100,
    "exploration_weight": 1.41,
    "temperature": 0.1,
    "blunder_chance": 0.0,
    "certainty_exponent": 1.0, # This was in your options but not used.
    "variance_weight": 0.0,     # This was in your options but not used.
}

def deep_merge(base_dict, update_dict):
    """
    Recursively merges two dictionaries, modifying the base_dict in-place.
    """
    for key, value in update_dict.items():
        if isinstance(base_dict.get(key), dict) and isinstance(value, dict):
            deep_merge(base_dict[key], value)
        else:
            base_dict[key] = value
    return base_dict

class Node:
    """A node in the MCTS tree."""
    def __init__(self, state: 'GameState', parent: 'Node' = None, move=None):
        self.state = state
        self.parent = parent
        self.move = move
        self.children = []
        self.untried_moves = state.get_legal_moves()
        # Optimization: shuffle once, then pop for O(1) move selection.
        random.shuffle(self.untried_moves) 
        self.visits = 0
        self.total_reward = 0.0
        # self.total_squared_reward = 0.0 # Not used unless you implement UCB-Tuned

    def is_fully_expanded(self) -> bool:
        return len(self.untried_moves) == 0

    def is_terminal(self) -> bool:
        # A node is terminal if its state represents the end of the game.
        return self.state.is_terminal()

    def add_child(self, move, child_state: 'GameState') -> 'Node':
        child = Node(state=child_state, parent=self, move=move)
        self.children.append(child)
        return child

class CCG_AI:
    """
    A Monte Carlo-based AI for a Collectible Card Game (CCG).
    This AI uses a hybrid MCTS approach that performs UCB searches
    within multiple "determinized" worlds to handle hidden information.
    """

    def __init__(self, options: dict = None):
        """Initializes the MCTS AI with a given configuration."""
        self.options = copy.deepcopy(DEFAULT_OPTIONS)
        if options:
            self.set_options(options)

    def set_options(self, options: dict):
        """Updates the AI's configuration from a dictionary of options."""
        if not isinstance(options, dict):
            raise TypeError("options must be a dictionary.")
        deep_merge(self.options, options)

    def find_best_move(self, initial_state: 'GameState') -> tuple:
        """
        Finds the best move using Information Set MCTS.
        It runs many small, independent MCTS searches, each on a different determinized world.
        """
        # --- 1. SETUP ---
        time_limit = self.options["time_limit_ms"] / 1000.0 if self.options["time_limit_ms"] != float("inf") else float("inf")
        evaluation_limit = self.options["evaluation_limit"]
        nodes_per_world = self.options["nodes_per_world"]

        legal_moves = initial_state.get_legal_moves()
        if not legal_moves: return None, 0
        if len(legal_moves) == 1: return legal_moves[0], 1

        # --- 2. MASTER STATISTICS (Aggregates results from all worlds) ---
        master_move_stats = {move: {"visits": 0, "total_reward": 0.0} for move in legal_moves}
        
        start_time = time.time()
        total_evaluation_count = 0
        
        # --- 3. OUTER LOOP (Worlds Loop) ---
        while True:
            # Check termination conditions for the entire process
            if (time.time() - start_time) >= time_limit: break
            if total_evaluation_count >= evaluation_limit: break

            # a. Create a new world and a new tree
            world_state = initial_state.determinize(initial_state.current_player_index)
            root_node = Node(state=world_state)
            
            # b. MIDDLE LOOP (MCTS search within this single world)
            for _ in range(nodes_per_world):
                if total_evaluation_count >= evaluation_limit: break

                # The four steps of a single MCTS iteration
                leaf_node = self._select(root_node)
                if not leaf_node.is_terminal():
                    leaf_node = self._expand(leaf_node)
                
                reward = self._simulate(leaf_node.state, initial_state.current_player_index)
                self._backpropagate(leaf_node, reward)
                
                total_evaluation_count += 1
            
            # c. Aggregate results from this world's tree into the master stats
            for child in root_node.children:
                if child.move in master_move_stats:
                    master_move_stats[child.move]["visits"] += child.visits
                    master_move_stats[child.move]["total_reward"] += child.total_reward

        # --- 4. FINAL DECISION ---
        if total_evaluation_count == 0:
            return random.choice(legal_moves), 0
        
        best_move = self._choose_best_move(master_move_stats, legal_moves)

        if random.random() < self.options["blunder_chance"]:
            return random.choice(legal_moves), total_evaluation_count
            
        return best_move, total_evaluation_count

    def _ucb_score(self, node: 'Node') -> float:
        """Calculates the UCB1 score for a given node."""
        if node.visits == 0:
            return float('inf')
        
        # Average reward for the node
        exploitation_score = node.total_reward / node.visits
        
        # Exploration term
        exploration_constant_C = self.options["exploration_weight"]
        exploration_score = exploration_constant_C * math.sqrt(
            math.log(node.parent.visits) / node.visits
        )
        
        return exploitation_score + exploration_score

    def _select(self, node: 'Node') -> 'Node':
        """
        Phase 1: Selection.
        Traverse the tree from the root, selecting the best child at each step
        until a leaf node (not fully expanded or terminal) is reached.
        """
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node # Reached a node that can be expanded
            # If fully expanded, move to the best child
            node = max(node.children, key=self._ucb_score)
        return node # Reached a terminal node

    def _expand(self, node: 'Node') -> 'Node':
        """
        Phase 2: Expansion.
        If the selected node is not fully expanded, add a new child node for an
        unexplored move.
        """
        # Pop an untried move (shuffled list makes this random and efficient)
        move = node.untried_moves.pop()
        child_state = node.state.process_action(move)
        return node.add_child(move, child_state)

    def _simulate(self, state: 'GameState', perspective_player_idx: int) -> float:
        """
        Phase 3: Simulation (or in this case, Heuristic Evaluation).
        From the newly expanded node's state, estimate the outcome of the game.
        Here, we use the score difference as a direct heuristic.
        """
        my_score = state.players[perspective_player_idx].score
        opp_score = state.players[1 - perspective_player_idx].score
        
        # Normalize score difference to a [-1, 1] reward
        max_swing = self.options["max_score_swing"]
        score_diff = my_score - opp_score
        clamped_diff = max(-max_swing, min(max_swing, score_diff))
        return clamped_diff / max_swing

    def _backpropagate(self, node: 'Node', reward: float):
        """
        Phase 4: Backpropagation.
        Update the visit counts and total rewards for all nodes from the
        leaf node back up to the root.
        """
        while node is not None:
            node.visits += 1
            # The reward is from the perspective of the player who made the move *leading* to this state.
            # MCTS standardly flips the reward at each level, but since we evaluate from a fixed
            # perspective, we don't need to flip.
            node.total_reward += reward
            node = node.parent

    def _choose_best_move(self, stats: dict, legal_moves: list):
        """Chooses the final move based on aggregated stats and temperature."""
        if not stats:
            return random.choice(legal_moves)
            
        temperature = self.options["temperature"]

        if temperature < 0.01:
            # Greedy: choose the move with the highest average reward.
            # Handle moves that were never visited by assigning a very low score.
            best_avg_reward = -float('inf')
            best_move = None
            for move, data in stats.items():
                if data["visits"] > 0:
                    avg_reward = data["total_reward"] / data["visits"]
                    if avg_reward > best_avg_reward:
                        best_avg_reward = avg_reward
                        best_move = move
            return best_move if best_move is not None else random.choice(legal_moves)
        else:
            # Probabilistic: choose based on visit counts raised to a power.
            moves = list(stats.keys())
            visits = [stats[m]["visits"] for m in moves]
            
            if not any(visits): # If no moves were visited at all
                return random.choice(legal_moves)

            # Apply temperature
            exponent = 1.0 / temperature
            weights = [v ** exponent for v in visits]
            
            # Use random.choices (plural) as it's the modern, weighted choice function
            return random.choices(moves, weights=weights, k=1)[0]
