import pygame
import numpy as np
from typing import Dict, List, Any

class TrainingEnvironment:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.scenarios = {
            'combat': self._create_combat_scenario,
            'survival': self._create_survival_scenario,
            'team': self._create_team_scenario,
            'resource': self._create_resource_scenario
        }
        self.current_scenario = None
        self.training_metrics = {}
        
    def _create_combat_scenario(self) -> Dict[str, Any]:
        """Create a focused combat training scenario"""
        return {
            'enemies': 5,
            'enemy_types': ['standard', 'fast'],
            'powerups': ['damage'],
            'duration': 600,
            'success_criteria': {
                'kills': 3,
                'survival_time': 500
            }
        }
        
    def _create_survival_scenario(self) -> Dict[str, Any]:
        """Create a survival-focused scenario"""
        return {
            'enemies': 8,
            'enemy_types': ['tank', 'sniper'],
            'powerups': ['shield', 'health'],
            'duration': 900,
            'success_criteria': {
                'survival_time': 800,
                'health_remaining': 50
            }
        }
    
    def select_scenario(self, scenario_type: str):
        if scenario_type in self.scenarios:
            self.current_scenario = self.scenarios[scenario_type]()
    
    def evaluate_performance(self, agent_stats: Dict) -> float:
        """Evaluate agent performance against scenario criteria"""
        if not self.current_scenario:
            return 0.0
            
        score = 0.0
        criteria = self.current_scenario['success_criteria']
        
        for metric, target in criteria.items():
            if metric in agent_stats:
                score += min(1.0, agent_stats[metric] / target)
                
        return score / len(criteria)
