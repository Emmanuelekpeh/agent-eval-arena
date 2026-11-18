import unittest
import numpy as np
import sys
sys.path.append('..')

from systems.agents.mlp_agent import MLPAgent

class TestGradientLearning(unittest.TestCase):
    """Test cases for gradient-based learning in MLPAgent."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.state_size = 20
        self.action_size = 5
        
        # Create agents for testing
        self.standard_agent = MLPAgent(
            input_size=self.state_size,
            output_size=self.action_size,
            hidden_layer_sizes=[32, 16],
            use_adam=False,
            learning_rate=0.01
        )
        
        self.adam_agent = MLPAgent(
            input_size=self.state_size,
            output_size=self.action_size,
            hidden_layer_sizes=[32, 16],
            use_adam=True,
            learning_rate=0.001
        )
        
        # Sample test data
        self.test_state = np.random.rand(self.state_size)
        self.next_state = np.random.rand(self.state_size)
        self.batch_states = np.random.rand(10, self.state_size)
        self.batch_next_states = np.random.rand(10, self.state_size)
    
    def test_agent_initialization(self):
        """Test that agents initialize correctly with gradient-learning parameters."""
        # Standard agent should not use Adam
        self.assertFalse(self.standard_agent.use_adam)
        
        # Adam agent should have initialized Adam parameters
        self.assertTrue(self.adam_agent.use_adam)
        self.assertEqual(len(self.adam_agent.adam_m), len(self.adam_agent.weights))
        self.assertEqual(len(self.adam_agent.adam_v), len(self.adam_agent.weights))
    
    def test_forward_pass(self):
        """Test that forward pass works correctly with both agent types."""
        for agent in [self.standard_agent, self.adam_agent]:
            # Test single state forward pass
            q_values = agent.predict(self.test_state)
            self.assertEqual(q_values.shape[-1], self.action_size)
            
            # Test batch forward pass
            batch_q_values = agent.predict(self.batch_states)
            self.assertEqual(batch_q_values.shape[0], self.batch_states.shape[0])
            self.assertEqual(batch_q_values.shape[1], self.action_size)
            
            # Get an action
            action = agent.act(self.test_state)
            
            # Action should be in range
            self.assertIn(action, range(self.action_size))
    
    def test_learning_step(self):
        """Test that learning updates weights and biases."""
        for agent in [self.standard_agent, self.adam_agent]:
            # Add experiences to memory
            for i in range(agent.batch_size + 10):
                agent.memory.add((
                    np.random.rand(self.state_size),
                    np.random.randint(0, self.action_size),
                    np.random.rand(),
                    np.random.rand(self.state_size),
                    False
                ))
            
            # Save original weights
            original_weights = [w.copy() for w in agent.weights]
            
            # Perform a learning step
            loss = agent.learn_from_batch()
            
            # Check that loss is returned
            self.assertIsNotNone(loss)
            
            # Check that at least some weights have changed
            weights_changed = False
            for i, (old_w, new_w) in enumerate(zip(original_weights, agent.weights)):
                if not np.array_equal(old_w, new_w):
                    weights_changed = True
                    break
                    
            self.assertTrue(weights_changed, f"Weights did not change after learning for {agent.__class__.__name__}")
    
    def test_adam_updates(self):
        """Test that Adam optimizer properly updates moment estimates."""
        agent = self.adam_agent
        
        # Add experiences to memory
        for i in range(agent.batch_size + 10):
            agent.memory.add((
                np.random.rand(self.state_size),
                np.random.randint(0, self.action_size),
                np.random.rand(),
                np.random.rand(self.state_size),
                False
            ))
        
        # Save original Adam parameters
        original_m = [m.copy() for m in agent.adam_m]
        original_v = [v.copy() for v in agent.adam_v]
        original_t = agent.adam_t
        
        # Perform a learning step
        agent.learn_from_batch()
        
        # Check that Adam parameters have been updated
        self.assertGreater(agent.adam_t, original_t)
        
        m_changed = False
        v_changed = False
        
        for i in range(len(original_m)):
            if not np.array_equal(original_m[i], agent.adam_m[i]):
                m_changed = True
            if not np.array_equal(original_v[i], agent.adam_v[i]):
                v_changed = True
                
        self.assertTrue(m_changed, "Adam first moment estimates did not change")
        self.assertTrue(v_changed, "Adam second moment estimates did not change")
    
    def test_serialization(self):
        """Test serialization and deserialization of agents with gradient-based parameters."""
        for agent in [self.standard_agent, self.adam_agent]:
            # Get serializable state
            state = agent.get_state()
            
            # Create a new agent of the same type
            new_agent = agent.__class__(
                input_size=self.state_size,
                output_size=self.action_size,
                hidden_layer_sizes=[32, 16],
                use_adam=agent.use_adam
            )
            
            # Load the state
            new_agent.load_state(state)
            
            # Check that parameters match
            self.assertEqual(agent.use_adam, new_agent.use_adam)
            self.assertEqual(len(agent.weights), len(new_agent.weights))
            
            # Check that weights and biases are copied correctly
            for w1, w2 in zip(agent.weights, new_agent.weights):
                np.testing.assert_array_equal(w1, w2)
            
            for b1, b2 in zip(agent.biases, new_agent.biases):
                np.testing.assert_array_equal(b1, b2)
            
            if agent.use_adam:
                self.assertEqual(agent.adam_t, new_agent.adam_t)
                self.assertEqual(len(agent.adam_m), len(new_agent.adam_m))
    
    def test_learning_convergence(self):
        """Test that agents can learn a simple task."""
        # We'll teach agents to always choose action 0 for a specific state
        target_state = np.random.rand(self.state_size)
        target_action = 0
        
        # Train many times on the same experience
        # We'll repeatedly add the same experience and train
        for i in range(50):
            for agent in [self.standard_agent, self.adam_agent]:
                # Add the target experience to memory (with a positive reward)
                for _ in range(agent.batch_size):
                    agent.memory.add((target_state, target_action, 1.0, target_state, False))
                
                # Learn from this experience
                agent.learn_from_batch()
        
        # Check if agents predict the highest Q-value for the target action
        for agent in [self.standard_agent, self.adam_agent]:
            q_values = agent.predict(target_state)
            best_action = np.argmax(q_values)
            self.assertEqual(best_action, target_action, 
                            f"Agent {agent.__class__.__name__} did not learn the target action")

    def test_train_on_batch(self):
        """Test the internal _train_on_batch method directly."""
        for agent in [self.standard_agent, self.adam_agent]:
            # Create a batch of experiences
            states = np.random.rand(agent.batch_size, self.state_size)
            actions = np.random.randint(0, self.action_size, size=agent.batch_size)
            rewards = np.random.rand(agent.batch_size)
            next_states = np.random.rand(agent.batch_size, self.state_size)
            dones = np.zeros(agent.batch_size)
            
            # Train directly on this batch
            loss = agent._train_on_batch(states, actions, rewards, next_states, dones)
            
            # Check that a loss value is returned
            self.assertIsNotNone(loss)
            self.assertIsInstance(loss, float)

    def test_gradient_backpropagation(self):
        """Test that gradients are properly backpropagated through the network."""
        for agent in [self.standard_agent, self.adam_agent]:
            # Create a simple single-item batch for testing
            states = np.random.rand(1, self.state_size)
            actions = np.array([0])  # Always choose the first action
            rewards = np.array([1.0])  # Positive reward
            next_states = states.copy()  # Same state for simplicity
            dones = np.array([False])
            
            # Get initial Q-values
            initial_q_values, _ = agent._forward(states)
            initial_q_value = initial_q_values[0, actions[0]]
            
            # Perform several training steps
            for _ in range(10):
                agent._train_on_batch(states, actions, rewards, next_states, dones)
            
            # Get updated Q-values
            updated_q_values, _ = agent._forward(states)
            updated_q_value = updated_q_values[0, actions[0]]
            
            # The Q-value for the chosen action should increase towards the reward
            self.assertGreater(updated_q_value, initial_q_value, 
                              f"Q-value did not increase after training for {agent.__class__.__name__}")

if __name__ == '__main__':
    unittest.main() 