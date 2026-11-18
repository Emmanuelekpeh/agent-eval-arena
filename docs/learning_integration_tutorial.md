# Learning Integration Tutorial

This tutorial shows how to use the enhanced learning integration system to make your agents adapt their strategies based on successes and failures.

## Overview

The learning integration system connects pattern recognition with strategy adaptation. It allows agents to:

1. Recognize patterns in their experiences
2. Assess the risk of actions in different contexts
3. Adapt strategies based on what works and what doesn't
4. Share successful strategies with teammates

## Basic Usage

### 1. Initialization

First, create the pattern recognition and learning integration systems:

```python
from systems.learning.pattern_recognition_system import PatternRecognitionSystem
from systems.learning.strategy_adaptation import StrategyAdaptationSystem
from systems.learning.learning_integration import LearningIntegration

# Create the systems
pattern_system = PatternRecognitionSystem()
strategy_system = StrategyAdaptationSystem()

# Create the integration
learning = LearningIntegration(
    pattern_system=pattern_system,
    strategy_system=strategy_system
)
```

### 2. Setting Up Agent Personalities

Connect your agents' personalities to influence their learning:

```python
# Set personality traits
pattern_system.integrate_personality(
    agent_id="agent1",
    traits={
        "openness": 0.7,        # Willingness to try new actions
        "conscientiousness": 0.6,  # Precision in pattern matching
        "risk_taking": 0.4      # Risk tolerance
    }
)
```

### 3. Recording Experiences

As your agents interact with the environment, record their experiences:

```python
# Get current state and context
state = env.get_state_for_agent(agent_id)
context = {
    "health": agent.health,
    "enemies_nearby": len(env.get_nearby_enemies(agent_id, radius=100)),
    "cover_available": env.is_cover_available(agent_id)
}

# Take an action
action = agent.choose_action(state)

# Receive reward
reward = env.step(agent_id, action)

# Record the experience
learning.record_experience(
    agent_id=agent_id,
    state=state,
    action=action,
    reward=reward,
    context=context
)
```

### 4. Getting Action Suggestions

When your agent needs to make a decision, get a suggestion based on past patterns:

```python
# Get current state and context
state = env.get_state_for_agent(agent_id)
context = {
    "health": agent.health,
    "enemies_nearby": len(env.get_nearby_enemies(agent_id, radius=100)),
    "cover_available": env.is_cover_available(agent_id)
}

# Get action suggestion with risk assessment
action, assessment = learning.suggest_action(agent_id, state, context)

# See the assessment details
print(f"Suggested action: {action}")
print(f"Confidence: {assessment['confidence']}")
print(f"Risk level: {assessment['risk_level']}")
print(f"Expected outcome: {assessment['outcome_prediction']}")

# Agent can decide whether to take the suggestion based on risk tolerance
if assessment['risk_level'] > agent.risk_tolerance:
    # Choose a safer action
    action = agent.get_default_action()
```

### 5. Adapting Strategies

Periodically adapt strategies based on accumulated experiences:

```python
# Analyze patterns and adapt strategies
adjustments = learning.adapt_strategies(agent_id)

# See what adjustments were made
for adjustment in adjustments:
    if adjustment["type"] == "success_factor":
        print(f"Found success factor: {adjustment['factor']} = {adjustment['value']}")
    elif adjustment["type"] == "risk_avoidance":
        print(f"Avoiding risky state dimension {adjustment['dimension']}")
```

### 6. Sharing Strategies Between Agents

Allow agents to share successful strategies with teammates:

```python
# Share strategies from an experienced agent to a new one
shared_strategies = learning.share_successful_strategies(
    source_agent_id="experienced_agent",
    target_agent_id="new_agent"
)

print(f"Shared {len(shared_strategies)} successful strategies")
```

## Advanced Features

### Analyzing Success and Failure Factors

Get deeper insights into what's working and what's not:

```python
# Get pattern analysis from the pattern system directly
analysis = pattern_system.analyze_success_failure_patterns(agent_id)

# Extract common factors in successful patterns
print("Success factors:")
for factor, values in analysis["success_factors"].items():
    print(f"  {factor}: {values}")

# Extract state characteristics that lead to success
print("High reward state characteristics:")
for state_char in analysis["high_reward_states"]:
    print(f"  Dimension {state_char['dimension']}: {state_char['value']}")
```

### Getting Pattern Feedback

Get detailed feedback about specific patterns:

```python
# Get pattern ID (typically from an assessment)
pattern_id = f"{agent_id}_0"

# Get feedback about this pattern
feedback = pattern_system.get_pattern_feedback(agent_id, pattern_id)

print(f"Pattern success rate: {feedback['success_rate']}")
print(f"Pattern failure rate: {feedback['failure_rate']}")
print(f"Average reward: {feedback['average_reward']}")
```

## Integration with Team Systems

The learning integration works well with team-based gameplay:

```python
# After forming teams, share knowledge within the team
for agent_id in team.members:
    if agent_id != team.leader:
        # Share leader's knowledge with team members
        learning.share_successful_strategies(
            source_agent_id=team.leader,
            target_agent_id=agent_id
        )
```

## Integration with Environment

For environment-aware learning:

```python
# When environment conditions change, update context accordingly
def get_context(agent, env):
    context = {
        "health": agent.health,
        "enemies_nearby": len(env.get_nearby_enemies(agent.id, radius=100)),
        "cover_available": env.is_cover_available(agent.id)
    }
    
    # Add environment-specific factors
    if env.is_night_time():
        context["visibility"] = "low"
    else:
        context["visibility"] = "high"
        
    # Add hazard information
    hazards = env.get_nearby_hazards(agent.id, radius=50)
    if hazards:
        context["hazard_nearby"] = True
        context["hazard_type"] = hazards[0].type
    
    return context
```

## Practical Tips

1. **Start with simple contexts**: Begin with a few key context variables that clearly influence outcomes.

2. **Record diverse experiences**: Make sure to record both successes and failures to help the system learn.

3. **Adapt strategies periodically**: Don't adapt after every experience; batch experiences and adapt periodically.

4. **Tune personality traits**: Different personality configurations lead to different learning behaviors.

5. **Monitor performance**: Keep track of how strategies evolve over time to ensure improvement.

6. **Combine with other systems**: The learning integration works best when combined with personality, team, and environmental systems. 