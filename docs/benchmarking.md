# Agent Benchmarking System

The Agent Benchmarking System provides standardized tools for evaluating agent performance across different scenarios, enabling quantitative comparison between agent implementations and tracking improvements over time.

## Core Components

### BenchmarkSystem

Central system that manages benchmarks, tracks metrics, and generates reports.

```python
from systems.benchmarking import BenchmarkSystem

# Typically accessed through the system manager
benchmark_system = system_manager.get_system("BenchmarkSystem")
```

### BenchmarkScenario

Defines a specific test scenario with environment parameters, objectives, and success criteria.

```python
from systems.benchmarking import BenchmarkScenario

# Example scenario structure
scenario = BenchmarkScenario(
    id="combat_basic",
    name="Basic Combat Test",
    description="Tests agent combat capabilities against standard enemies",
    difficulty="medium",
    duration=120,  # seconds
    environment_params={"terrain": "arena", "obstacles": 5},
    enemy_params={"count": 3, "types": ["basic"], "difficulty": "medium"},
    resource_params={"health_packs": 2, "energy": 3},
    objective="combat",
    success_threshold=75.0,
    tags=["combat", "basic"]
)
```

### BenchmarkScenarioLibrary

Provides access to predefined benchmark scenarios organized by type and difficulty.

```python
from systems.benchmarking import BenchmarkScenarioLibrary

# Get scenarios
library = BenchmarkScenarioLibrary()
combat_scenarios = library.get_scenarios_by_objective("combat")
hard_scenarios = library.get_scenarios_by_difficulty("hard")
scenarios_with_tags = library.get_scenarios_by_tags(["team", "resource"])
```

### BenchmarkRunner

Handles the execution of benchmarks and comparison of agents.

```python
from systems.benchmarking import BenchmarkRunner

# Create and run benchmarks
runner = BenchmarkRunner()
result = runner.run_single_benchmark(my_agent, "survival_basic")
comparison = runner.run_agent_comparison([agent1, agent2, agent3], "combat_advanced")
progression = runner.run_agent_progression(learning_agent, "balanced")
```

## Standard Scenarios

The system includes several categories of benchmark scenarios:

### Combat Scenarios

Tests agent's ability to engage and defeat enemies efficiently.

- **combat_basic**: Standard combat against 3 basic enemies
- **combat_intermediate**: Mixed enemy types with varied attack patterns
- **combat_advanced**: Multiple waves with increasing difficulty
- **combat_boss**: Single powerful enemy requiring tactical approaches

### Survival Scenarios

Tests agent's ability to survive in challenging environments.

- **survival_basic**: Survive for a set time with minimal threats
- **survival_intermediate**: Survive with limited resources and regular threats
- **survival_advanced**: Survive in hazardous environments with aggressive enemies
- **survival_extreme**: Survive against overwhelming odds with dwindling resources

### Resource Scenarios

Tests agent's ability to collect and manage resources efficiently.

- **resource_basic**: Collect specific resources with minimal opposition
- **resource_competition**: Compete for limited resources against enemies
- **resource_priority**: Manage priorities between different resource types
- **resource_extraction**: Extract resources from protected nodes

### Team Scenarios

Tests agent's effectiveness in team-based operations.

- **team_coordination**: Basic coordination with allied agents
- **team_formation**: Maintain formations and coordinated movement
- **team_roles**: Specialize in complementary roles to achieve objectives
- **team_vs_team**: Compete against another team of agents

## Running Benchmarks

### Basic Usage

```python
from systems.agents import MLPAgent
from systems.benchmarking import BenchmarkRunner

# Create an agent to benchmark
agent = MLPAgent("TestAgent")
agent.initialize(state_size=64, action_size=5)

# Run a single benchmark
runner = BenchmarkRunner()
result = runner.run_single_benchmark(agent, "combat_basic")
print(f"Agent score: {result['score']}")
```

### Comparing Agents

```python
from systems.agents import MLPAgent, PerceptronAgent
from systems.benchmarking import BenchmarkRunner

# Create agents to compare
agents = [
    MLPAgent("MLP-1"),
    MLPAgent("MLP-2"),
    PerceptronAgent("Perceptron-1")
]
for agent in agents:
    agent.initialize(state_size=64, action_size=5)

# Compare agents on a specific scenario
runner = BenchmarkRunner()
comparison = runner.run_agent_comparison(agents, "survival_intermediate")

# Print rankings
print("Agent Rankings:")
for rank, (agent_id, score) in enumerate(comparison["rankings"]):
    print(f"{rank+1}. {agent_id}: {score:.2f}")
```

### Tracking Agent Progression

```python
from systems.agents import TeamAgent
from systems.benchmarking import BenchmarkRunner

# Create a learning agent
agent = TeamAgent("Learning-Agent")
agent.initialize(state_size=64, action_size=5)

# Run progression benchmarks
runner = BenchmarkRunner()
progression = runner.run_agent_progression(agent, focus_area="combat")

# Show improvement over time
print("Progression Results:")
for difficulty, result in progression["results"].items():
    print(f"{difficulty}: {'Passed' if result['passed'] else 'Failed'} - Score: {result['score']:.2f}")
```

## Interpreting Results

Benchmark results include the following metrics:

- **Score**: Overall performance score (0-100)
- **Survival Time**: How long the agent survived (seconds)
- **Kills**: Number of enemies defeated
- **Resources Collected**: Amount of each resource type collected
- **Accuracy**: Percentage of successful attacks/actions
- **Decision Time**: Average and maximum time for making decisions

### Success Criteria

Each scenario has a specific `success_threshold` that defines the minimum score required to consider the benchmark passed. This threshold is calibrated for each scenario based on:

1. Difficulty level
2. Objective type
3. Environmental challenges

### Visualizing Results

The BenchmarkSystem can generate visual reports for easier analysis:

```python
# Generate a report file
benchmark_system.generate_report(output_file="benchmark_report.html")

# Generate performance graphs
graph_files = benchmark_system.generate_performance_graphs()
```

## Command-Line Interface

The benchmarking system includes a simple command-line interface for running benchmarks:

```bash
python -m tools.benchmark_cli run --agent MLPAgent --scenario combat_basic
python -m tools.benchmark_cli compare --agents MLPAgent,PerceptronAgent --scenario survival_advanced
python -m tools.benchmark_cli report --output benchmark_results.html
```

## GUI Interface

A graphical interface is available for interactive benchmarking:

```bash
python -m tools.benchmark_gui
```

The GUI provides:
- Agent selection
- Scenario browsing and selection
- Real-time results display
- Comparative charts
- Report generation

## Best Practices

1. **Benchmark early and often** during development to track progress
2. **Use consistent scenarios** when comparing iterations of an agent
3. **Run multiple trials** for more reliable results
4. **Compare against baseline agents** to contextualize performance
5. **Focus on specific metrics** relevant to your agent's design goals 