import unittest
import numpy as np
import sys
import os
import time
from collections import defaultdict
import random
sys.path.append('..')

from systems.learning.pattern_recognition import ActionPattern
from systems.learning.pattern_recognition_system import PatternRecognitionSystem

class TestPatternRecognition(unittest.TestCase):
    
    def setUp(self):
        self.pattern_system = PatternRecognitionSystem(max_patterns=100)
        
        # Create test data
        self.test_state = np.array([10.0, 20.0, 0.5, 100.0, 80.0, 1.0, 0.0])
        self.test_context = {
            'team_id': 'team_1',
            'in_combat': True,
            'personality_type': 'high_aggressiveness_low_caution',
            'near_enemy': True
        }
        
    def test_action_pattern_creation(self):
        # Create a pattern
        pattern = ActionPattern("test_pattern", sequence_length=3)
        
        # Add state-action pairs
        pattern.add_state_action({'position_x': 10.0, 'health': 100.0}, 1)
        pattern.add_state_action({'position_x': 15.0, 'health': 90.0}, 2)
        pattern.add_state_action({'position_x': 20.0, 'health': 80.0}, 4)
        
        # Test sequence length is maintained
        self.assertEqual(len(pattern.state_action_sequence), 3)
        
        # Test pattern starts with empty outcome history
        self.assertEqual(len(pattern.outcome_history), 0)
        
        # Record outcome
        pattern.record_outcome(True, 10.0, {'in_combat': True})
        
        # Test outcome is recorded
        self.assertEqual(len(pattern.outcome_history), 1)
        self.assertEqual(pattern.success_rate, 1.0)
        self.assertGreater(pattern.confidence, 0.0)
        self.assertEqual(pattern.total_reward, 10.0)
        
    def test_pattern_matching(self):
        # Create pattern
        pattern = ActionPattern("test_pattern", sequence_length=3)
        pattern.add_state_action({'position_x': 10.0, 'health': 100.0}, 1)
        pattern.add_state_action({'position_x': 15.0, 'health': 90.0}, 2)
        pattern.add_state_action({'position_x': 20.0, 'health': 80.0}, 4)
        
        # Create similar sequence
        similar_sequence = [
            ({'position_x': 9.0, 'health': 95.0}, 1),
            ({'position_x': 14.0, 'health': 85.0}, 2),
            ({'position_x': 21.0, 'health': 75.0}, 4)
        ]
        
        # Test matching
        match_score = pattern.matches(similar_sequence)
        self.assertGreater(match_score, 0.8)
        
        # Create different sequence (different actions)
        different_sequence = [
            ({'position_x': 10.0, 'health': 100.0}, 1),
            ({'position_x': 15.0, 'health': 90.0}, 3),  # Different action
            ({'position_x': 20.0, 'health': 80.0}, 4)
        ]
        
        # Test non-matching due to different action
        match_score = pattern.matches(different_sequence)
        self.assertEqual(match_score, 0.0)
        
    def test_pattern_recognition_system(self):
        # Record experiences for agent
        agent_id = "test_agent"
        context = {
            'team_id': 'team_1',
            'in_combat': True
        }
        
        # Repeat pattern creation to increase confidence
        for _ in range(3):
            # Record a sequence of similar actions
            for i in range(5):
                state = np.array([10.0 + i, 20.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
                self.pattern_system.record_experience(agent_id, state, 1, 0.0, context)
                
            # Record a final action with reward
            state = np.array([15.0, 15.0, 0.5, 90.0, 80.0, 1.0, 0.0])
            self.pattern_system.record_experience(agent_id, state, 2, 10.0, context)
        
        # Check that a pattern was created
        self.assertGreater(len(self.pattern_system.patterns), 0)
        
        # Test suggestion
        state = np.array([10.0, 20.0, 0.5, 100.0, 80.0, 1.0, 0.0])
        
        # Record the start of a similar sequence
        self.pattern_system.record_experience(agent_id, state, 1, 0.0, context)
        state = np.array([11.0, 19.0, 0.5, 98.0, 80.0, 1.0, 0.0])
        self.pattern_system.record_experience(agent_id, state, 1, 0.0, context)
        
        # Get suggestion for next action
        state = np.array([12.0, 18.0, 0.5, 96.0, 80.0, 1.0, 0.0])
        suggested_action, confidence = self.pattern_system.suggest_action(agent_id, state, context)
        
        # Verify behavior
        self.assertIsNotNone(suggested_action)
        self.assertGreater(confidence, 0.0)
        
    def test_feature_extraction(self):
        state = np.array([10.0, 20.0, 0.5, 100.0, 80.0, 1.0, 0.0])
        features = self.pattern_system._extract_features(state)
        
        self.assertEqual(features['position_x'], 10.0)
        self.assertEqual(features['position_y'], 20.0)
        self.assertEqual(features['health'], 100.0)
        self.assertEqual(features['energy'], 80.0)
        self.assertEqual(features['nearby_entity'], 1.0)
        
    def test_tag_functionality(self):
        # Create a pattern
        pattern = ActionPattern("test_pattern")
        
        # Add tags
        pattern.add_tag('combat')
        pattern.add_tag('formation')
        
        # Test tags were added
        self.assertIn('combat', pattern.get_tags())
        self.assertIn('formation', pattern.get_tags())
        
        # Test pattern tagging
        context = {
            'in_combat': True,
            'in_formation': True
        }
        
        agent_id = "test_agent"
        state = np.array([10.0, 20.0, 0.5, 100.0, 80.0, 1.0, 0.0])
        
        # Create a sequence that will generate a pattern
        for i in range(3):
            self.pattern_system.record_experience(agent_id, state, 1, 0.0, context)
            
        self.pattern_system.record_experience(agent_id, state, 1, 10.0, context)
        
        # Get the created pattern
        pattern_values = list(self.pattern_system.patterns.values())
        self.assertGreater(len(pattern_values), 0)
        test_pattern = pattern_values[0]
        
        # Check that tags were applied
        self.assertIn('combat', test_pattern.get_tags())
        self.assertIn('formation', test_pattern.get_tags())
        
    def test_pattern_sharing(self):
        # Create patterns for source agent
        source_agent = "source_agent"
        target_agent = "target_agent"
        
        context = {
            'team_id': 'team_1',
            'in_combat': True
        }
        
        # Record successful patterns for source agent
        for i in range(3):
            state = np.array([10.0 + i, 20.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
            self.pattern_system.record_experience(source_agent, state, 1, 0.0, context)
            
        self.pattern_system.record_experience(source_agent, state, 2, 10.0, context)
        
        # Record another pattern with different tag
        combat_context = context.copy()
        combat_context['in_combat'] = True
        
        for i in range(3):
            state = np.array([30.0 + i, 40.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
            self.pattern_system.record_experience(source_agent, state, 4, 0.0, combat_context)
            
        self.pattern_system.record_experience(source_agent, state, 0, 15.0, combat_context)
        
        # Share patterns
        shared_count = self.pattern_system.share_patterns(source_agent, target_agent)
        
        # Check that patterns were shared
        self.assertGreater(shared_count, 0)
        
        # Check target agent can use shared patterns
        target_patterns = [p for p_id, p in self.pattern_system.patterns.items() 
                         if p_id.startswith(f"pattern_{target_agent}")]
        
        self.assertGreater(len(target_patterns), 0)
        
        # Check shared tag was added
        self.assertIn('shared', target_patterns[0].get_tags())
        
    def test_personality_integration(self):
        agent_id = "personality_agent"
        
        # Create personality traits
        personality_traits = {
            'aggressiveness': 0.8,
            'caution': 0.2,
            'curiosity': 0.6
        }
        
        # Integrate with system
        self.pattern_system.integrate_with_personality(agent_id, personality_traits)
        
        # Check agent context was updated
        self.assertIn(agent_id, self.pattern_system.agent_contexts)
        self.assertEqual(
            self.pattern_system.agent_contexts[agent_id]['personality_aggressiveness'], 
            0.8
        )
        
        # Check personality type was set
        self.assertIn('personality_type', self.pattern_system.agent_contexts[agent_id])
        self.assertEqual(
            self.pattern_system.agent_contexts[agent_id]['personality_type'],
            'high_aggressiveness_low_caution'
        )
        
    def test_serialization(self):
        # Create some patterns
        agent_id = "test_agent"
        context = {'team_id': 'team_1', 'in_combat': True}
        
        for i in range(3):
            state = np.array([10.0 + i, 20.0 - i, 0.5, 100.0 - 2*i, 80.0, 1.0, 0.0])
            self.pattern_system.record_experience(agent_id, state, 1, 0.0, context)
            
        self.pattern_system.record_experience(agent_id, state, 2, 10.0, context)
        
        # Serialize to dict
        data = self.pattern_system.save_to_dict()
        
        # Create new system
        new_system = PatternRecognitionSystem()
        new_system.load_from_dict(data)
        
        # Check patterns were loaded
        self.assertEqual(len(new_system.patterns), len(self.pattern_system.patterns))
        
        # Check functionality is preserved
        pattern_id = list(self.pattern_system.patterns.keys())[0]
        orig_pattern = self.pattern_system.patterns[pattern_id]
        loaded_pattern = new_system.patterns[pattern_id]
        
        self.assertEqual(orig_pattern.success_rate, loaded_pattern.success_rate)
        self.assertEqual(orig_pattern.confidence, loaded_pattern.confidence)
        
class TestPatternRecognitionSystem(unittest.TestCase):
    def setUp(self):
        """Set up the pattern recognition system and basic test data"""
        self.pattern_system = PatternRecognitionSystem(
            max_patterns=100,
            min_confidence_threshold=0.5,
            learning_rate=0.1,
            state_similarity_threshold=0.8
        )

        # Define Action Mapping
        self.ACTION_MAP = {"attack": 0, "defend": 1, "retreat": 2, "heal": 3, "scout": 4}
        
        # Set up an agent with personality traits
        self.agent_id = "test_agent"
        self.pattern_system.integrate_with_personality(
            agent_id=self.agent_id,
            traits={
                "openness": 0.7,
                "conscientiousness": 0.6,
                "extraversion": 0.5,
                "agreeableness": 0.6,
                "neuroticism": 0.3,
                "risk_taking": 0.4
            }
        )
        
        # Create some sample states, actions, and rewards
        self.sample_states = [
            np.array([10.0, 20.0, 30.0]),
            np.array([15.0, 25.0, 35.0]),
            np.array([5.0, 15.0, 25.0]),
            np.array([12.0, 22.0, 32.0]),
            np.array([8.0, 18.0, 28.0])
        ]
        
        # Use integer actions based on the map
        self.sample_actions = [self.ACTION_MAP["attack"], self.ACTION_MAP["defend"], self.ACTION_MAP["retreat"], self.ACTION_MAP["heal"], self.ACTION_MAP["scout"]]
        
        self.sample_rewards = [1.0, 0.5, -0.5, 0.8, 0.2]
        
        self.sample_contexts = [
            {"health": 0.8, "enemies_nearby": 2, "cover_available": True},
            {"health": 0.5, "enemies_nearby": 3, "cover_available": False},
            {"health": 0.2, "enemies_nearby": 5, "cover_available": False},
            {"health": 0.6, "enemies_nearby": 1, "cover_available": True},
            {"health": 0.9, "enemies_nearby": 0, "cover_available": True}
        ]
        
        # Record some sample experiences
        for i in range(5):
            self.pattern_system.record_experience(
                agent_id=self.agent_id,
                state=self.sample_states[i],
                action=self.sample_actions[i],
                reward=self.sample_rewards[i],
                context=self.sample_contexts[i]
            )
            
        # Add more samples of similar states with varying outcomes
        # to create success/failure patterns
        
        # Success cases for "attack" action
        for i in range(5):
            similar_state = self.sample_states[0] + np.random.normal(0, 2, 3)
            self.pattern_system.record_experience(
                agent_id=self.agent_id,
                state=similar_state,
                action=self.ACTION_MAP["attack"],
                reward=0.8 + np.random.normal(0, 0.2),
                context={"health": 0.7 + np.random.normal(0, 0.1), 
                         "enemies_nearby": 2, 
                         "cover_available": True}
            )
            
        # Failure cases for "attack" action
        for i in range(5):
            similar_state = self.sample_states[0] + np.random.normal(0, 2, 3)
            self.pattern_system.record_experience(
                agent_id=self.agent_id,
                state=similar_state,
                action=self.ACTION_MAP["attack"],
                reward=-0.5 + np.random.normal(0, 0.2),
                context={"health": 0.3 + np.random.normal(0, 0.1), 
                         "enemies_nearby": 5, 
                         "cover_available": False}
            )
    
    def test_record_and_suggest_action(self):
        """Test that actions can be recorded and then suggested"""
        # Try suggesting an action with a state similar to one we've seen
        similar_to_first = self.sample_states[0] + np.random.normal(0, 1, 3)
        action, confidence = self.pattern_system.suggest_action(
            agent_id=self.agent_id,
            state=similar_to_first,
            context=self.sample_contexts[0]
        )
        
        # The suggested action should be "attack" (integer 0) with some confidence
        self.assertIsNotNone(action)
        self.assertTrue(confidence > 0)
    
    def test_suggest_action_with_risk_assessment(self):
        """Test that action suggestions include risk assessment"""
        similar_to_first = self.sample_states[0] + np.random.normal(0, 1, 3)
        
        # Get action with risk assessment
        action, assessment = self.pattern_system.suggest_action_with_risk_assessment(
            agent_id=self.agent_id,
            state=similar_to_first,
            context=self.sample_contexts[0]
        )
        
        # Check the assessment contains all expected fields
        self.assertIsNotNone(action)
        self.assertIn("confidence", assessment)
        self.assertIn("risk_level", assessment)
        self.assertIn("outcome_prediction", assessment)
        self.assertIn("pattern_ids", assessment)
        
        # Check risk level is a float between 0 and 1
        self.assertTrue(0 <= assessment["risk_level"] <= 1)
        
        # Check that outcome prediction exists
        self.assertTrue("expected_reward" in assessment["outcome_prediction"])
    
    def test_analyze_success_failure_patterns(self):
        """Test the analysis of success and failure patterns"""
        analysis = self.pattern_system.analyze_success_failure_patterns(self.agent_id)
        
        # Check that the analysis contains expected fields
        self.assertIn("success_factors", analysis)
        self.assertIn("failure_factors", analysis)
        self.assertIn("high_reward_states", analysis)
        self.assertIn("low_reward_states", analysis)
        
        # Check that we have some success factors from our context
        success_factors = analysis["success_factors"]
        self.assertTrue(len(success_factors) > 0)
        
        # There should be some health-related success factor
        health_related = False
        for factor, values in success_factors.items():
            if "health" in factor:
                health_related = True
                break
        self.assertTrue(health_related, "Expected health-related success factor")
        
        # Check that high reward states has some entries
        self.assertTrue(len(analysis["high_reward_states"]) > 0)
    
    def test_find_similar_patterns(self):
        """Test finding similar patterns"""
        # Create a new state to find patterns for
        test_state = np.array([11.0, 21.0, 31.0])
        test_action = self.ACTION_MAP["attack"]
        test_context = {"health": 0.75, "enemies_nearby": 2, "cover_available": True}
        
        # Directly test the internal method
        patterns = self.pattern_system._find_similar_patterns(
            agent_id=self.agent_id,
            state=test_state,
            action=test_action,
            context=test_context
        )
        
        # There should be at least one similar pattern
        self.assertTrue(len(patterns) > 0)
        
        # The similar patterns should include our action
        actions_in_patterns = [p["action"] for p in patterns]
        self.assertIn(test_action, actions_in_patterns)
    
    def test_calculate_state_similarity(self):
        """Test state similarity calculation"""
        state1 = np.array([10.0, 20.0, 30.0])
        state2 = np.array([11.0, 21.0, 31.0])
        
        similarity = self.pattern_system._calculate_state_similarity(state1, state2)
        
        # These states are very similar, so similarity should be high
        self.assertTrue(similarity > 0.9)
        
        # Test with very different states
        state3 = np.array([50.0, 60.0, 70.0])
        similarity = self.pattern_system._calculate_state_similarity(state1, state3)
        
        # These states are different, so similarity should be low
        self.assertTrue(similarity < 0.5)
    
    def test_calculate_context_similarity(self):
        """Test context similarity calculation"""
        context1 = {"health": 0.8, "enemies_nearby": 2, "cover_available": True}
        context2 = {"health": 0.75, "enemies_nearby": 2, "cover_available": True}
        
        similarity = self.pattern_system._calculate_context_similarity(context1, context2)
        
        # These contexts are very similar
        self.assertTrue(similarity > 0.9)
        
        # Test with different contexts
        context3 = {"health": 0.3, "enemies_nearby": 5, "cover_available": False}
        similarity = self.pattern_system._calculate_context_similarity(context1, context3)
        
        # These contexts are different
        self.assertTrue(similarity < 0.7)
    
    def test_save_and_load(self):
        """Test saving and loading the pattern recognition system"""
        # Save the system to a temporary file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        try:
            temp_file.close()
            
            # Save the system
            self.pattern_system.save_to_file(temp_file.name)
            
            # Create a new system and load from file
            new_system = PatternRecognitionSystem()
            new_system.load_from_file(temp_file.name)
            
            # Check that patterns were loaded by suggesting an action
            similar_to_first = self.sample_states[0] + np.random.normal(0, 1, 3)
            action, confidence = new_system.suggest_action(
                agent_id=self.agent_id,
                state=similar_to_first,
                context=self.sample_contexts[0]
            )
            
            # There should be a suggestion with confidence
            self.assertIsNotNone(action)
            self.assertTrue(confidence > 0)
            
        finally:
            # Clean up
            import os
            os.unlink(temp_file.name)
    
    def test_get_pattern_statistics(self):
        """Test getting pattern statistics"""
        stats = self.pattern_system.get_pattern_statistics(self.agent_id)
        
        # Check that stats contains expected fields
        self.assertIn("total_patterns", stats)
        self.assertIn("average_reward", stats)
        self.assertIn("most_common_actions", stats)
        self.assertIn("highest_reward_actions", stats)
        
        # There should be some patterns
        self.assertTrue(stats["total_patterns"] > 0)
        
        # Most common actions should include "attack" (integer 0)
        self.assertIn(self.ACTION_MAP["attack"], [action for action, count in stats["most_common_actions"]])


if __name__ == "__main__":
    unittest.main() 