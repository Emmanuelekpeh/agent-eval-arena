import numpy as np
from collections import deque

class ExperienceMemory:
    def __init__(self, capacity=10000):
        self.capacity = capacity
        self.memories = deque(maxlen=capacity)
        self.priorities = deque(maxlen=capacity)
        self.pattern_memory = {}
        
    def add_experience(self, state, action, reward, next_state, done):
        self.memories.append((state, action, reward, next_state, done))
        # Calculate priority based on reward magnitude and novelty
        priority = abs(reward) + self.calculate_novelty(state)
        self.priorities.append(priority)
        
    def calculate_novelty(self, state):
        # Measure how different this state is from recent ones
        if len(self.memories) < 2:
            return 1.0
        recent_states = [m[0] for m in list(self.memories)[-10:]]
        avg_diff = np.mean([np.sum(np.abs(state - old_state)) 
                           for old_state in recent_states])
        return min(1.0, avg_diff)

class TeamLearning:
    def __init__(self):
        self.team_strategies = {}
        self.strategy_scores = {}
        self.learning_rate = 0.01
        
    def update_team_strategy(self, team_id, states, actions, reward):
        if team_id not in self.team_strategies:
            self.team_strategies[team_id] = []
        
        # Store successful team plays
        if reward > 0:
            self.team_strategies[team_id].append({
                'states': states,
                'actions': actions,
                'score': reward
            })
