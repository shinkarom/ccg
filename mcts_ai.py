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

        # --- Standard MCTS stats for THIS node ---
        self.wins = 0.0
        self.visits = 0

        # --- RAVE stats for this node's CHILDREN, stored on the PARENT ---
        # This matches your design. The parent node holds the RAVE stats for the
        # moves leading to its children.
        self.rave_wins = {}   # Key: action, Value: wins
        self.rave_visits = {} # Key: action, Value: visits

        # --- Self-Contained Expansion Logic ---
        # The node determines its own untried actions from its own state.
        self.untried_actions = self.game_state.get_legal_moves()
        random.shuffle(self.untried_actions) # Shuffle to avoid deterministic bias

    def is_terminal(self):
        return self.game_state.is_terminal()

    def is_fully_expanded(self) -> bool:
        """A node is fully expanded if there are no more untried actions."""
        # This is now self-contained and much more robust.
        return len(self.untried_actions) == 0

    def expand(self) -> 'MCTSNode':
        """
        Expands the tree by creating one new child node.
        This function assumes the node is NOT fully expanded.
        """
        action = self.untried_actions.pop()
        next_state = self.game_state.process_action(action)
        child_node = MCTSNode(next_state, parent=self, action=action)
        self.children.append(child_node)
        return child_node

    def best_child(self, exploration_weight=1.41):
        """Selects the best child using the UCB1 formula, modified for RAVE."""
        # This function is already well-implemented and compatible with this design.
        best_score = -1
        best_children = []
        for child in self.children:
            if child.visits == 0:
                # Unvisited children have infinite score and should be picked.
                # Returning one immediately is a common and effective shortcut.
                return child

            # RAVE score is fetched from the PARENT's (self) dictionaries
            rave_score = self.rave_wins.get(child.action, 0) / self.rave_visits.get(child.action, 1)

            # MCTS score is from the child's own stats
            mcts_score = child.wins / child.visits
            
            # Beta interpolates between RAVE and MCTS
            beta = math.sqrt(RAVE_EQUIVALENCE / (3 * self.visits + RAVE_EQUIVALENCE))
            
            combined_score = (1 - beta) * mcts_score + beta * rave_score
            
            # Standard UCT exploration term
            explore_score = exploration_weight * math.sqrt(math.log(self.visits) / child.visits)
            
            final_score = combined_score + explore_score
            
            if final_score > best_score:
                best_score = final_score
                best_children = [child]
            elif final_score == best_score:
                best_children.append(child)
        return random.choice(best_children)

