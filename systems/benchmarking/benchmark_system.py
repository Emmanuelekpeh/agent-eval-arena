import numpy as np
import time
import logging
import json
import os
from typing import Dict, List, Any, Optional, Tuple, Type
from dataclasses import dataclass, field
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path

from systems.agents.base_agent import BaseAgent
from systems.core.base_system import BaseSystem

@dataclass
class BenchmarkResult:
    """Stores the result of a benchmark run for a single agent."""
    agent_id: str
    agent_type: str
    scenario_id: str
    score: float
    survival_time: float
    kills: int
    resources_collected: Dict[str, float]
    accuracy: float
    decision_times: List[float]
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "scenario_id": self.scenario_id,
            "score": self.score,
            "survival_time": self.survival_time,
            "kills": self.kills,
            "resources_collected": self.resources_collected,
            "accuracy": self.accuracy,
            "avg_decision_time": np.mean(self.decision_times) if self.decision_times else 0,
            "max_decision_time": max(self.decision_times) if self.decision_times else 0,
            "metrics": self.metrics,
            "timestamp": self.timestamp
        }

@dataclass
class BenchmarkScenario:
    """Defines a benchmark scenario for testing agents."""
    id: str
    name: str
    description: str
    difficulty: str  # "easy", "medium", "hard"
    duration: int  # in seconds
    environment_params: Dict[str, Any]
    enemy_params: Dict[str, Any]
    resource_params: Dict[str, Any]
    objective: str  # "survival", "combat", "resource", "mixed"
    success_threshold: float
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the scenario to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "difficulty": self.difficulty,
            "duration": self.duration,
            "environment_params": self.environment_params,
            "enemy_params": self.enemy_params,
            "resource_params": self.resource_params,
            "objective": self.objective,
            "success_threshold": self.success_threshold,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BenchmarkScenario':
        """Create a scenario from a dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            difficulty=data["difficulty"],
            duration=data["duration"],
            environment_params=data["environment_params"],
            enemy_params=data["enemy_params"],
            resource_params=data["resource_params"],
            objective=data["objective"],
            success_threshold=data["success_threshold"],
            tags=data.get("tags", [])
        )

class BenchmarkSystem(BaseSystem):
    """System for benchmarking agent performance across various scenarios."""
    
    def __init__(self, results_dir: str = "benchmark_results"):
        super().__init__(name="BenchmarkSystem", priority=0)
        self.results_dir = Path(results_dir)
        self.scenarios: Dict[str, BenchmarkScenario] = {}
        self.results: Dict[str, List[BenchmarkResult]] = {}
        self.current_scenario: Optional[BenchmarkScenario] = None
        self.active_benchmarks: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        
    def _initialize(self) -> None:
        """Initialize the benchmark system."""
        self.results_dir.mkdir(exist_ok=True, parents=True)
        self._load_default_scenarios()
        self._load_previous_results()
        self.logger.info("Benchmark system initialized")
    
    def _shutdown(self) -> None:
        """Clean up resources when shutting down."""
        self._save_results()
        self.logger.info("Benchmark system shutdown")
    
    def _update(self, delta_time: float) -> None:
        """Update active benchmarks."""
        for agent_id, benchmark in list(self.active_benchmarks.items()):
            benchmark["elapsed_time"] += delta_time
            
            # Check if benchmark duration has been reached
            if benchmark["elapsed_time"] >= benchmark["scenario"].duration:
                self._finish_benchmark(agent_id)
    
    def _load_default_scenarios(self) -> None:
        """Load default benchmark scenarios."""
        # Survival scenario
        self.scenarios["survival_basic"] = BenchmarkScenario(
            id="survival_basic",
            name="Basic Survival",
            description="Test the agent's ability to survive for a period of time",
            difficulty="easy",
            duration=300,  # 5 minutes
            environment_params={
                "map_size": 800,
                "obstacles": 10,
                "hazards": 5
            },
            enemy_params={
                "count": 5,
                "spawn_rate": 0.2,
                "difficulty": "easy"
            },
            resource_params={
                "energy_count": 10,
                "health_count": 5
            },
            objective="survival",
            success_threshold=240,  # survive at least 4 minutes
            tags=["survival", "basic"]
        )
        
        # Combat scenario
        self.scenarios["combat_basic"] = BenchmarkScenario(
            id="combat_basic",
            name="Basic Combat",
            description="Test the agent's combat effectiveness",
            difficulty="medium",
            duration=240,  # 4 minutes
            environment_params={
                "map_size": 600,
                "obstacles": 8,
                "hazards": 2
            },
            enemy_params={
                "count": 10,
                "spawn_rate": 0.4,
                "difficulty": "medium"
            },
            resource_params={
                "energy_count": 5,
                "health_count": 3
            },
            objective="combat",
            success_threshold=5,  # kill at least 5 enemies
            tags=["combat", "basic"]
        )
        
        # Resource collection scenario
        self.scenarios["resource_basic"] = BenchmarkScenario(
            id="resource_basic",
            name="Resource Collection",
            description="Test the agent's ability to efficiently collect resources",
            difficulty="easy",
            duration=180,  # 3 minutes
            environment_params={
                "map_size": 700,
                "obstacles": 15,
                "hazards": 0
            },
            enemy_params={
                "count": 3,
                "spawn_rate": 0.1,
                "difficulty": "easy"
            },
            resource_params={
                "energy_count": 20,
                "health_count": 10,
                "special_count": 5
            },
            objective="resource",
            success_threshold=15,  # collect at least 15 resources
            tags=["resource", "basic"]
        )
        
        # Team coordination scenario
        self.scenarios["team_basic"] = BenchmarkScenario(
            id="team_basic",
            name="Team Coordination",
            description="Test the agent's ability to coordinate with team members",
            difficulty="hard",
            duration=360,  # 6 minutes
            environment_params={
                "map_size": 1000,
                "obstacles": 20,
                "hazards": 8
            },
            enemy_params={
                "count": 15,
                "spawn_rate": 0.3,
                "difficulty": "hard"
            },
            resource_params={
                "energy_count": 15,
                "health_count": 10,
                "special_count": 5
            },
            objective="mixed",
            success_threshold=100,  # combined score of at least 100
            tags=["team", "coordination", "advanced"]
        )
        
        self.logger.info(f"Loaded {len(self.scenarios)} default benchmark scenarios")
    
    def _load_previous_results(self) -> None:
        """Load previous benchmark results from disk."""
        results_file = self.results_dir / "benchmark_results.json"
        if results_file.exists():
            try:
                with open(results_file, 'r') as f:
                    data = json.load(f)
                
                for agent_type, results in data.items():
                    self.results[agent_type] = []
                    for result_data in results:
                        result = BenchmarkResult(
                            agent_id=result_data["agent_id"],
                            agent_type=result_data["agent_type"],
                            scenario_id=result_data["scenario_id"],
                            score=result_data["score"],
                            survival_time=result_data["survival_time"],
                            kills=result_data["kills"],
                            resources_collected=result_data["resources_collected"],
                            accuracy=result_data["accuracy"],
                            decision_times=[],  # We don't save the full list
                            metrics=result_data["metrics"],
                            timestamp=result_data["timestamp"]
                        )
                        self.results[agent_type].append(result)
                
                self.logger.info(f"Loaded benchmark results for {len(self.results)} agent types")
            except Exception as e:
                self.logger.error(f"Failed to load benchmark results: {str(e)}")
    
    def _save_results(self) -> None:
        """Save benchmark results to disk."""
        results_file = self.results_dir / "benchmark_results.json"
        try:
            # Convert results to a format suitable for JSON serialization
            serialized_results = {}
            for agent_type, results in self.results.items():
                serialized_results[agent_type] = [r.to_dict() for r in results]
            
            with open(results_file, 'w') as f:
                json.dump(serialized_results, f, indent=2)
            
            self.logger.info(f"Saved benchmark results to {results_file}")
        except Exception as e:
            self.logger.error(f"Failed to save benchmark results: {str(e)}")
    
    def add_scenario(self, scenario: BenchmarkScenario) -> None:
        """
        Add a new benchmark scenario.
        
        Args:
            scenario: The scenario to add
        """
        if scenario.id in self.scenarios:
            self.logger.warning(f"Overwriting existing scenario: {scenario.id}")
        
        self.scenarios[scenario.id] = scenario
        self.logger.info(f"Added benchmark scenario: {scenario.id}")
    
    def get_scenario(self, scenario_id: str) -> Optional[BenchmarkScenario]:
        """
        Get a benchmark scenario by ID.
        
        Args:
            scenario_id: The ID of the scenario to get
            
        Returns:
            The scenario, or None if not found
        """
        return self.scenarios.get(scenario_id)
    
    def start_benchmark(self, agent: BaseAgent, scenario_id: str) -> bool:
        """
        Start a benchmark for an agent.
        
        Args:
            agent: The agent to benchmark
            scenario_id: The ID of the scenario to run
            
        Returns:
            True if the benchmark was started, False otherwise
        """
        if agent.id in self.active_benchmarks:
            self.logger.warning(f"Agent {agent.id} is already being benchmarked")
            return False
        
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            self.logger.error(f"Scenario not found: {scenario_id}")
            return False
        
        # Initialize benchmark data
        self.active_benchmarks[agent.id] = {
            "scenario": scenario,
            "elapsed_time": 0.0,
            "agent": agent,
            "agent_type": agent.__class__.__name__,
            "start_time": time.time(),
            "score": 0.0,
            "kills": 0,
            "resources_collected": {"energy": 0.0, "health": 0.0, "special": 0.0},
            "shots_fired": 0,
            "shots_hit": 0,
            "decision_times": []
        }
        
        self.logger.info(f"Started benchmark: {agent.id} on {scenario_id}")
        return True
    
    def record_decision_time(self, agent_id: str, decision_time: float) -> None:
        """
        Record the time taken for an agent to make a decision.
        
        Args:
            agent_id: The ID of the agent
            decision_time: The time taken in seconds
        """
        if agent_id in self.active_benchmarks:
            self.active_benchmarks[agent_id]["decision_times"].append(decision_time)
    
    def record_kill(self, agent_id: str) -> None:
        """
        Record a kill for an agent.
        
        Args:
            agent_id: The ID of the agent
        """
        if agent_id in self.active_benchmarks:
            self.active_benchmarks[agent_id]["kills"] += 1
            self.active_benchmarks[agent_id]["score"] += 10  # Base score for a kill
    
    def record_shot(self, agent_id: str, hit: bool) -> None:
        """
        Record a shot fired by an agent.
        
        Args:
            agent_id: The ID of the agent
            hit: Whether the shot hit a target
        """
        if agent_id in self.active_benchmarks:
            self.active_benchmarks[agent_id]["shots_fired"] += 1
            if hit:
                self.active_benchmarks[agent_id]["shots_hit"] += 1
                self.active_benchmarks[agent_id]["score"] += 2  # Small score for a hit
    
    def record_resource_collected(self, agent_id: str, resource_type: str, amount: float) -> None:
        """
        Record a resource collected by an agent.
        
        Args:
            agent_id: The ID of the agent
            resource_type: The type of resource collected
            amount: The amount collected
        """
        if agent_id in self.active_benchmarks:
            if resource_type in self.active_benchmarks[agent_id]["resources_collected"]:
                self.active_benchmarks[agent_id]["resources_collected"][resource_type] += amount
            else:
                self.active_benchmarks[agent_id]["resources_collected"][resource_type] = amount
            
            self.active_benchmarks[agent_id]["score"] += amount  # Score based on amount
    
    def update_score(self, agent_id: str, score_delta: float) -> None:
        """
        Update an agent's score.
        
        Args:
            agent_id: The ID of the agent
            score_delta: The amount to change the score by
        """
        if agent_id in self.active_benchmarks:
            self.active_benchmarks[agent_id]["score"] += score_delta
    
    def _finish_benchmark(self, agent_id: str) -> None:
        """
        Finish a benchmark for an agent.
        
        Args:
            agent_id: The ID of the agent
        """
        if agent_id not in self.active_benchmarks:
            self.logger.warning(f"No active benchmark for agent {agent_id}")
            return
        
        benchmark = self.active_benchmarks[agent_id]
        
        # Calculate accuracy
        accuracy = 0.0
        if benchmark["shots_fired"] > 0:
            accuracy = benchmark["shots_hit"] / benchmark["shots_fired"]
        
        # Create benchmark result
        result = BenchmarkResult(
            agent_id=agent_id,
            agent_type=benchmark["agent_type"],
            scenario_id=benchmark["scenario"].id,
            score=benchmark["score"],
            survival_time=benchmark["elapsed_time"],
            kills=benchmark["kills"],
            resources_collected=benchmark["resources_collected"],
            accuracy=accuracy,
            decision_times=benchmark["decision_times"],
            metrics={
                "shots_fired": benchmark["shots_fired"],
                "shots_hit": benchmark["shots_hit"]
            }
        )
        
        # Add to results
        if benchmark["agent_type"] not in self.results:
            self.results[benchmark["agent_type"]] = []
        
        self.results[benchmark["agent_type"]].append(result)
        
        # Remove from active benchmarks
        del self.active_benchmarks[agent_id]
        
        # Save results
        self._save_results()
        
        self.logger.info(f"Finished benchmark for {agent_id} with score {result.score:.2f}")
    
    def cancel_benchmark(self, agent_id: str) -> bool:
        """
        Cancel an active benchmark.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            True if the benchmark was canceled, False otherwise
        """
        if agent_id in self.active_benchmarks:
            del self.active_benchmarks[agent_id]
            self.logger.info(f"Canceled benchmark for {agent_id}")
            return True
        
        return False
    
    def get_results(self, agent_type: Optional[str] = None, 
                    scenario_id: Optional[str] = None) -> List[BenchmarkResult]:
        """
        Get benchmark results.
        
        Args:
            agent_type: Optional filter by agent type
            scenario_id: Optional filter by scenario ID
            
        Returns:
            A list of benchmark results
        """
        results = []
        
        # Collect results matching the filters
        for a_type, type_results in self.results.items():
            if agent_type and a_type != agent_type:
                continue
            
            for result in type_results:
                if scenario_id and result.scenario_id != scenario_id:
                    continue
                
                results.append(result)
        
        return results
    
    def get_agent_rankings(self, scenario_id: str) -> List[Tuple[str, float]]:
        """
        Get a ranking of agent types for a specific scenario.
        
        Args:
            scenario_id: The ID of the scenario
            
        Returns:
            A list of (agent_type, average_score) tuples, sorted by score
        """
        rankings = []
        
        for agent_type, results in self.results.items():
            # Filter results for this scenario
            scenario_results = [r for r in results if r.scenario_id == scenario_id]
            
            if scenario_results:
                avg_score = sum(r.score for r in scenario_results) / len(scenario_results)
                rankings.append((agent_type, avg_score))
        
        # Sort by score (descending)
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return rankings
    
    def generate_report(self, scenario_id: Optional[str] = None,
                        agent_type: Optional[str] = None,
                        output_file: Optional[str] = None) -> str:
        """
        Generate a benchmark report.
        
        Args:
            scenario_id: Optional filter by scenario ID
            agent_type: Optional filter by agent type
            output_file: Optional file to save the report to
            
        Returns:
            The report as a string
        """
        results = self.get_results(agent_type=agent_type, scenario_id=scenario_id)
        
        # Group results by scenario and agent type
        by_scenario = {}
        by_agent_type = {}
        
        for result in results:
            # Group by scenario
            if result.scenario_id not in by_scenario:
                by_scenario[result.scenario_id] = []
            by_scenario[result.scenario_id].append(result)
            
            # Group by agent type
            if result.agent_type not in by_agent_type:
                by_agent_type[result.agent_type] = []
            by_agent_type[result.agent_type].append(result)
        
        # Generate report
        report = "# Agent Benchmark Report\n\n"
        report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if scenario_id:
            scenario = self.get_scenario(scenario_id)
            if scenario:
                report += f"## Scenario: {scenario.name}\n\n"
                report += f"Description: {scenario.description}\n"
                report += f"Difficulty: {scenario.difficulty}\n"
                report += f"Duration: {scenario.duration} seconds\n"
                report += f"Objective: {scenario.objective}\n\n"
        
        # Overall rankings
        report += "## Overall Rankings\n\n"
        
        if by_scenario:
            report += "| Scenario | Agent Type | Avg Score | Avg Survival Time | Avg Kills | Avg Accuracy |\n"
            report += "|----------|------------|-----------|-------------------|-----------|-------------|\n"
            
            for s_id, s_results in by_scenario.items():
                # Group by agent type within scenario
                s_by_agent = {}
                for r in s_results:
                    if r.agent_type not in s_by_agent:
                        s_by_agent[r.agent_type] = []
                    s_by_agent[r.agent_type].append(r)
                
                # Calculate averages
                for a_type, a_results in s_by_agent.items():
                    avg_score = sum(r.score for r in a_results) / len(a_results)
                    avg_survival = sum(r.survival_time for r in a_results) / len(a_results)
                    avg_kills = sum(r.kills for r in a_results) / len(a_results)
                    avg_accuracy = sum(r.accuracy for r in a_results) / len(a_results)
                    
                    scenario_name = self.get_scenario(s_id).name if self.get_scenario(s_id) else s_id
                    report += f"| {scenario_name} | {a_type} | {avg_score:.2f} | {avg_survival:.2f}s | {avg_kills:.2f} | {avg_accuracy:.2%} |\n"
        else:
            report += "No results available.\n\n"
        
        # Save report if output file specified
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report)
            except Exception as e:
                self.logger.error(f"Failed to save report: {str(e)}")
        
        return report
    
    def generate_performance_graphs(self, output_dir: Optional[str] = None) -> List[str]:
        """
        Generate performance graphs for benchmark results.
        
        Args:
            output_dir: Optional directory to save the graphs to
            
        Returns:
            A list of filenames for the generated graphs
        """
        if not self.results:
            self.logger.warning("No benchmark results to generate graphs from")
            return []
        
        if output_dir:
            graph_dir = Path(output_dir)
            graph_dir.mkdir(exist_ok=True, parents=True)
        else:
            graph_dir = self.results_dir / "graphs"
            graph_dir.mkdir(exist_ok=True, parents=True)
        
        filenames = []
        
        # Generate a score comparison graph across scenarios
        try:
            plt.figure(figsize=(12, 8))
            scenarios = list(self.scenarios.keys())
            agent_types = list(self.results.keys())
            
            # Prepare data
            data = {}
            for agent_type in agent_types:
                data[agent_type] = []
                for scenario_id in scenarios:
                    # Filter results for this agent type and scenario
                    filtered_results = [r for r in self.results[agent_type] 
                                       if r.scenario_id == scenario_id]
                    
                    if filtered_results:
                        avg_score = sum(r.score for r in filtered_results) / len(filtered_results)
                        data[agent_type].append(avg_score)
                    else:
                        data[agent_type].append(0)
            
            # Plot data
            x = np.arange(len(scenarios))
            width = 0.8 / len(agent_types)
            
            for i, agent_type in enumerate(agent_types):
                plt.bar(x + i * width, data[agent_type], width, label=agent_type)
            
            plt.xlabel('Scenario')
            plt.ylabel('Average Score')
            plt.title('Agent Performance by Scenario')
            plt.xticks(x + width * (len(agent_types) - 1) / 2, scenarios)
            plt.legend()
            
            # Save figure
            filename = graph_dir / "scenario_comparison.png"
            plt.savefig(filename)
            plt.close()
            
            filenames.append(str(filename))
            self.logger.info(f"Generated scenario comparison graph: {filename}")
        except Exception as e:
            self.logger.error(f"Failed to generate scenario comparison graph: {str(e)}")
        
        # Generate performance metrics for each agent type
        for agent_type in agent_types:
            try:
                plt.figure(figsize=(12, 8))
                
                # Prepare data
                timestamps = []
                scores = []
                
                # Sort results by timestamp
                sorted_results = sorted(self.results[agent_type], 
                                       key=lambda r: datetime.fromisoformat(r.timestamp))
                
                for i, result in enumerate(sorted_results):
                    timestamps.append(i)  # Use index for x-axis
                    scores.append(result.score)
                
                plt.plot(timestamps, scores, 'o-', label='Score')
                
                plt.xlabel('Benchmark Run')
                plt.ylabel('Score')
                plt.title(f'Performance Trend: {agent_type}')
                plt.legend()
                
                # Save figure
                filename = graph_dir / f"trend_{agent_type}.png"
                plt.savefig(filename)
                plt.close()
                
                filenames.append(str(filename))
                self.logger.info(f"Generated trend graph for {agent_type}: {filename}")
            except Exception as e:
                self.logger.error(f"Failed to generate trend graph for {agent_type}: {str(e)}")
        
        return filenames
    
    def compare_agents(self, agent_types: List[str], scenario_id: str) -> Dict[str, Any]:
        """
        Compare multiple agent types on a specific scenario.
        
        Args:
            agent_types: The agent types to compare
            scenario_id: The scenario to compare on
            
        Returns:
            A dictionary with comparison metrics
        """
        comparison = {
            "scenario_id": scenario_id,
            "agent_comparisons": []
        }
        
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            self.logger.error(f"Scenario not found: {scenario_id}")
            return comparison
        
        for agent_type in agent_types:
            # Filter results for this agent type and scenario
            filtered_results = [r for r in self.results.get(agent_type, []) 
                               if r.scenario_id == scenario_id]
            
            if not filtered_results:
                comparison["agent_comparisons"].append({
                    "agent_type": agent_type,
                    "runs": 0,
                    "metrics": {}
                })
                continue
            
            # Calculate metrics
            avg_score = sum(r.score for r in filtered_results) / len(filtered_results)
            avg_survival = sum(r.survival_time for r in filtered_results) / len(filtered_results)
            avg_kills = sum(r.kills for r in filtered_results) / len(filtered_results)
            avg_accuracy = sum(r.accuracy for r in filtered_results) / len(filtered_results)
            
            # Calculate success rate
            success_count = sum(1 for r in filtered_results if r.score >= scenario.success_threshold)
            success_rate = success_count / len(filtered_results)
            
            # Calculate resource efficiency
            total_resources = sum(sum(r.resources_collected.values()) for r in filtered_results)
            if total_resources > 0:
                resource_score_ratio = sum(r.score for r in filtered_results) / total_resources
            else:
                resource_score_ratio = 0
            
            comparison["agent_comparisons"].append({
                "agent_type": agent_type,
                "runs": len(filtered_results),
                "metrics": {
                    "avg_score": avg_score,
                    "avg_survival_time": avg_survival,
                    "avg_kills": avg_kills,
                    "avg_accuracy": avg_accuracy,
                    "success_rate": success_rate,
                    "resource_score_ratio": resource_score_ratio
                }
            })
        
        return comparison 