import numpy as np
import time
import logging
import json
import os
from typing import Dict, List, Any, Optional, Tuple, Type
from datetime import datetime
from pathlib import Path

from systems.agents.base_agent import BaseAgent
from systems.benchmarking.benchmark_system import BenchmarkSystem, BenchmarkScenario
from systems.benchmarking.benchmark_scenarios import BenchmarkScenarioLibrary

class BenchmarkRunner:
    """
    Runner for executing benchmarks on different agents.
    This class provides methods to run single or batch benchmarks
    and collect performance statistics.
    """
    
    def __init__(self, output_dir: str = "benchmark_results"):
        self.benchmark_system = BenchmarkSystem(output_dir)
        self.scenario_library = BenchmarkScenarioLibrary()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.logger = logging.getLogger(__name__)
        
    def run_single_benchmark(self, agent: BaseAgent, scenario_id: str) -> Dict[str, Any]:
        """
        Run a single benchmark for an agent.
        
        Args:
            agent: The agent to benchmark
            scenario_id: The ID of the scenario to run
            
        Returns:
            A dictionary with the benchmark results
        """
        scenario = self.scenario_library.get_scenario(scenario_id)
        if not scenario:
            self.logger.error(f"Scenario not found: {scenario_id}")
            return {"success": False, "error": "Scenario not found"}
        
        # Add the scenario to the benchmark system
        self.benchmark_system.add_scenario(scenario)
        
        # Start the benchmark
        self.logger.info(f"Starting benchmark: Agent {agent.id} on scenario {scenario_id}")
        start_time = time.time()
        
        if not self.benchmark_system.start_benchmark(agent, scenario_id):
            return {"success": False, "error": "Failed to start benchmark"}
        
        # Run the benchmark
        self._run_benchmark_simulation(agent, scenario)
        
        # Get the results
        results = self.benchmark_system.get_results(
            agent_type=agent.__class__.__name__, 
            scenario_id=scenario_id
        )
        
        if not results:
            return {"success": False, "error": "No results generated"}
        
        # Get the latest result
        result = results[-1]
        
        self.logger.info(f"Benchmark completed in {time.time() - start_time:.2f} seconds")
        
        # Return the results
        return {
            "success": True,
            "agent_id": agent.id,
            "agent_type": agent.__class__.__name__,
            "scenario_id": scenario_id,
            "score": result.score,
            "survival_time": result.survival_time,
            "kills": result.kills,
            "resources_collected": result.resources_collected,
            "accuracy": result.accuracy,
            "metrics": result.metrics,
            "timestamp": result.timestamp
        }
    
    def run_batch_benchmarks(self, agents: List[BaseAgent], 
                           scenario_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run multiple benchmarks for multiple agents.
        
        Args:
            agents: The agents to benchmark
            scenario_ids: The IDs of the scenarios to run
            
        Returns:
            A dictionary mapping agent IDs to lists of benchmark results
        """
        results = {}
        
        for agent in agents:
            agent_results = []
            for scenario_id in scenario_ids:
                result = self.run_single_benchmark(agent, scenario_id)
                agent_results.append(result)
            results[agent.id] = agent_results
        
        return results
    
    def run_agent_comparison(self, agents: List[BaseAgent], 
                          scenario_id: str) -> Dict[str, Any]:
        """
        Run a comparison benchmark for multiple agents on a single scenario.
        
        Args:
            agents: The agents to benchmark
            scenario_id: The ID of the scenario to run
            
        Returns:
            A dictionary with comparison results
        """
        comparison = {
            "scenario_id": scenario_id,
            "agents": [],
            "rankings": []
        }
        
        # Run benchmark for each agent
        for agent in agents:
            result = self.run_single_benchmark(agent, scenario_id)
            if result["success"]:
                comparison["agents"].append({
                    "agent_id": agent.id,
                    "agent_type": agent.__class__.__name__,
                    "score": result["score"],
                    "survival_time": result["survival_time"],
                    "kills": result["kills"],
                    "accuracy": result["accuracy"]
                })
        
        # Rank agents by score
        comparison["rankings"] = sorted(
            comparison["agents"],
            key=lambda a: a["score"],
            reverse=True
        )
        
        # Generate charts
        self._generate_comparison_charts(comparison, scenario_id)
        
        return comparison
    
    def run_agent_progression(self, agent: BaseAgent, focus_area: str = "balanced") -> Dict[str, Any]:
        """
        Run a progression of benchmarks for an agent to measure learning progress.
        
        Args:
            agent: The agent to benchmark
            focus_area: Focus area for the progression
            
        Returns:
            A dictionary with progression results
        """
        # Get progression scenario IDs
        scenario_ids = self.scenario_library.create_scenario_progression(
            agent.__class__.__name__, focus_area)
        
        progression = {
            "agent_id": agent.id,
            "agent_type": agent.__class__.__name__,
            "focus_area": focus_area,
            "results": []
        }
        
        # Run benchmarks for each scenario
        for scenario_id in scenario_ids:
            result = self.run_single_benchmark(agent, scenario_id)
            if result["success"]:
                progression["results"].append({
                    "scenario_id": scenario_id,
                    "score": result["score"],
                    "success": result["score"] >= self.scenario_library.get_scenario(scenario_id).success_threshold
                })
        
        # Calculate progression metrics
        if progression["results"]:
            success_rate = sum(1 for r in progression["results"] if r["success"]) / len(progression["results"])
            progression["success_rate"] = success_rate
            progression["max_difficulty_completed"] = self._get_max_difficulty_completed(
                progression["results"], scenario_ids)
        
        return progression
    
    def _run_benchmark_simulation(self, agent: BaseAgent, scenario: BenchmarkScenario) -> None:
        """
        Simulate running a benchmark scenario.
        
        Args:
            agent: The agent to benchmark
            scenario: The scenario to run
        """
        # In a real implementation, this would set up and run a full simulation
        # based on the scenario parameters. For now, we'll simulate it with some
        # random actions and state updates.
        
        agent_id = agent.id
        duration = scenario.duration
        state_size = 20  # Assume a standard state size for now
        
        # Create a simulated environment state
        state = np.random.rand(state_size)
        
        # Initialize metrics
        kills = 0
        resources = {"energy": 0.0, "health": 0.0, "special": 0.0}
        shots_fired = 0
        shots_hit = 0
        
        # Simulate the benchmark for the specified duration
        steps = min(duration, 100)  # Cap at 100 steps for simulation
        time_per_step = duration / steps
        
        for i in range(steps):
            # Measure decision time
            start_time = time.time()
            action = agent.get_action(state)
            decision_time = time.time() - start_time
            
            # Record the decision time
            self.benchmark_system.record_decision_time(agent_id, decision_time)
            
            # Simulate action outcome based on scenario difficulty
            difficulty_factor = {"easy": 0.7, "medium": 0.5, "hard": 0.3}[scenario.difficulty]
            
            # Simulate combat
            if action == 0:  # Assume 0 is shoot
                shots_fired += 1
                hit = np.random.random() < (difficulty_factor + 0.2)  # Better chance to hit
                self.benchmark_system.record_shot(agent_id, hit)
                shots_hit += 1 if hit else 0
                
                if hit and np.random.random() < difficulty_factor:
                    kills += 1
                    self.benchmark_system.record_kill(agent_id)
            
            # Simulate resource collection
            elif action == 1:  # Assume 1 is collect resource
                if np.random.random() < difficulty_factor:
                    resource_type = np.random.choice(["energy", "health", "special"])
                    amount = np.random.uniform(5.0, 20.0)
                    resources[resource_type] += amount
                    self.benchmark_system.record_resource_collected(agent_id, resource_type, amount)
            
            # Update state for next step
            state = np.random.rand(state_size)
            
            # Add some randomness to score
            score_update = np.random.uniform(-5.0, 10.0) * difficulty_factor
            self.benchmark_system.update_score(agent_id, score_update)
            
            # Simulate time passing
            time.sleep(0.01)  # Small delay to avoid hogging CPU
            
            # Update the benchmark system
            self.benchmark_system.update(time_per_step)
        
        # Ensure the benchmark is finished
        if agent_id in self.benchmark_system.active_benchmarks:
            self.benchmark_system._finish_benchmark(agent_id)
    
    def _generate_comparison_charts(self, comparison: Dict[str, Any], scenario_id: str) -> None:
        """
        Generate comparison charts for agent benchmarks.
        
        Args:
            comparison: The comparison results
            scenario_id: The ID of the scenario
        """
        # In a full implementation, this would generate charts comparing agent performance
        # For now, just log that we would generate charts
        self.logger.info(f"Would generate comparison charts for scenario {scenario_id} " +
                       f"with {len(comparison['agents'])} agents")
    
    def _get_max_difficulty_completed(self, results: List[Dict[str, Any]], 
                                   scenario_ids: List[str]) -> str:
        """
        Get the maximum difficulty level completed successfully.
        
        Args:
            results: The benchmark results
            scenario_ids: The progression scenario IDs
            
        Returns:
            The maximum difficulty completed ("easy", "medium", "hard")
        """
        # Map scenario IDs to difficulties
        scenario_difficulties = {}
        for scenario_id in scenario_ids:
            scenario = self.scenario_library.get_scenario(scenario_id)
            if scenario:
                scenario_difficulties[scenario_id] = scenario.difficulty
        
        # Check which difficulties were completed
        completed_difficulties = set()
        for result in results:
            if result["success"] and result["scenario_id"] in scenario_difficulties:
                completed_difficulties.add(scenario_difficulties[result["scenario_id"]])
        
        # Return max difficulty
        if "hard" in completed_difficulties:
            return "hard"
        elif "medium" in completed_difficulties:
            return "medium"
        elif "easy" in completed_difficulties:
            return "easy"
        else:
            return "none"
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        Generate a comprehensive benchmark report.
        
        Args:
            output_file: Optional file to save the report to
            
        Returns:
            The report as a string
        """
        return self.benchmark_system.generate_report(output_file=output_file)
    
    def generate_performance_graphs(self) -> List[str]:
        """
        Generate performance graphs for all benchmarked agents.
        
        Returns:
            A list of filenames for the generated graphs
        """
        return self.benchmark_system.generate_performance_graphs(
            output_dir=str(self.output_dir / "graphs"))


# Command-line interface
if __name__ == "__main__":
    import argparse
    from systems.agents.agent_factory import create_agent, get_available_agent_types
    
    parser = argparse.ArgumentParser(description='Run agent benchmarks')
    parser.add_argument('--agent', type=str, help='Agent type to benchmark')
    parser.add_argument('--scenario', type=str, help='Scenario ID to run')
    parser.add_argument('--list-agents', action='store_true', help='List available agent types')
    parser.add_argument('--list-scenarios', action='store_true', help='List available scenarios')
    parser.add_argument('--report', action='store_true', help='Generate benchmark report')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    runner = BenchmarkRunner()
    
    if args.list_agents:
        print("Available agent types:")
        for agent_type in get_available_agent_types().keys():
            print(f"  - {agent_type}")
    
    elif args.list_scenarios:
        print("Available scenarios:")
        for scenario in runner.scenario_library.get_all_scenarios():
            print(f"  - {scenario.id}: {scenario.name} ({scenario.difficulty})")
    
    elif args.agent and args.scenario:
        agent = create_agent(args.agent)
        if agent:
            result = runner.run_single_benchmark(agent, args.scenario)
            if result["success"]:
                print(f"Benchmark results for {args.agent} on {args.scenario}:")
                print(f"  Score: {result['score']:.2f}")
                print(f"  Survival time: {result['survival_time']:.2f}s")
                print(f"  Kills: {result['kills']}")
                print(f"  Accuracy: {result['accuracy']:.2%}")
            else:
                print(f"Benchmark failed: {result.get('error', 'Unknown error')}")
        else:
            print(f"Agent type not found: {args.agent}")
    
    elif args.report:
        report = runner.generate_report()
        print(report)
        
        # Generate graphs
        graph_files = runner.generate_performance_graphs()
        print(f"Generated {len(graph_files)} performance graphs")
    
    else:
        parser.print_help() 