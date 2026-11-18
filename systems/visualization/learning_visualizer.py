"""
Learning visualization tools for monitoring AI agent learning progress.

This module provides visualization utilities specifically designed for learning metrics,
including experience memory analytics, pattern recognition, and strategy adaptation progress.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from typing import Dict, List, Tuple, Any, Optional
import os
from datetime import datetime
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg

class LearningVisualizer:
    """
    Visualizes learning-related metrics and progress for AI agents.
    
    This class provides methods for visualizing various aspects of agent learning,
    including learning curves, pattern recognition statistics, and strategy adaptation
    effectiveness over time.
    """
    
    def __init__(self, save_dir: str = 'analytics/learning'):
        """
        Initialize the learning visualizer.
        
        Args:
            save_dir: Directory to save generated visualizations
        """
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        
        # Store historical data for visualizations
        self.agent_learning_history = {}
        self.pattern_recognition_history = {}
        self.strategy_adaptation_history = {}
        
    def add_learning_data(self, agent_id: str, data: Dict[str, Any], timestamp: Optional[datetime] = None):
        """
        Add learning data for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            data: Dictionary containing learning metrics like rewards, losses, etc.
            timestamp: Time of data recording (uses current time if None)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        if agent_id not in self.agent_learning_history:
            self.agent_learning_history[agent_id] = []
            
        data_point = {
            'timestamp': timestamp,
            **data
        }
        self.agent_learning_history[agent_id].append(data_point)
    
    def add_pattern_data(self, agent_id: str, pattern_stats: Dict[str, Any], timestamp: Optional[datetime] = None):
        """
        Add pattern recognition statistics for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            pattern_stats: Dictionary containing pattern recognition metrics
            timestamp: Time of data recording (uses current time if None)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        if agent_id not in self.pattern_recognition_history:
            self.pattern_recognition_history[agent_id] = []
            
        data_point = {
            'timestamp': timestamp,
            **pattern_stats
        }
        self.pattern_recognition_history[agent_id].append(data_point)
    
    def add_strategy_data(self, agent_id: str, strategy_data: Dict[str, Any], timestamp: Optional[datetime] = None):
        """
        Add strategy adaptation data for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            strategy_data: Dictionary containing strategy adaptation metrics
            timestamp: Time of data recording (uses current time if None)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        if agent_id not in self.strategy_adaptation_history:
            self.strategy_adaptation_history[agent_id] = []
            
        data_point = {
            'timestamp': timestamp,
            **strategy_data
        }
        self.strategy_adaptation_history[agent_id].append(data_point)
    
    def plot_learning_curve(self, agent_ids: List[str] = None, metric: str = 'rewards', 
                           window_size: int = 10, figsize: Tuple[int, int] = (10, 6),
                           save_plot: bool = False) -> Figure:
        """
        Plot learning curves for specified agents.
        
        Args:
            agent_ids: List of agent IDs to include (all agents if None)
            metric: Which learning metric to plot ('rewards', 'losses', etc.)
            window_size: Size of the moving average window
            figsize: Figure dimensions (width, height)
            save_plot: Whether to save the plot to disk
            
        Returns:
            Matplotlib Figure object
        """
        if agent_ids is None:
            agent_ids = list(self.agent_learning_history.keys())
            
        fig, ax = plt.subplots(figsize=figsize)
        
        for agent_id in agent_ids:
            if agent_id not in self.agent_learning_history:
                continue
                
            # Extract data for the specified metric
            data_points = self.agent_learning_history[agent_id]
            data_values = [point.get(metric, 0) for point in data_points]
            
            # Calculate moving average if enough data points
            if len(data_values) >= window_size:
                smoothed_values = np.convolve(data_values, 
                                             np.ones(window_size)/window_size, 
                                             mode='valid')
                x_values = list(range(len(smoothed_values)))
                
                # Plot the learning curve
                ax.plot(x_values, smoothed_values, label=f"Agent {agent_id}")
                
                # Plot the raw data with lower alpha
                ax.plot(data_values, alpha=0.3, color=ax.lines[-1].get_color())
                
            else:
                # Plot raw data if not enough for smoothing
                ax.plot(data_values, label=f"Agent {agent_id}")
        
        # Add labels and legend
        ax.set_xlabel('Training Steps')
        ax.set_ylabel(f'{metric.capitalize()}')
        ax.set_title(f'Learning Curve: {metric.capitalize()}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Save the plot if requested
        if save_plot:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(self.save_dir, f'learning_curve_{metric}_{timestamp}.png')
            fig.savefig(filename, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_pattern_recognition_progress(self, agent_ids: List[str] = None, 
                                         metrics: List[str] = None,
                                         figsize: Tuple[int, int] = (12, 8),
                                         save_plot: bool = False) -> Figure:
        """
        Plot pattern recognition metrics over time.
        
        Args:
            agent_ids: List of agent IDs to include (all agents if None)
            metrics: Which pattern recognition metrics to plot
            figsize: Figure dimensions (width, height)
            save_plot: Whether to save the plot to disk
            
        Returns:
            Matplotlib Figure object
        """
        if agent_ids is None:
            agent_ids = list(self.pattern_recognition_history.keys())
            
        if metrics is None:
            metrics = ['total_patterns', 'avg_success_rate', 'most_successful_pattern_rate']
            
        fig, axes = plt.subplots(len(metrics), 1, figsize=figsize, sharex=True)
        if len(metrics) == 1:
            axes = [axes]
            
        for i, metric in enumerate(metrics):
            ax = axes[i]
            
            for agent_id in agent_ids:
                if agent_id not in self.pattern_recognition_history:
                    continue
                    
                # Extract data for the specified metric
                data_points = self.pattern_recognition_history[agent_id]
                
                # Convert to dataframe for easier manipulation
                df = pd.DataFrame(data_points)
                if 'timestamp' in df.columns and metric in df.columns:
                    ax.plot(df['timestamp'], df[metric], label=f"Agent {agent_id}")
            
            # Add labels
            ax.set_ylabel(metric.replace('_', ' ').title())
            ax.grid(True, alpha=0.3)
            
            if i == 0:
                ax.set_title('Pattern Recognition Progress')
            if i == len(metrics) - 1:
                ax.set_xlabel('Time')
                
            ax.legend()
        
        fig.tight_layout()
        
        # Save the plot if requested
        if save_plot:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(self.save_dir, f'pattern_recognition_{timestamp}.png')
            fig.savefig(filename, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_strategy_adaptation(self, agent_ids: List[str] = None,
                               figsize: Tuple[int, int] = (10, 8),
                               save_plot: bool = False) -> Figure:
        """
        Plot strategy adaptation effectiveness over time.
        
        Args:
            agent_ids: List of agent IDs to include (all agents if None)
            figsize: Figure dimensions (width, height)
            save_plot: Whether to save the plot to disk
            
        Returns:
            Matplotlib Figure object
        """
        if agent_ids is None:
            agent_ids = list(self.strategy_adaptation_history.keys())
            
        fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)
        
        # Plot success rate
        ax1 = axes[0]
        for agent_id in agent_ids:
            if agent_id not in self.strategy_adaptation_history:
                continue
                
            # Extract data
            data_points = self.strategy_adaptation_history[agent_id]
            df = pd.DataFrame(data_points)
            
            if 'timestamp' in df.columns and 'success_rate' in df.columns:
                ax1.plot(df['timestamp'], df['success_rate'], label=f"Agent {agent_id}")
        
        ax1.set_ylabel('Success Rate')
        ax1.set_title('Strategy Adaptation Effectiveness')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Plot average reward
        ax2 = axes[1]
        for agent_id in agent_ids:
            if agent_id not in self.strategy_adaptation_history:
                continue
                
            # Extract data
            data_points = self.strategy_adaptation_history[agent_id]
            df = pd.DataFrame(data_points)
            
            if 'timestamp' in df.columns and 'avg_reward' in df.columns:
                ax2.plot(df['timestamp'], df['avg_reward'], label=f"Agent {agent_id}")
        
        ax2.set_ylabel('Average Reward')
        ax2.set_xlabel('Time')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        fig.tight_layout()
        
        # Save the plot if requested
        if save_plot:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(self.save_dir, f'strategy_adaptation_{timestamp}.png')
            fig.savefig(filename, dpi=300, bbox_inches='tight')
        
        return fig
    
    def visualize_pattern_clusters(self, agent_id: str, figsize: Tuple[int, int] = (10, 8),
                                 save_plot: bool = False) -> Figure:
        """
        Visualize discovered pattern clusters for an agent.
        
        Args:
            agent_id: Agent ID to visualize patterns for
            figsize: Figure dimensions (width, height)
            save_plot: Whether to save the plot to disk
            
        Returns:
            Matplotlib Figure object
        """
        if agent_id not in self.pattern_recognition_history:
            raise ValueError(f"No pattern data available for agent {agent_id}")
            
        # Get the most recent pattern data
        pattern_data = self.pattern_recognition_history[agent_id][-1]
        
        success_patterns = pattern_data.get('success_patterns', [])
        failure_patterns = pattern_data.get('failure_patterns', [])
        
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        
        # Plot success patterns
        ax1 = axes[0]
        if success_patterns:
            # Implementation depends on the structure of patterns
            # Placeholder for demonstration
            pattern_counts = list(range(len(success_patterns)))
            pattern_values = [1.0] * len(success_patterns)  # Example values
            ax1.bar(pattern_counts, pattern_values, color='green', alpha=0.7)
            ax1.set_title('Success Patterns')
            ax1.set_xlabel('Pattern ID')
            ax1.set_ylabel('Success Rate')
        else:
            ax1.text(0.5, 0.5, "No success patterns", 
                   ha='center', va='center', transform=ax1.transAxes)
            
        # Plot failure patterns
        ax2 = axes[1]
        if failure_patterns:
            # Implementation depends on the structure of patterns
            # Placeholder for demonstration
            pattern_counts = list(range(len(failure_patterns)))
            pattern_values = [1.0] * len(failure_patterns)  # Example values
            ax2.bar(pattern_counts, pattern_values, color='red', alpha=0.7)
            ax2.set_title('Failure Patterns')
            ax2.set_xlabel('Pattern ID')
            ax2.set_ylabel('Failure Rate')
        else:
            ax2.text(0.5, 0.5, "No failure patterns", 
                   ha='center', va='center', transform=ax2.transAxes)
        
        fig.suptitle(f'Pattern Clusters for Agent {agent_id}')
        fig.tight_layout()
        
        # Save the plot if requested
        if save_plot:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(self.save_dir, f'pattern_clusters_{agent_id}_{timestamp}.png')
            fig.savefig(filename, dpi=300, bbox_inches='tight')
        
        return fig
    
    def visualize_cross_agent_learning(self, metric: str = 'rewards',
                                     figsize: Tuple[int, int] = (12, 10),
                                     save_plot: bool = False) -> Figure:
        """
        Compare learning progress across multiple agents.
        
        Args:
            metric: Which learning metric to compare
            figsize: Figure dimensions (width, height)
            save_plot: Whether to save the plot to disk
            
        Returns:
            Matplotlib Figure object
        """
        # Collect data for each agent
        agent_ids = list(self.agent_learning_history.keys())
        agent_data = {}
        
        for agent_id in agent_ids:
            data_points = self.agent_learning_history[agent_id]
            values = [point.get(metric, 0) for point in data_points]
            agent_data[agent_id] = values
            
        # Create the plot
        fig, ax = plt.subplots(figsize=figsize)
        
        # Calculate box plot data
        box_data = [agent_data[agent_id] for agent_id in agent_ids if agent_data[agent_id]]
        
        if box_data:
            ax.boxplot(box_data, labels=agent_ids, showfliers=True)
            
            # Add a scatter plot for individual data points
            for i, agent_id in enumerate(agent_ids):
                if agent_id in agent_data and agent_data[agent_id]:
                    y = agent_data[agent_id]
                    x = [i + 1] * len(y)
                    ax.scatter(x, y, alpha=0.5, s=20)
            
            ax.set_title(f'Cross-Agent Learning Comparison: {metric.capitalize()}')
            ax.set_xlabel('Agent')
            ax.set_ylabel(metric.capitalize())
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, "No data available", 
                  ha='center', va='center', transform=ax.transAxes)
        
        # Save the plot if requested
        if save_plot:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(self.save_dir, f'cross_agent_{metric}_{timestamp}.png')
            fig.savefig(filename, dpi=300, bbox_inches='tight')
        
        return fig
    
    def render_to_surface(self, figure: Figure, width: int, height: int):
        """
        Render a matplotlib figure to a surface for display in a game or UI.
        
        Args:
            figure: Matplotlib Figure to render
            width: Desired width of the surface
            height: Desired height of the surface
            
        Returns:
            Surface object (actual implementation depends on the rendering system)
        """
        # This implementation would depend on the rendering system
        # For now, we'll return the raw data that could be used to create a surface
        
        # Render the figure to a canvas
        canvas = FigureCanvasAgg(figure)
        canvas.draw()
        
        # Get the RGBA buffer
        w, h = int(figure.get_figwidth() * figure.get_dpi()), int(figure.get_figheight() * figure.get_dpi())
        buf = np.frombuffer(canvas.tostring_argb(), dtype=np.uint8)
        buf.shape = (h, w, 4)
        
        # Resize if needed
        if (w, h) != (width, height):
            # This would need to be implemented with the appropriate image library
            # (e.g., OpenCV, PIL, or pygame.transform)
            pass
        
        return buf  # Would be converted to the appropriate surface type 