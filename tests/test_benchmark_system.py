import unittest
import tempfile
import shutil
from pathlib import Path
import numpy as np

from systems.benchmarking.benchmark_system import BenchmarkSystem, BenchmarkScenario, BenchmarkResult
from systems.benchmarking.benchmark_scenarios import BenchmarkScenarioLibrary
from systems.benchmarking.benchmark_runner import BenchmarkRunner
from systems.agents.mlp_agent import MLPAgent
from systems.agents.perceptron_agent import PerceptronAgent

class MockAgent:
    """Simple mock agent for testing benchmarks."""
    def __init__(self, agent_id="mock-agent"):
        self.id = agent_id
        
    def get_action(self, state):
        return np.random.randint(0, 5)  # Return a random action


class TestBenchmarkSystem(unittest.TestCase):
    """Test the benchmark system functionality."""
    
    def setUp(self):
        # Create a temporary directory for test results
        self.temp_dir = tempfile.mkdtemp()
        self.benchmark_system = BenchmarkSystem(self.temp_dir)
        
        # Create a test scenario
        self.test_scenario = BenchmarkScenario(
            id="test-scenario",
            name="Test Scenario",
            description="A test scenario",
            difficulty="easy",
            duration=10,
            environment_params={"map_size": 100},
            enemy_params={"count": 2},
            resource_params={"energy_count": 5},
            objective="survival",
            success_threshold=5
        )
        
        # Add the scenario to the system
        self.benchmark_system.add_scenario(self.test_scenario)
        
        # Create a test agent
        self.test_agent = MockAgent()
    
    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_scenario_creation(self):
        """Test creating and retrieving a scenario."""
        scenario = self.benchmark_system.get_scenario("test-scenario")
        self.assertIsNotNone(scenario)
        self.assertEqual(scenario.id, "test-scenario")
        self.assertEqual(scenario.name, "Test Scenario")
    
    def test_start_benchmark(self):
        """Test starting a benchmark."""
        started = self.benchmark_system.start_benchmark(self.test_agent, "test-scenario")
        self.assertTrue(started)
        self.assertIn(self.test_agent.id, self.benchmark_system.active_benchmarks)
    
    def test_record_metrics(self):
        """Test recording benchmark metrics."""
        # Start a benchmark
        self.benchmark_system.start_benchmark(self.test_agent, "test-scenario")
        
        # Record some metrics
        self.benchmark_system.record_decision_time(self.test_agent.id, 0.1)
        self.benchmark_system.record_kill(self.test_agent.id)
        self.benchmark_system.record_shot(self.test_agent.id, True)
        self.benchmark_system.record_resource_collected(self.test_agent.id, "energy", 10.0)
        self.benchmark_system.update_score(self.test_agent.id, 5.0)
        
        # Finish the benchmark
        self.benchmark_system._finish_benchmark(self.test_agent.id)
        
        # Check the results
        results = self.benchmark_system.get_results()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].agent_id, self.test_agent.id)
        self.assertEqual(results[0].scenario_id, "test-scenario")
        self.assertEqual(results[0].kills, 1)
    
    def test_generate_report(self):
        """Test generating a benchmark report."""
        # Start and finish a benchmark
        self.benchmark_system.start_benchmark(self.test_agent, "test-scenario")
        self.benchmark_system._finish_benchmark(self.test_agent.id)
        
        # Generate a report
        report = self.benchmark_system.generate_report()
        
        # Check the report
        self.assertIsNotNone(report)
        self.assertIn("Agent Benchmark Report", report)
        self.assertIn("Test Scenario", report)


class TestBenchmarkScenarioLibrary(unittest.TestCase):
    """Test the benchmark scenario library functionality."""
    
    def setUp(self):
        self.scenario_library = BenchmarkScenarioLibrary()
    
    def test_default_scenarios(self):
        """Test that the library has default scenarios."""
        scenarios = self.scenario_library.get_all_scenarios()
        self.assertGreater(len(scenarios), 0)
    
    def test_get_scenario_by_id(self):
        """Test getting a scenario by ID."""
        # Get a combat scenario
        scenario = self.scenario_library.get_scenario("combat_novice")
        self.assertIsNotNone(scenario)
        self.assertEqual(scenario.id, "combat_novice")
        self.assertEqual(scenario.objective, "combat")
    
    def test_get_scenarios_by_tags(self):
        """Test getting scenarios by tags."""
        # Get scenarios with the "combat" tag
        scenarios = self.scenario_library.get_scenarios_by_tags(["combat"])
        self.assertGreater(len(scenarios), 0)
        for scenario in scenarios:
            self.assertIn("combat", scenario.tags)
    
    def test_get_scenarios_by_difficulty(self):
        """Test getting scenarios by difficulty."""
        # Get easy scenarios
        scenarios = self.scenario_library.get_scenarios_by_difficulty("easy")
        self.assertGreater(len(scenarios), 0)
        for scenario in scenarios:
            self.assertEqual(scenario.difficulty, "easy")
    
    def test_create_scenario_progression(self):
        """Test creating a scenario progression."""
        # Create a progression for a specific agent type
        progression = self.scenario_library.create_scenario_progression("MLPAgent1", "combat")
        self.assertGreater(len(progression), 0)


class TestBenchmarkRunner(unittest.TestCase):
    """Test the benchmark runner functionality."""
    
    def setUp(self):
        # Create a temporary directory for test results
        self.temp_dir = tempfile.mkdtemp()
        self.runner = BenchmarkRunner(self.temp_dir)
        
        # Create test agents
        self.test_agent1 = MLPAgent(name="test-mlp")
        self.test_agent1.initialize(20, 5)  # Initialize with state size 20 and 5 actions
        
        self.test_agent2 = PerceptronAgent(name="test-perceptron")
        self.test_agent2.initialize(20, 5)
    
    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_run_single_benchmark(self):
        """Test running a single benchmark."""
        # Run a benchmark on the combat_novice scenario
        result = self.runner.run_single_benchmark(self.test_agent1, "combat_novice")
        
        # Check the result
        self.assertTrue(result["success"])
        self.assertEqual(result["agent_id"], self.test_agent1.id)
        self.assertEqual(result["scenario_id"], "combat_novice")
    
    def test_run_agent_comparison(self):
        """Test running an agent comparison."""
        # Run a comparison on the survival_basic scenario
        comparison = self.runner.run_agent_comparison(
            [self.test_agent1, self.test_agent2], "survival_basic")
        
        # Check the comparison
        self.assertEqual(comparison["scenario_id"], "survival_basic")
        self.assertEqual(len(comparison["agents"]), 2)
        self.assertGreater(len(comparison["rankings"]), 0)


if __name__ == "__main__":
    unittest.main() 