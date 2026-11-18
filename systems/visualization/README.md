# Visualization System

## Overview

The Visualization System provides tools for visualizing game state, agent behavior, and learning progress in the AI Battle Arena. It includes components for rendering the game world as well as specialized tools for visualizing learning metrics and analytics.

## Components

### VisualizationSystem

The core visualization system responsible for rendering the game state, including agents, teams, resources, and combat interactions. It handles camera positioning, visual effects, and rendering of the game world.

### LearningVisualizer

A specialized visualization component that generates graphs and visualizations for agent learning metrics, including:

- Learning curves (rewards, losses)
- Pattern recognition progress
- Strategy adaptation effectiveness
- Pattern clusters
- Cross-agent learning comparisons

This class uses Matplotlib to generate visualizations and provides methods to save them to disk or render them to surfaces for display in-game.

### LearningUIComponent

An interactive UI component that renders learning visualizations directly within the game UI. It provides a movable, resizable panel with tabs for different visualization types and buttons for controlling the display. Features include:

- Multiple visualization types (learning curves, pattern progress, etc.)
- Movable panel (drag from header)
- Minimizable interface
- Agent selection for detailed metrics
- Automatic updates at regular intervals

### VisualizationIntegration

The system that integrates the visualization components with the game loop. It manages:

- Component lifecycle (creation, updates, rendering, destruction)
- Event handling for UI components
- Integration with the SystemManager
- Performance-aware visualization (auto-hiding during intensive gameplay)
- Keyboard shortcuts for toggling visualization (F3, F4)

## Usage

### Basic Integration

The visualization system is automatically integrated with the game through the `main.py` file. It is registered with the SystemManager:

```python
# Initialize visualization integration
visualization_integration = VisualizationIntegration()
system_manager.register_system("visualization_integration", visualization_integration, priority=80)
```

### Event Handling

Events are passed to the visualization components in the main game loop:

```python
# Handle events
for event in pygame.event.get():
    if event.type == pygame.QUIT:
        running = False
    else:
        # Pass event to visualization system
        visualization_integration.handle_event(event)
```

### Rendering

Visualization components are rendered after all systems are updated:

```python
# Update all systems
system_manager.update(delta_time)

# Render visualization components
visualization_integration.render(screen)
```

## Controls

- **F3**: Toggle all visualizations on/off
- **F4**: Toggle learning visualization panel
- **Drag**: Move visualization panels by dragging the header
- **X button**: Close a visualization panel
- **_ button**: Minimize a visualization panel
- **Tab buttons**: Switch between different visualization types

## Customizing Visualizations

Custom visualizations can be added by:

1. Creating a new class that implements the same interface as `LearningUIComponent`
2. Adding an instance to the `VisualizationIntegration` system:

```python
custom_component = CustomVisualizationComponent()
visualization_integration.add_component(custom_component)
```

## Technical Details

- The system uses Matplotlib for generating visualizations
- Pygame is used for rendering UI components
- The system is designed to be performance-aware, automatically disabling during intensive gameplay to maintain frame rate
- Visualizations update on a customizable interval (defaults to 2 seconds) to minimize performance impact 