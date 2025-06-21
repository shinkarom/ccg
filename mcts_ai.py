# mcts_ai.py

import random
import math
import time
from game_state import GameState
import game_logic

RAVE_EQUIVALENCE = 350

class MCTSNode:
    def __init__(self, game_state: GameState, parent=None, action=None):
        self.game_state = game_state # This is just a representative state
        self.parent = parent
        self.action = action
        self.children = []
        self.wins = 0
        self.visits = 0
        self.rave_wins = {} # RAVE setup still needs the full move list
        self.rave_visits = {}

    def is_fully_expanded(self, legal_moves_in_current_sim: list) -> bool:
        """A node is fully expanded if it has a child for every currently legal move."""
        return len(legal_moves_in_current_sim) == len(self.children)

    def best_child(self, exploration_weight=1.41):
        """Selects the best child using the UCB1 formula, modified for RAVE."""
        best_score = -1
        best_children = []
        for child in self.children:
            if child.visits == 0:
                return child

            rave_visits = self.rave_visits.get(child.action, 0)
            if rave_visits == 0:
                rave_score = 0
            else:
                rave_score = self.rave_wins.get(child.action, 0) / rave_visits
            
            mcts_score = child.wins / child.visits
            
            beta = math.sqrt(RAVE_EQUIVALENCE / (3 * self.visits + RAVE_EQUIVALENCE))
            
            combined_score = (1 - beta) * mcts_score + beta * rave_score
            
            explore_score = exploration_weight * math.sqrt(math.log(self.visits) / child.visits)
            
            final_score = combined_score + explore_score
            
            if final_score > best_score:
                best_score = final_score
                best_children = [child]
            elif final_score == best_score:
                best_children.append(child)
        return random.choice(best_children)

    def expand(self):
        action = self.untried_actions.pop()
        next_state = self.game_state.process_action(action)
        child_node = MCTSNode(next_state, parent=self, action=action)
        self.children.append(child_node)
        return child_node

class MCTS_AI:
    def __init__(self, time_limit_ms=1000):
        self.time_limit = time_limit_ms / 1000.0

    # In MCTS_AI class

    def find_best_move(self, initial_state: GameState) -> tuple:
        root = MCTSNode(game_state=initial_state.clone()) # Store a safe clone in the root
        real_legal_moves = initial_state.get_legal_moves()

        # The .get() method handles non-existent keys, so RAVE init is not strictly needed.
        # We can rely on the backpropagation step to populate the dictionaries.

        if len(real_legal_moves) == 1:
            return real_legal_moves[0], 1
        
        rollout_count = 0
        start_time = time.time()

        while time.time() - start_time < self.time_limit:
            rollout_count += 1

            # CRITICAL: Assume .determinize() returns a NEW, DEEP COPY of the state.
            current_sim_state = initial_state.determinize(initial_state.current_player_index)
            
            node = root
            moves_in_tree = set()

            # --- SELECTION & EXPANSION ---
            while True:
                if current_sim_state.is_terminal(): # Use a simple is_terminal() check if possible
                    break
                
                legal_moves_now = current_sim_state.get_legal_moves()
                if not legal_moves_now: # No moves possible, terminal state
                    break

                existing_child_actions = {c.action for c in node.children}
                untried_actions = [m for m in legal_moves_now if m not in existing_child_actions]

                if untried_actions:
                    # --- EXPANSION ---
                    action_to_expand = random.choice(untried_actions)
                    
                    # The state passed to the new node is for REPRESENTATION ONLY.
                    # We use current_sim_state for the actual simulation.
                    # Here we pass a clone so the node has a state, but it won't be used in this run.
                    child_node = MCTSNode(current_sim_state.clone(), parent=node, action=action_to_expand)
                    node.children.append(child_node)
                    
                    node = child_node # Move to the new node
                    moves_in_tree.add(action_to_expand)
                    
                    # Apply action to our simulation state
                    current_sim_state = current_sim_state.process_action(action_to_expand)
                    break # Exit traversal to begin simulation from the new node's state
                else:
                    # --- SELECTION ---
                    if not node.children: # Terminal node in our search tree
                        break
                    node = node.best_child()
                    moves_in_tree.add(node.action)
                    # Apply action to our simulation state
                    current_sim_state = current_sim_state.process_action(node.action)

            # --- SIMULATION & BACKPROPAGATION ---
            # *** KEY CHANGE HERE ***
            # Simulate from the CURRENT simulation state, NOT the state stored in the node.
            final_state, moves_in_sim = self.simulate(current_sim_state)
            self.backpropagate(node, final_state, initial_state.current_player_index, moves_in_tree, moves_in_sim)

        # --- Final decision logic ---
        if not root.children:
            # This can happen if time runs out before a single rollout completes
            return random.choice(real_legal_moves) if real_legal_moves else None, rollout_count

        best_move_node = max(root.children, key=lambda c: c.visits)
        return best_move_node.action, rollout_count
    
    # In your MCTS_AI class
    import pprint # For pretty printing lists/dicts

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
        for _ in range(20): 
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

    def backpropagate(self, leaf_node: 'MCTSNode', final_sim_state: GameState, 
                  search_player_index: int, moves_in_tree: set, moves_in_sim: set):
        """
        Updates the statistics of nodes from the leaf back up to the root.
        """
        
        # --- 1. Determine the simulation result (1 for P0 win, -1 for P1 win, 0 for draw) ---
        winner_idx = final_sim_state.get_winner_index()
        result = 0 
        if winner_idx == 0: 
            result = 1
        elif winner_idx == 1: 
            result = -1
        # Fallback to health heuristic if the game didn't officially end.
        elif winner_idx == -1:
            p0_health = final_sim_state.players[0].health
            p1_health = final_sim_state.players[1].health
            if p0_health > p1_health: 
                result = 1
            elif p1_health > p0_health: 
                result = -1

        # --- 2. Walk up the tree and update stats ---
        all_moves_made_in_playout = moves_in_tree.union(moves_in_sim)
        node_iterator = leaf_node
        
        while node_iterator is not None:
            # Determine the outcome from the perspective of the player at THIS node.
            # This is the key fix.
            player_at_node = node_iterator.game_state.current_player_index
            is_win_for_node_player = (player_at_node == 0 and result == 1) or \
                                     (player_at_node == 1 and result == -1)
            
            # A. Update standard MCTS stats for the node
            node_iterator.visits += 1
            if is_win_for_node_player:
                node_iterator.wins += 1
            # (Alternatively, if you have draws, you could add 0.5 for a draw)
            # elif result == 0:
            #     node_iterator.wins += 0.5

            # B. Update RAVE stats for all moves in the playout
            # The win attribution is based on the perspective of the player at THIS node.
            for move in all_moves_made_in_playout:
                # Use .get() for safety in case a move isn't in the dict yet.
                node_iterator.rave_visits[move] = node_iterator.rave_visits.get(move, 0) + 1
                if is_win_for_node_player:
                    node_iterator.rave_wins[move] = node_iterator.rave_wins.get(move, 0) + 1
            
            # Move up to the parent node
            node_iterator = node_iterator.parent
