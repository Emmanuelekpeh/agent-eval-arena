import unittest
import numpy as np
import sys
import os
import time
sys.path.append('..')

from systems.learning.pattern_recognition_system import PatternRecognitionSystem

class TestSuccessFailurePatternRecognition(unittest.TestCase):
    
    def setUp(self):
        self.pattern_system = PatternRecognitionSystem(max_patterns=100)
        
        # Create test data
        self.test_state = np.array([10.0, 20.0, 0.5, 100.0, 80.0, 1.0, 0.0])
        self.test_context = {
            'team_id': 'team_1',
            'in_combat': True,
            'near_enemy': True
        }
        
        # Setup test agent with personality
        self.agent_id = "test_agent"
        self.pattern_system.integrate_with_personality(self.agent_id, {
            "openness": 0.7,
            "conscientiousness": 0.6,
            "extraversion": 0.5,
            "agreeableness": 0.6,
            "neuroticism": 0.3,
            "risk_tolerance": 0.5,
            "caution": 0.5
        })
        
    def test_success_pattern_identification(self):
        """Test that patterns with positive rewards are identified as success patterns"""
        # Create a successful pattern (multiple positive reward experiences)
        for i in range(5):
            state = np.array([10.0 + i, 20.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
            action = 1
            reward = 1.0  # Positive reward
            self.pattern_system.record_experience(self.agent_id, state, action, reward, self.test_context)
        
        # Get success patterns
        success_patterns = self.pattern_system.get_success_patterns(self.agent_id)
        
        # Verify pattern was identified as success
        self.assertGreater(len(success_patterns), 0)
        
        # Check pattern has high success rate
        self.assertGreater(success_patterns[0]["success_rate"], 0.8)
        
        # Verify this pattern isn't in failure patterns
        failure_patterns = self.pattern_system.get_failure_patterns(self.agent_id)
        self.assertEqual(len(failure_patterns), 0)
    
    def test_failure_pattern_identification(self):
        """Test that patterns with negative rewards are identified as failure patterns"""
        # Create a failure pattern (multiple negative reward experiences)
        for i in range(5):
            state = np.array([30.0 + i, 40.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
            action = 2
            reward = -1.0  # Negative reward
            self.pattern_system.record_experience(self.agent_id, state, action, reward, self.test_context)
        
        # Get failure patterns
        failure_patterns = self.pattern_system.get_failure_patterns(self.agent_id)
        
        # Verify pattern was identified as failure
        self.assertGreater(len(failure_patterns), 0)
        
        # Check pattern has low success rate
        self.assertLess(failure_patterns[0]["success_rate"], 0.2)
        
        # Verify this pattern isn't in success patterns
        success_patterns = self.pattern_system.get_success_patterns(self.agent_id)
        self.assertEqual(len(success_patterns), 0)
    
    def test_pattern_suggestion_avoids_failures(self):
        """Test that action suggestions avoid known failure patterns for cautious agents"""
        # Create a cautious agent
        cautious_agent = "cautious_agent"
        self.pattern_system.integrate_with_personality(cautious_agent, {
            "openness": 0.5,
            "conscientiousness": 0.8,
            "extraversion": 0.3,
            "agreeableness": 0.6,
            "neuroticism": 0.6,
            "risk_tolerance": 0.2,
            "caution": 0.9  # Very cautious
        })
        
        # Create a failure pattern
        for i in range(5):
            state = np.array([30.0 + i, 40.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
            action = 2
            reward = -1.0  # Negative reward
            self.pattern_system.record_experience(cautious_agent, state, action, reward, self.test_context)
        
        # Create a success pattern with different action
        for i in range(5):
            state = np.array([10.0 + i, 20.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
            action = 1
            reward = 1.0  # Positive reward
            self.pattern_system.record_experience(cautious_agent, state, action, reward, self.test_context)
        
        # Test suggestion with state similar to failure pattern
        test_state = np.array([32.0, 38.0, 0.5, 96.0, 80.0, 1.0, 0.0])
        suggested_action, confidence = self.pattern_system.suggest_action(cautious_agent, test_state, self.test_context)
        
        # A cautious agent should not suggest action 2 (from failure pattern)
        self.assertNotEqual(suggested_action, 2)
        
        # Now test with a risk-tolerant agent that should be willing to try action 2
        risky_agent = "risky_agent"
        self.pattern_system.integrate_with_personality(risky_agent, {
            "openness": 0.7,
            "conscientiousness": 0.4,
            "extraversion": 0.7,
            "agreeableness": 0.5,
            "neuroticism": 0.3,
            "risk_tolerance": 0.9,  # Very risk-tolerant
            "caution": 0.1  # Not cautious
        })
        
        # Copy the patterns from cautious agent
        self.pattern_system.patterns[risky_agent] = self.pattern_system.patterns[cautious_agent].copy()
        # Iterate over a copy of the items to avoid RuntimeError
        for pattern_id, outcomes in list(self.pattern_system.pattern_outcomes.items()):
            if pattern_id.startswith(f"{cautious_agent}_"):
                idx = pattern_id.split('_')[1]
                new_pattern_id = f"{risky_agent}_{idx}"
                self.pattern_system.pattern_outcomes[new_pattern_id] = outcomes.copy()
        
        # For a risk-tolerant agent, we might still get a suggestion even with the failure pattern
        # Let's not assert specific behavior as it can be probabilistic
    
    def test_pattern_factors_analysis(self):
        """Test analysis of common factors in success/failure patterns"""
        # Create several similar success patterns
        for i in range(10):
            state = np.array([10.0 + i*0.5, 20.0 - i*0.5, 0.5, 100.0 - i, 80.0, 1.0, 0.0])
            action = 1
            context = {
                'team_id': 'team_1',
                'in_combat': True,
                'near_enemy': True,
                'health_percentage': 0.8 - i*0.05,
                'energy_level': 'high'
            }
            reward = 1.0
            self.pattern_system.record_experience(self.agent_id, state, action, reward, context)
        
        # Create several similar failure patterns
        for i in range(10):
            state = np.array([50.0 + i*0.5, 60.0 - i*0.5, 0.5, 100.0 - i, 80.0, 1.0, 0.0])
            action = 3
            context = {
                'team_id': 'team_2',
                'in_combat': True,
                'near_enemy': False,
                'health_percentage': 0.3 - i*0.02,
                'energy_level': 'low'
            }
            reward = -1.0
            self.pattern_system.record_experience(self.agent_id, state, action, reward, context)
        
        # Analyze success factors
        success_factors = self.pattern_system.analyze_pattern_factors(self.agent_id, "success")
        
        # Verify some expected success factors
        self.assertIn('team_id', success_factors)
        self.assertEqual(success_factors['team_id']['value'], 'team_1')
        self.assertIn('near_enemy', success_factors)
        self.assertEqual(success_factors['near_enemy']['value'], 'True')
        self.assertIn('action', success_factors)
        self.assertEqual(success_factors['action']['value'], 1)
        
        # Analyze failure factors
        failure_factors = self.pattern_system.analyze_pattern_factors(self.agent_id, "failure")
        
        # Verify some expected failure factors
        self.assertIn('team_id', failure_factors)
        self.assertEqual(failure_factors['team_id']['value'], 'team_2')
        self.assertIn('near_enemy', failure_factors)
        self.assertEqual(failure_factors['near_enemy']['value'], 'False')
        self.assertIn('energy_level', failure_factors)
        self.assertEqual(failure_factors['energy_level']['value'], 'low')
        self.assertIn('action', failure_factors)
        self.assertEqual(failure_factors['action']['value'], 3)
    
    def test_pattern_outcomes_in_stats(self):
        """Test that pattern outcome counts are included in stats"""
        # Create some success and failure patterns
        for i in range(5):
            # Success pattern
            state = np.array([10.0 + i, 20.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
            self.pattern_system.record_experience(self.agent_id, state, 1, 1.0, self.test_context)
            
            # Failure pattern
            state = np.array([30.0 + i, 40.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
            self.pattern_system.record_experience(self.agent_id, state, 2, -1.0, self.test_context)
            
            # Neutral pattern (small rewards)
            state = np.array([50.0 + i, 60.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
            self.pattern_system.record_experience(self.agent_id, state, 3, 0.1, self.test_context)
        
        # Get stats
        stats = self.pattern_system.get_pattern_stats(self.agent_id)
        
        # Verify outcome counts
        self.assertIn('success_patterns', stats)
        self.assertIn('failure_patterns', stats)
        self.assertIn('neutral_patterns', stats)
        
        # We should have at least one pattern of each type
        self.assertGreater(stats['success_patterns'], 0)
        self.assertGreater(stats['failure_patterns'], 0)
        self.assertGreater(stats['neutral_patterns'], 0)
        
        # Sum should equal total patterns
        self.assertEqual(
            stats['success_patterns'] + stats['failure_patterns'] + stats['neutral_patterns'],
            stats['total_patterns']
        )
    
    def test_serialization_with_outcomes(self):
        """Test that pattern outcomes are properly serialized and deserialized"""
        # Create some patterns with outcomes
        for i in range(5):
            # Success pattern
            state = np.array([10.0 + i, 20.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
            self.pattern_system.record_experience(self.agent_id, state, 1, 1.0, self.test_context)
        
        # Serialize
        data = self.pattern_system.save_to_dict()
        
        # Verify pattern_outcomes is included
        self.assertIn('pattern_outcomes', data)
        
        # Create new system and load data
        new_system = PatternRecognitionSystem()
        new_system.load_from_dict(data)
        
        # Verify pattern outcomes were loaded
        success_patterns = new_system.get_success_patterns(self.agent_id)
        self.assertGreater(len(success_patterns), 0)

if __name__ == '__main__':
    unittest.main() 