class MCTS_AI:
    def __init__(self, time_limit_ms=1000):
        self.time_limit = time_limit_ms / 1000.0

    # In MCTS_AI class

    def find_best_move(self, initial_state: 'GameState') -> tuple:
        """
        Finds the best move using MCTS with Determination and RAVE.
        
        This version correctly tracks and returns the TOTAL number of simulations (playouts)
        run across all determinizations.
        """
        real_legal_moves = initial_state.get_legal_moves()
        if not real_legal_moves:
            return None, 0
        if len(real_legal_moves) == 1:
            return real_legal_moves[0], 1

        master_move_stats = {move: {"wins": 0.0, "visits": 0} for move in real_legal_moves}
        
        start_time = time.time()
        # This counter will track the total number of simulations (playouts).
        total_playout_count = 0

        # --- DETERMINATION LOOP (Outer Loop) ---
        while time.time() - start_time < self.time_limit:
            
            # 1. DETERMINIZE: Create a single, perfect-information "possible world".
            determinate_state = initial_state.determinize(initial_state.current_player_index)
            
            # 2. SETUP SOLVER: Create a TEMPORARY root for a new MCTS search.
            solver_root = MCTSNode(game_state=determinate_state)
            
            # 3. RUN MCTS SOLVER (Inner Loop)
            for _ in range(SOLVER_ITERATIONS):
                
                # A single playout consists of one full cycle of
                # Select -> Expand -> Simulate -> Backpropagate.
                # We increment our total count here.
                total_playout_count += 1

                # --- Selection & Expansion Phase ---
                node = solver_root
                moves_in_tree = set()
                
                while not node.is_terminal():
                    if not node.is_fully_expanded():
                        node = node.expand()
                        moves_in_tree.add(node.action)
                        break
                    else:
                        node = node.best_child()
                        moves_in_tree.add(node.action)
                
                # --- Simulation Phase ---
                final_sim_state, moves_in_sim = self.simulate(node.game_state)
                
                # --- Backpropagation Phase ---
                self.backpropagate(
                    leaf_node=node,
                    final_sim_state=final_sim_state,
                    search_player_index=initial_state.current_player_index,
                    moves_in_tree=moves_in_tree,
                    moves_in_sim=moves_in_sim
                )
            
            # 4. AGGREGATE RESULTS
            for child in solver_root.children:
                move = child.action
                if move in master_move_stats:
                    master_move_stats[move]["visits"] += child.visits
                    master_move_stats[move]["wins"] += child.wins

        # --- FINAL DECISION ---
        if total_playout_count == 0:
            # If time limit was too short for even one playout.
            return random.choice(real_legal_moves), 0

        # The selection logic remains the same: pick the most visited move.
        best_move = max(master_move_stats, key=lambda m: master_move_stats[m]["visits"])
        print(master_move_stats)
        # Return the chosen move and the TOTAL number of playouts.
        return best_move, total_playout_count

    def simulate(self, state_to_sim_from: GameState) -> (GameState, set):
        """
        Runs a random playout from a given state.
        
        Args:
            state_to_sim_from: The game state of the newly expanded node.
            
        Returns:
            A tuple containing:
            - The terminal or final state of the simulation.
            - A set of all unique actions taken during the simulation.
        """
        sim_state = state_to_sim_from.clone()
        moves_in_sim = set()
        
        # The simulation is limited by a fixed number of turns to prevent infinite loops.
        for _ in range(40): 
            # Check for a winner using the official method.
            if sim_state.get_winner_index() != -1:
                break
            
            # Get all legal moves from the current simulation state.
            legal_moves = sim_state.get_legal_moves()
            if not legal_moves:
                break

            # Choose a random action to simulate.
            action = random.choice(legal_moves)
            moves_in_sim.add(action)

            # Process the action to advance the simulation state.
            sim_state = sim_state.process_action(action)
            
        return sim_state, moves_in_sim

    def backpropagate(self, leaf_node: MCTSNode, final_sim_state: 'GameState', 
                  search_player_index: int, moves_in_tree: set, moves_in_sim: set):
        """
        Updates statistics from the leaf to the root, correctly populating both
        standard MCTS values and the parent-held RAVE statistics.
        """
        winner_idx = final_sim_state.get_winner_index()

        # 1. Determine the reward from the perspective of the *search player*.
        # This keeps the initial perspective consistent throughout the backpropagation.
        reward_for_search_player = 0.0
        if winner_idx == search_player_index:
            reward_for_search_player = 1.0
        elif winner_idx == -2:
            reward_for_search_player = 0.5
        elif winner_idx == -1: # Unfinished game heuristic
            p_search_health = final_sim_state.players[search_player_index].health
            p_other_health = final_sim_state.players[1 - search_player_index].health
            if p_search_health > p_other_health: reward_for_search_player = 1.0
            elif p_search_health < p_other_health: reward_for_search_player = 0.0
            else: reward_for_search_player = 0.5

        # 2. Collect all moves for the RAVE update.
        all_moves_made_in_playout = moves_in_tree.union(moves_in_sim)
        
        # 3. Iterate up the tree from the leaf to the root.
        node = leaf_node
        while node is not None:
            # 4. Determine reward perspective for the current node.
            # The player who acts at a node is the one whose turn it is.
            player_at_node = node.game_state.current_player_index
            
            if player_at_node == search_player_index:
                current_reward = reward_for_search_player
            else:
                # The opponent's reward is the inverse.
                current_reward = 1.0 - reward_for_search_player

            # 5. RAVE Update: The current 'node' is the parent. We update its
            # RAVE dictionaries for any of its children whose moves appeared in the playout.
            for move in all_moves_made_in_playout:
                if move in node.rave_visits: # Check if it's a potential move from this node
                    node.rave_visits[move] += 1
                    node.rave_wins[move] += current_reward

            # 6. Standard MCTS Update: Update the stats for the node that is on the direct path.
            node.visits += 1
            node.wins += current_reward
            
            # 7. Move up to the parent for the next iteration.
            node = node.parent
