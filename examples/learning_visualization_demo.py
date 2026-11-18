"""
Learning Visualization Demo

This script demonstrates how to use the LearningVisualizer to track and visualize 
agent learning progress, pattern recognition, and strategy adaptation.
"""

import sys
import os
import random
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from systems.visualization.learning_visualizer import LearningVisualizer
from systems.learning.pattern_recognition_system import PatternRecognitionSystem
from systems.learning.strategy_adaptation_system import StrategyAdaptationSystem

def generate_sample_learning_data(agent_id, n_steps, with_improvement=True):
    """Generate sample learning data for demonstration purposes."""
    data = []
    base_reward = 0.0
    
    for i in range(n_steps):
        if with_improvement:
            # Simulate learning improvement over time with random noise
            reward = base_reward + (i / n_steps) * 10 + random.uniform(-1.0, 1.0)
            loss = max(0.5, 5.0 - (i / n_steps) * 4) + random.uniform(-0.2, 0.2)
        else:
            # Simulate random performance without improvement
            reward = base_reward + random.uniform(-2.0, 2.0)
            loss = random.uniform(1.0, 5.0)
        
        # Create a sample data point
        data.append({
            'rewards': reward,
            'losses': loss,
            'actions_taken': random.randint(1, 10),
            'exploration_rate': max(0.1, 1.0 - (i / n_steps) * 0.9)
        })
    
    return data

def generate_sample_pattern_data(agent_id, n_steps):
    """Generate sample pattern recognition data."""
    data = []
    base_timestamp = datetime.now() - timedelta(hours=n_steps)
    
    total_patterns = 0
    success_patterns = 0
    
    for i in range(n_steps):
        # Simulate discovering new patterns over time
        if random.random() < 0.3:  # 30% chance to discover a new pattern
            total_patterns += 1
            if random.random() < 0.7:  # 70% chance the pattern is successful
                success_patterns += 1
        
        # Calculate metrics
        avg_success_rate = success_patterns / max(1, total_patterns)
        highest_success_rate = min(1.0, avg_success_rate + random.uniform(0, 0.2))
        
        data.append({
            'timestamp': base_timestamp + timedelta(hours=i),
            'total_patterns': total_patterns,
            'avg_success_rate': avg_success_rate,
            'highest_success_rate': highest_success_rate,
            'most_successful_pattern_rate': highest_success_rate,
            'avg_use_count': random.randint(1, 10),
            'success_patterns': success_patterns,
            'failure_patterns': total_patterns - success_patterns
        })
    
    return data

def generate_sample_strategy_data(agent_id, n_steps):
    """Generate sample strategy adaptation data."""
    data = []
    base_timestamp = datetime.now() - timedelta(hours=n_steps)
    base_success_rate = 0.3
    
    for i in range(n_steps):
        # Simulate improving strategy over time
        success_rate = min(0.95, base_success_rate + (i / n_steps) * 0.6 + random.uniform(-0.05, 0.05))
        avg_reward = success_rate * 10 + random.uniform(-1, 1)
        
        data.append({
            'timestamp': base_timestamp + timedelta(hours=i),
            'success_rate': success_rate,
            'avg_reward': avg_reward,
            'total_actions': i * 10 + random.randint(1, 20)
        })
    
    return data

def demonstrate_learning_visualization():
    """Main function to demonstrate learning visualization."""
    print("Demonstrating Learning Visualization Tools")
    print("------------------------------------------")
    
    # Initialize the visualizer
    visualizer = LearningVisualizer(save_dir='examples/output/learning_viz')
    print(f"Visualizations will be saved to: {visualizer.save_dir}")
    
    # Generate sample data for multiple agents
    agent_ids = ['agent_1', 'agent_2', 'agent_3']
    
    print("\nGenerating sample learning data...")
    for agent_id in agent_ids:
        # Generate different learning patterns for different agents
        with_improvement = agent_id != 'agent_3'  # agent_3 doesn't improve
        n_steps = random.randint(50, 100)
        
        # Add learning data
        learning_data = generate_sample_learning_data(agent_id, n_steps, with_improvement)
        for step, data_point in enumerate(learning_data):
            visualizer.add_learning_data(agent_id, data_point)
        
        # Add pattern data
        pattern_data = generate_sample_pattern_data(agent_id, n_steps // 5)
        for data_point in pattern_data:
            visualizer.add_pattern_data(agent_id, data_point)
        
        # Add strategy data
        strategy_data = generate_sample_strategy_data(agent_id, n_steps // 3)
        for data_point in strategy_data:
            visualizer.add_strategy_data(agent_id, data_point)
            
        print(f"  Generated data for {agent_id}: {n_steps} learning steps, "
              f"{len(pattern_data)} pattern updates, {len(strategy_data)} strategy updates")
    
    # Generate and save visualizations
    print("\nGenerating visualizations...")
    
    # 1. Learning curves
    print("  Generating learning curves...")
    learning_fig = visualizer.plot_learning_curve(metric='rewards', save_plot=True)
    loss_fig = visualizer.plot_learning_curve(metric='losses', save_plot=True)
    
    # 2. Pattern recognition progress
    print("  Generating pattern recognition progress...")
    pattern_fig = visualizer.plot_pattern_recognition_progress(
        metrics=['total_patterns', 'avg_success_rate'], save_plot=True)
    
    # 3. Strategy adaptation effectiveness
    print("  Generating strategy adaptation charts...")
    strategy_fig = visualizer.plot_strategy_adaptation(save_plot=True)
    
    # 4. Pattern clusters for a specific agent
    print("  Generating pattern clusters...")
    clusters_fig = visualizer.visualize_pattern_clusters(agent_ids[0], save_plot=True)
    
    # 5. Cross-agent learning comparison
    print("  Generating cross-agent comparison...")
    comparison_fig = visualizer.visualize_cross_agent_learning(save_plot=True)
    
    # Display the figures (in a non-blocking way)
    print("\nDisplaying visualizations...")
    plt.ion()  # Turn on interactive mode
    plt.show()
    
    input("\nPress Enter to close the demonstration...")
    plt.close('all')

if __name__ == "__main__":
    demonstrate_learning_visualization() 