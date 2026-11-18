import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
import logging
from dataclasses import dataclass, field

from systems.benchmarking.benchmark_system import BenchmarkScenario

class BenchmarkScenarioLibrary:
    """A library of benchmark scenarios for testing different agent capabilities."""
    
    def __init__(self, custom_scenarios_path: Optional[str] = None):
        self.scenarios: Dict[str, BenchmarkScenario] = {}
        self.logger = logging.getLogger(__name__)
        self.custom_scenarios_path = Path(custom_scenarios_path) if custom_scenarios_path else None
        
        # Initialize with default scenarios
        self._initialize_combat_scenarios()
        self._initialize_survival_scenarios()
        self._initialize_resource_scenarios()
        self._initialize_team_scenarios()
        self._initialize_specialized_scenarios()
        
        # Load custom scenarios if available
        if self.custom_scenarios_path and self.custom_scenarios_path.exists():
            self._load_custom_scenarios()
    
    def _initialize_combat_scenarios(self) -> None:
        """Initialize combat-focused benchmark scenarios."""
        # Basic combat scenario
        self.scenarios["combat_novice"] = BenchmarkScenario(
            id="combat_novice",
            name="Novice Combat Challenge",
            description="Basic combat scenario with few, low-difficulty enemies",
            difficulty="easy",
            duration=180,  # 3 minutes
            environment_params={
                "map_size": 600,
                "obstacles": 5,
                "hazards": 0,
                "cover_objects": 3
            },
            enemy_params={
                "count": 5,
                "spawn_rate": 0.2,
                "difficulty": "easy",
                "types": ["basic"]
            },
            resource_params={
                "energy_count": 5,
                "health_count": 3,
                "special_count": 0
            },
            objective="combat",
            success_threshold=3,  # Kill at least 3 enemies
            tags=["combat", "basic", "beginner"]
        )
        
        # Intermediate combat scenario
        self.scenarios["combat_intermediate"] = BenchmarkScenario(
            id="combat_intermediate",
            name="Intermediate Combat Challenge",
            description="Combat scenario with medium difficulty enemies and varied types",
            difficulty="medium",
            duration=240,  # 4 minutes
            environment_params={
                "map_size": 700,
                "obstacles": 8,
                "hazards": 2,
                "cover_objects": 5
            },
            enemy_params={
                "count": 10,
                "spawn_rate": 0.3,
                "difficulty": "medium",
                "types": ["basic", "fast", "tank"]
            },
            resource_params={
                "energy_count": 8,
                "health_count": 5,
                "special_count": 2
            },
            objective="combat",
            success_threshold=6,  # Kill at least 6 enemies
            tags=["combat", "intermediate"]
        )
        
        # Advanced combat scenario
        self.scenarios["combat_advanced"] = BenchmarkScenario(
            id="combat_advanced",
            name="Advanced Combat Challenge",
            description="Difficult combat scenario with numerous, high-difficulty enemies",
            difficulty="hard",
            duration=300,  # 5 minutes
            environment_params={
                "map_size": 800,
                "obstacles": 12,
                "hazards": 4,
                "cover_objects": 8,
                "dynamic_obstacles": True
            },
            enemy_params={
                "count": 15,
                "spawn_rate": 0.4,
                "difficulty": "hard",
                "types": ["basic", "fast", "tank", "sniper"],
                "coordination": 0.7
            },
            resource_params={
                "energy_count": 10,
                "health_count": 7,
                "special_count": 3
            },
            objective="combat",
            success_threshold=8,  # Kill at least 8 enemies
            tags=["combat", "advanced"]
        )
        
        # Precision combat scenario
        self.scenarios["combat_precision"] = BenchmarkScenario(
            id="combat_precision",
            name="Precision Combat Test",
            description="Tests agent's accuracy and precision in combat",
            difficulty="medium",
            duration=240,  # 4 minutes
            environment_params={
                "map_size": 800,
                "obstacles": 15,
                "hazards": 0,
                "cover_objects": 12
            },
            enemy_params={
                "count": 8,
                "spawn_rate": 0.3,
                "difficulty": "medium",
                "types": ["basic", "fast"],
                "movement_pattern": "evasive"
            },
            resource_params={
                "energy_count": 5,
                "health_count": 3,
                "special_count": 0,
                "limited_ammo": True
            },
            objective="combat",
            success_threshold=0.7,  # 70% accuracy
            tags=["combat", "precision", "accuracy"]
        )
    
    def _initialize_survival_scenarios(self) -> None:
        """Initialize survival-focused benchmark scenarios."""
        # Basic survival scenario
        self.scenarios["survival_basic"] = BenchmarkScenario(
            id="survival_basic",
            name="Basic Survival Challenge",
            description="Simple survival scenario with minimal threats",
            difficulty="easy",
            duration=300,  # 5 minutes
            environment_params={
                "map_size": 600,
                "obstacles": 5,
                "hazards": 2,
                "cover_objects": 4
            },
            enemy_params={
                "count": 3,
                "spawn_rate": 0.1,
                "difficulty": "easy",
                "types": ["basic"]
            },
            resource_params={
                "energy_count": 8,
                "health_count": 5,
                "special_count": 0
            },
            objective="survival",
            success_threshold=270,  # Survive for at least 270 seconds
            tags=["survival", "basic"]
        )
        
        # Endurance survival scenario
        self.scenarios["survival_endurance"] = BenchmarkScenario(
            id="survival_endurance",
            name="Endurance Survival Challenge",
            description="Long-duration survival scenario with resource scarcity",
            difficulty="medium",
            duration=600,  # 10 minutes
            environment_params={
                "map_size": 800,
                "obstacles": 10,
                "hazards": 5,
                "cover_objects": 6,
                "shrinking_zone": True
            },
            enemy_params={
                "count": 6,
                "spawn_rate": 0.2,
                "difficulty": "medium",
                "types": ["basic", "fast"]
            },
            resource_params={
                "energy_count": 6,
                "health_count": 4,
                "special_count": 1,
                "respawn_rate": 0.3
            },
            objective="survival",
            success_threshold=480,  # Survive for at least 8 minutes
            tags=["survival", "endurance", "resources"]
        )
        
        # Hazard survival scenario
        self.scenarios["survival_hazards"] = BenchmarkScenario(
            id="survival_hazards",
            name="Hazardous Environment Survival",
            description="Survival scenario focused on environmental hazards",
            difficulty="hard",
            duration=360,  # 6 minutes
            environment_params={
                "map_size": 700,
                "obstacles": 8,
                "hazards": 12,
                "cover_objects": 5,
                "hazard_damage": 15,
                "hazard_movement": True
            },
            enemy_params={
                "count": 4,
                "spawn_rate": 0.15,
                "difficulty": "medium",
                "types": ["basic"]
            },
            resource_params={
                "energy_count": 10,
                "health_count": 8,
                "special_count": 2
            },
            objective="survival",
            success_threshold=300,  # Survive for at least 5 minutes
            tags=["survival", "hazards", "environment"]
        )
    
    def _initialize_resource_scenarios(self) -> None:
        """Initialize resource-focused benchmark scenarios."""
        # Resource collection scenario
        self.scenarios["resource_collection"] = BenchmarkScenario(
            id="resource_collection",
            name="Resource Collection Challenge",
            description="Tests agent's ability to efficiently collect resources",
            difficulty="easy",
            duration=240,  # 4 minutes
            environment_params={
                "map_size": 700,
                "obstacles": 10,
                "hazards": 0,
                "cover_objects": 0
            },
            enemy_params={
                "count": 2,
                "spawn_rate": 0.05,
                "difficulty": "easy",
                "types": ["basic"]
            },
            resource_params={
                "energy_count": 20,
                "health_count": 15,
                "special_count": 5,
                "distribution": "clustered"
            },
            objective="resource",
            success_threshold=20,  # Collect at least 20 resources
            tags=["resource", "collection", "efficiency"]
        )
        
        # Resource competition scenario
        self.scenarios["resource_competition"] = BenchmarkScenario(
            id="resource_competition",
            name="Resource Competition",
            description="Tests agent's ability to collect resources while competing with enemies",
            difficulty="medium",
            duration=300,  # 5 minutes
            environment_params={
                "map_size": 800,
                "obstacles": 12,
                "hazards": 2,
                "cover_objects": 4
            },
            enemy_params={
                "count": 8,
                "spawn_rate": 0.2,
                "difficulty": "medium",
                "types": ["basic", "fast"],
                "resource_seeking": True
            },
            resource_params={
                "energy_count": 15,
                "health_count": 10,
                "special_count": 5,
                "distribution": "random",
                "respawn_rate": 0.4
            },
            objective="resource",
            success_threshold=25,  # Collect at least 25 resources
            tags=["resource", "competition", "strategy"]
        )
        
        # Resource priority scenario
        self.scenarios["resource_priority"] = BenchmarkScenario(
            id="resource_priority",
            name="Resource Prioritization",
            description="Tests agent's ability to prioritize different resource types",
            difficulty="medium",
            duration=360,  # 6 minutes
            environment_params={
                "map_size": 900,
                "obstacles": 15,
                "hazards": 4,
                "cover_objects": 6
            },
            enemy_params={
                "count": 5,
                "spawn_rate": 0.15,
                "difficulty": "medium",
                "types": ["basic", "tank"]
            },
            resource_params={
                "energy_count": 8,
                "health_count": 8,
                "special_count": 8,
                "distribution": "strategic",
                "value_multipliers": {"energy": 1.0, "health": 2.0, "special": 3.0}
            },
            objective="resource",
            success_threshold=40,  # Collect 40 weighted points of resources
            tags=["resource", "priority", "decision-making"]
        )
    
    def _initialize_team_scenarios(self) -> None:
        """Initialize team-focused benchmark scenarios."""
        # Basic team coordination scenario
        self.scenarios["team_basic"] = BenchmarkScenario(
            id="team_basic",
            name="Basic Team Coordination",
            description="Tests agent's ability to coordinate with team members",
            difficulty="medium",
            duration=300,  # 5 minutes
            environment_params={
                "map_size": 800,
                "obstacles": 10,
                "hazards": 2,
                "cover_objects": 5
            },
            enemy_params={
                "count": 8,
                "spawn_rate": 0.2,
                "difficulty": "medium",
                "types": ["basic", "fast"],
                "team_size": 4
            },
            resource_params={
                "energy_count": 10,
                "health_count": 8,
                "special_count": 3,
                "distribution": "strategic"
            },
            objective="mixed",
            success_threshold=100,  # Combined team score of at least 100
            tags=["team", "coordination", "basic"]
        )
        
        # Role-based team scenario
        self.scenarios["team_roles"] = BenchmarkScenario(
            id="team_roles",
            name="Team Role Specialization",
            description="Tests agent's ability to fulfill specialized roles in a team",
            difficulty="hard",
            duration=420,  # 7 minutes
            environment_params={
                "map_size": 1000,
                "obstacles": 15,
                "hazards": 5,
                "cover_objects": 10,
                "zones": {"control": 3, "resource": 2}
            },
            enemy_params={
                "count": 12,
                "spawn_rate": 0.3,
                "difficulty": "hard",
                "types": ["basic", "fast", "tank", "sniper"],
                "team_size": 6,
                "coordination": 0.8
            },
            resource_params={
                "energy_count": 12,
                "health_count": 10,
                "special_count": 6,
                "distribution": "zone_based"
            },
            objective="mixed",
            success_threshold=150,  # Combined team score of at least 150
            tags=["team", "roles", "specialization", "advanced"]
        )
        
        # Team vs. team scenario
        self.scenarios["team_versus"] = BenchmarkScenario(
            id="team_versus",
            name="Team Versus Team",
            description="Tests agent's team performance against an enemy team",
            difficulty="hard",
            duration=480,  # 8 minutes
            environment_params={
                "map_size": 1200,
                "obstacles": 20,
                "hazards": 8,
                "cover_objects": 15,
                "zones": {"control": 5, "neutral": 2},
                "symmetrical": True
            },
            enemy_params={
                "count": 0,  # No random enemies, just the enemy team
                "spawn_rate": 0,
                "enemy_team": {
                    "size": 4,
                    "difficulty": "hard",
                    "coordination": 0.9,
                    "types": ["balanced"]
                }
            },
            resource_params={
                "energy_count": 15,
                "health_count": 12,
                "special_count": 8,
                "distribution": "contested"
            },
            objective="team_victory",
            success_threshold=1,  # Win the match
            tags=["team", "versus", "competitive", "advanced"]
        )
    
    def _initialize_specialized_scenarios(self) -> None:
        """Initialize specialized benchmark scenarios for specific skills."""
        # Evasion scenario
        self.scenarios["specialized_evasion"] = BenchmarkScenario(
            id="specialized_evasion",
            name="Evasion Challenge",
            description="Tests agent's ability to evade enemies and projectiles",
            difficulty="medium",
            duration=240,  # 4 minutes
            environment_params={
                "map_size": 600,
                "obstacles": 8,
                "hazards": 4,
                "cover_objects": 6,
                "open_center": True
            },
            enemy_params={
                "count": 10,
                "spawn_rate": 0.3,
                "difficulty": "medium",
                "types": ["fast", "sniper"],
                "projectile_speed": 1.5
            },
            resource_params={
                "energy_count": 5,
                "health_count": 3,
                "special_count": 0
            },
            objective="survival",
            success_threshold=180,  # Survive for at least 3 minutes
            tags=["specialized", "evasion", "movement"]
        )
        
        # Stealth scenario
        self.scenarios["specialized_stealth"] = BenchmarkScenario(
            id="specialized_stealth",
            name="Stealth Operation",
            description="Tests agent's ability to avoid detection and operate stealthily",
            difficulty="hard",
            duration=360,  # 6 minutes
            environment_params={
                "map_size": 1000,
                "obstacles": 25,
                "hazards": 5,
                "cover_objects": 20,
                "lighting": "dynamic",
                "vision_cones": True
            },
            enemy_params={
                "count": 12,
                "spawn_rate": 0.2,
                "difficulty": "hard",
                "types": ["patrol", "stationary"],
                "detection_range": 0.8,
                "alert_behavior": True
            },
            resource_params={
                "energy_count": 8,
                "health_count": 4,
                "special_count": 2,
                "distribution": "guarded"
            },
            objective="stealth",
            success_threshold=5,  # Complete 5 objectives without detection
            tags=["specialized", "stealth", "tactical"]
        )
        
        # Decision-making scenario
        self.scenarios["specialized_decision"] = BenchmarkScenario(
            id="specialized_decision",
            name="Tactical Decision Making",
            description="Tests agent's ability to make optimal decisions under pressure",
            difficulty="hard",
            duration=300,  # 5 minutes
            environment_params={
                "map_size": 800,
                "obstacles": 12,
                "hazards": 6,
                "cover_objects": 8,
                "dynamic_environment": True,
                "events": ["resource_surge", "enemy_wave", "safe_zone"]
            },
            enemy_params={
                "count": 8,
                "spawn_rate": 0.25,
                "difficulty": "varied",
                "types": ["basic", "fast", "tank", "sniper"],
                "spawn_pattern": "wave"
            },
            resource_params={
                "energy_count": 12,
                "health_count": 10,
                "special_count": 5,
                "distribution": "temporal",
                "decay": True
            },
            objective="score",
            success_threshold=200,  # Achieve a score of at least 200
            tags=["specialized", "decision-making", "optimization"]
        )
        
        # Learning scenario
        self.scenarios["specialized_learning"] = BenchmarkScenario(
            id="specialized_learning",
            name="Adaptive Learning Challenge",
            description="Tests agent's ability to learn and adapt to changing conditions",
            difficulty="hard",
            duration=600,  # 10 minutes
            environment_params={
                "map_size": 900,
                "obstacles": 15,
                "hazards": 8,
                "cover_objects": 10,
                "phases": 3,
                "phase_transitions": ["combat", "stealth", "resource"]
            },
            enemy_params={
                "count": 10,
                "spawn_rate": 0.2,
                "difficulty": "adaptive",
                "types": ["basic", "fast", "tank", "special"],
                "behavior_shifts": True
            },
            resource_params={
                "energy_count": 15,
                "health_count": 12,
                "special_count": 6,
                "distribution": "phase_based",
                "value_shifts": True
            },
            objective="adaptation",
            success_threshold=0.7,  # Adaptation score of at least 0.7
            tags=["specialized", "learning", "adaptation", "advanced"]
        )
    
    def _load_custom_scenarios(self) -> None:
        """Load custom scenarios from file."""
        try:
            with open(self.custom_scenarios_path, 'r') as f:
                scenario_data = json.load(f)
            
            for data in scenario_data:
                scenario = BenchmarkScenario.from_dict(data)
                self.scenarios[scenario.id] = scenario
            
            self.logger.info(f"Loaded {len(scenario_data)} custom scenarios from {self.custom_scenarios_path}")
        except Exception as e:
            self.logger.error(f"Failed to load custom scenarios: {str(e)}")
    
    def save_custom_scenario(self, scenario: BenchmarkScenario) -> bool:
        """
        Save a custom scenario to file.
        
        Args:
            scenario: The scenario to save
            
        Returns:
            True if the scenario was saved, False otherwise
        """
        if not self.custom_scenarios_path:
            self.logger.error("No custom scenarios path specified")
            return False
        
        try:
            # Create directory if it doesn't exist
            self.custom_scenarios_path.parent.mkdir(exist_ok=True, parents=True)
            
            # Load existing scenarios
            custom_scenarios = []
            if self.custom_scenarios_path.exists():
                with open(self.custom_scenarios_path, 'r') as f:
                    custom_scenarios = json.load(f)
            
            # Update or add scenario
            updated = False
            for i, s in enumerate(custom_scenarios):
                if s["id"] == scenario.id:
                    custom_scenarios[i] = scenario.to_dict()
                    updated = True
                    break
            
            if not updated:
                custom_scenarios.append(scenario.to_dict())
            
            # Save scenarios
            with open(self.custom_scenarios_path, 'w') as f:
                json.dump(custom_scenarios, f, indent=2)
            
            # Update in-memory scenarios
            self.scenarios[scenario.id] = scenario
            
            self.logger.info(f"Saved custom scenario: {scenario.id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save custom scenario: {str(e)}")
            return False
    
    def get_scenario(self, scenario_id: str) -> Optional[BenchmarkScenario]:
        """
        Get a scenario by ID.
        
        Args:
            scenario_id: The ID of the scenario
            
        Returns:
            The scenario, or None if not found
        """
        return self.scenarios.get(scenario_id)
    
    def get_scenarios_by_tags(self, tags: List[str], match_all: bool = False) -> List[BenchmarkScenario]:
        """
        Get scenarios that match the specified tags.
        
        Args:
            tags: Tags to match
            match_all: If True, match all tags; if False, match any tag
            
        Returns:
            A list of matching scenarios
        """
        if not tags:
            return []
        
        matching_scenarios = []
        
        for scenario in self.scenarios.values():
            if match_all:
                # Must match all tags
                if all(tag in scenario.tags for tag in tags):
                    matching_scenarios.append(scenario)
            else:
                # Match any tag
                if any(tag in scenario.tags for tag in tags):
                    matching_scenarios.append(scenario)
        
        return matching_scenarios
    
    def get_scenarios_by_difficulty(self, difficulty: str) -> List[BenchmarkScenario]:
        """
        Get scenarios of a specific difficulty.
        
        Args:
            difficulty: The difficulty level ("easy", "medium", "hard")
            
        Returns:
            A list of matching scenarios
        """
        return [s for s in self.scenarios.values() if s.difficulty == difficulty]
    
    def get_scenarios_by_objective(self, objective: str) -> List[BenchmarkScenario]:
        """
        Get scenarios with a specific objective.
        
        Args:
            objective: The objective type
            
        Returns:
            A list of matching scenarios
        """
        return [s for s in self.scenarios.values() if s.objective == objective]
    
    def get_all_scenarios(self) -> List[BenchmarkScenario]:
        """
        Get all available scenarios.
        
        Returns:
            A list of all scenarios
        """
        return list(self.scenarios.values())
    
    def create_scenario_progression(self, agent_type: str, 
                                  focus_area: str = "balanced") -> List[str]:
        """
        Create a progression of scenarios for an agent to train on.
        
        Args:
            agent_type: The type of agent
            focus_area: Focus area ("combat", "survival", "resource", "team", "balanced")
            
        Returns:
            A list of scenario IDs in order of difficulty
        """
        # Select scenarios based on focus area
        if focus_area == "combat":
            relevant_scenarios = self.get_scenarios_by_tags(["combat"])
        elif focus_area == "survival":
            relevant_scenarios = self.get_scenarios_by_tags(["survival"])
        elif focus_area == "resource":
            relevant_scenarios = self.get_scenarios_by_tags(["resource"])
        elif focus_area == "team":
            relevant_scenarios = self.get_scenarios_by_tags(["team"])
        else:  # balanced
            # Get a mix of scenario types
            combat = self.get_scenarios_by_tags(["combat"])[:2]
            survival = self.get_scenarios_by_tags(["survival"])[:2]
            resource = self.get_scenarios_by_tags(["resource"])[:1]
            team = self.get_scenarios_by_tags(["team"])[:1]
            relevant_scenarios = combat + survival + resource + team
        
        # Sort by difficulty
        difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
        sorted_scenarios = sorted(relevant_scenarios, 
                                 key=lambda s: difficulty_order.get(s.difficulty, 1))
        
        # Return IDs
        return [s.id for s in sorted_scenarios] 