# AI Battle Arena - Project Backlog

This backlog tracks tasks for understanding, refining, extending, and improving the AI Battle Arena codebase.

## Epics

*   **E01: Core System Understanding:** Gain a comprehensive understanding of the fundamental systems driving the simulation. [COMPLETED]
*   **E02: Visualization System Deep Dive:** Fully understand the architecture and implementation of the visualization components. [COMPLETED]
*   **E03: Learning & Evolution Analysis:** Analyze how agents learn and evolve within the environment. [COMPLETED]
*   **E04: Configuration Management:** Understand how the simulation is configured and how settings impact behavior. [COMPLETED]
*   **E05: Refactoring & Enhancement:** Identify areas for code improvement, refactoring, and potential feature additions. [STATUS: Ongoing]
*   **E06: Testing Improvement:** Increase unit and integration test coverage and resolve existing issues. [STATUS: TO DO]
*   **E07: Documentation Update:** Ensure documentation accurately reflects the current architecture and clarifies component roles. [STATUS: TO DO]

## Completed Refactoring & Enhancements

*   **[COMPLETED]** `[E05]` Refactor formation logic: Consolidate formation definitions and state within `FormationMovementSystem`. `TeamSystem` should query `FormationMovementSystem` for formation info and focus on team composition, roles, and abilities. (Previously T06)
*   **[COMPLETED]** `[E05]` Refine damage application to include modifiers (CombatSystem, TeamCombatIntegration, BattleRoyaleEnv).
*   **[COMPLETED]** `[E05]` Refactor `AgentSystem._execute_action` with private helper methods.
*   **[COMPLETED]** `[E05]` Refactor rendering logic: Moved agent drawing responsibility from `BattleRoyaleEnv.render` to `VisualizationIntegration.render`.

## M01 - Suppression and Morale Implementation [COMPLETED]
*   **[DONE]** `[M01.1 - HIGH]` Create `systems/morale/morale_suppression_system.py` with `MoraleSuppressionSystem` class structure. [FEATURE]
*   **[DONE]** `[M01.2 - HIGH]** Implement configuration loading (`_load_config`) and initialization (`_initialize`) in `MoraleSuppressionSystem`. Add necessary config values to `config/unified_config.py`. [FEATURE] [CONFIG]
*   **[DONE]** `[M01.3 - HIGH]** Implement agent registration (`register_agent`) and removal (`_remove_agent`, called from `_handle_entity_destroyed`) in `MoraleSuppressionSystem`. [FEATURE]
*   **[DONE]** `[M01.4 - HIGH]** Implement passive update logic (`_update`) for suppression decay and optional morale change in `MoraleSuppressionSystem`. [FEATURE]
*   **[DONE]** `[M01.5 - HIGH]** Implement `apply_morale_change` and `apply_suppression_increase` methods in `MoraleSuppressionSystem`, including personality modifier lookups. [FEATURE]
*   **[DONE]** `[M01.6 - HIGH]** Implement event handlers (`_handle_entity_created`, `_handle_entity_destroyed`, `_handle_agent_damaged`, `_handle_attack_miss`) in `MoraleSuppressionSystem`. [FEATURE]
*   **[DONE]** `[M01.7 - MEDIUM]** Define and implement placeholder event handlers for team actions (`_handle_team_action`) and potential heavy fire volume events in `MoraleSuppressionSystem`. [FEATURE]
*   **[DONE]** `[M01.8 - HIGH]** Modify `AgentSystem._get_agent_state` to query and append `morale` and `suppression` from `MoraleSuppressionSystem`. [INTEGRATION]
*   **[DONE]** `[M01.9 - HIGH]** Modify `AgentSystem._execute_action` to query suppression and apply penalties to movement speed and action timers/accuracy. [INTEGRATION]
*   **[DONE]** `[M01.10 - HIGH]** Modify `CombatSystem.calculate_final_damage` to query morale/suppression and apply modifiers. [INTEGRATION]
*   **[DONE]** `[M01.11 - HIGH]** Modify `BattleRoyaleEnv._resolve_hit` to query suppression and modify accuracy. [INTEGRATION]
*   **[DONE]** `[M01.12 - HIGH]** Modify `BattleRoyaleEnv._check_bullet_collisions` (or equivalent) to generate suppression events/calls for near misses. [INTEGRATION]
*   **[DONE]** `[M01.13 - MEDIUM]** Modify `PersonalitySystem` to define and provide effect values for morale/suppression sensitivity and decay. [INTEGRATION]
*   **[DONE]** `[M01.14 - MEDIUM]** Modify `TeamSystem` event handlers and relevant methods to trigger morale changes via `MoraleSuppressionSystem`. [INTEGRATION]
*   **[DONE]** `[M01.15 - MEDIUM]** Modify `FormationMovementSystem.get_formation_score` to incorporate agent morale queried from `MoraleSuppressionSystem`. [INTEGRATION]
*   **[DONE]** `[M01.16 - LOW]** Add `morale` and `suppression` attributes to `agents/agent.py`. [REFACTORING]
*   **[DONE]** `[M01.17 - HIGH]** Register `MoraleSuppressionSystem` in `main.py` with appropriate priority. [INTEGRATION]
*   **[DONE]** `[M01.18 - MEDIUM]** Implement unit tests for `MoraleSuppressionSystem`. [TESTING]

## Technical Debt / Next Up

*   **[DONE]** `[T09 - MEDIUM]** Improve agent movement collision response (Set agent-agent restitution to 0, use dynamic obstacle radii). [TECH DEBT]
*   **[BLOCKED]** `[T10 - MEDIUM]** Implement comprehensive unit tests for Combat Mechanics (beyond status effects and `calculate_final_damage`). **Reason:** Blocked by persistent TypeError in _resolve_hit tests (mocking issue?) and inability to locate _check_bullet_collisions source. Tests skipped in `test_combat_mechanics.py`. [TESTING]
*   **[TO DO]** `[T11 - MEDIUM]** Implement comprehensive unit tests for Learning System validation. [TESTING]
*   **[TO DO]** `[T12 - LOW]** Add integration tests for resource management. [TESTING]
*   **[TO DO]** `[T13 - LOW]** Add integration tests for evolution system. [TESTING]

## Completed Analysis & Minor Tasks

*   **[COMPLETED]** Analyze `learning_visualizer.py` role and implementation.
*   **[COMPLETED]** Analyze `learning_ui_component.py` structure and integration.
*   **[COMPLETED]** Analyze `main.py` for application structure and system orchestration.
*   **[COMPLETED]** Analyze `visualization_integration.py` integration.
*   **[COMPLETED]** Analyze `system_manager.py` role.
*   **[COMPLETED]** Analyze `config/unified_config.py` structure.
*   **[COMPLETED]** Analyze `systems/environment/environment.py`.
*   **[COMPLETED]** Analyze `systems/physics/collision_system.py`.
*   **[COMPLETED]** Analyze `systems/combat/combat_system.py`.
*   **[COMPLETED]** Analyze `learning_integration.py`.
*   **[COMPLETED]** Analyze `systems/agents/agent_system.py`.
*   **[COMPLETED]** Analyze `systems/agents/team_system.py`.
*   **[COMPLETED]** Analyze core agent classes (`systems/agents/base_agent.py`).
*   **[COMPLETED]** Analyze `systems/visualization/visualization_system.py`.
*   **[COMPLETED]** Analyze `systems/visualization/rendering.py`.
*   **[COMPLETED]** Implement unit tests for `CombatSystem` status effect methods (`apply_status_effect`, `update_status_effects`, `_get_status_effect`). (Previously T07 part 2)
*   **[COMPLETED]** Implement core attack resolution logic design (hit/miss determination based on accuracy, range, LoS) likely within `environment.py` (`_check_bullet_collisions`). (Previously T08)
*   **[COMPLETED]** Design unit tests for core attack resolution logic. (Previously T07 part 1)
*   **[COMPLETED]** Implement comprehensive unit tests for `CombatSystem.calculate_final_damage`. (Previously T05)
*   **[COMPLETED]** Implement peer-to-peer learning logic in `systems/learning/learning_integration.py` (`_share_learning_with_peers`). (Previously T01)
*   **[COMPLETED]** Investigate `pass` statement in `systems/agents/team_system.py` (`_on_agent_action`). (Previously T04)

## Icebox / Future Ideas

*   **[F01]** Deep dive analysis of `systems/agents/agent_actions.py`.
*   **[F02]** Analyze Physics Integration (`systems/physics/collision_system.py`, `systems/agents/agent_system.py`) - Verify agent-obstacle resolution. (Previously P01)
*   **[F03]** Dynamic personality evolution based on experiences.
*   **[F04]** Social learning between agents with similar personalities.
*   **[F05]** Emotional states affecting decision-making.
*   **[F06]** Team-based combat tactics.
*   **[F07]** Role-specific abilities in combat.
*   **[F08]** Formation-based attack and defense bonuses.

## Current Sprint / Near-Term Focus

*   **Cleanup & Consolidation (Part of E05):**
    *   `[T14 - HIGH]** Identify and remove/archive deprecated/redundant files (e.g., `config.py` vs `unified_config.py`, `performance_monitor.py` vs `performance.py`, `systems/visual_feedback.py` vs `systems/visualization/`, `backup_...` dir). **Status: RECOMMENDED FOR REMOVAL/ARCHIVAL** [REFACTORING]
    *   `[T15 - HIGH]** Ensure all systems consistently use `config/unified_config.py`. **Note:** `main.py` currently imports the old `SystemMonitor`. [REFACTORING]
    *   `[T16 - MEDIUM]** Define the primary entry point (`enhanced_game_loop.py` seems better) and refactor/remove others (`main.py`). Rename chosen file to `main.py`. **Status: RECOMMEND CONSOLIDATION/REMOVAL** [REFACTORING]
    *   `[T17 - MEDIUM]** Consolidate combat mechanics logic into `CombatSystem` and potentially helper classes. Remove redundant files (e.g., `backup_.../combat/`). [REFACTORING]
    *   `[T18 - MEDIUM]** Clarify/consolidate visualization components (`systems/visual_feedback.py` vs `systems/visualization/`). **Status: RECOMMEND REMOVING visual_feedback.py** [REFACTORING]
    *   `[T19 - LOW]** Add `requirements.txt` for dependency management. [SETUP]
    *   `[T30 - LOW]** Ensure necessary battle visual effects (damage numbers, screen shake, etc.) from `visual_feedback.py` are present in `VisualizationSystem`/`Renderer`. [VISUALIZATION] [REFACTORING]

*   **Core System Refactoring (Part of E05 - Confirmed SRP Approach):**
    *   `[T20 - HIGH]` **EntityManager Implementation:** [REFACTORING]
        *   `[T20.1]` Create `systems/core/entity_manager.py` with `EntityManager` class inheriting `BaseSystem`.
        *   `[T20.2]` Implement core entity storage (e.g., dictionary).
        *   `[T20.3]` Implement `register_entity`, `unregister_entity`, `get_entity` methods.
        *   `[T20.4]` Add spatial partitioning (e.g., internal QuadTree) for efficient querying.
        *   `[T20.5]` Implement `get_entities_in_range`, `get_all_entities_of_type` using spatial partitioning.
        *   `[T20.6]` Implement `update_entity_position` (updating internal state and spatial partition).
        *   `[T20.7]` Register `EntityManager` with `SystemManager` (high priority).
        *   `[T20.8]` **Migration:** Modify existing systems (`CollisionSystem`, `AgentSystem`, `BattleRoyaleEnv`, `Rendering`, etc.) to register/unregister entities via `EntityManager`.
        *   `[T20.9]` **Migration:** Modify systems needing entity data to query `EntityManager` instead of holding local lists.
        *   `[T20.10]` Add unit tests for `EntityManager`.
    *   `[T21 - HIGH]` **CollisionSystem Refactoring:** [REFACTORING] [PHYSICS]
        *   `[T21.1]` Modify `CollisionSystem` to query `EntityManager` for entity positions/bounds.
        *   `[T21.2]` Implement collision checks for all relevant pairs (agent-agent, agent-obstacle, bullet-agent, bullet-obstacle, agent-pickup).
        *   `[T21.3]` Remove direct collision *resolution* logic (damage, physics changes).
        *   `[T21.4]` Implement emission of detailed `ENTITY_COLLISION` events (and potentially others like `AGENT_AGENT_COLLISION`) via `SystemManager` on collision detection.
        *   `[T21.5]` Remove collision detection/resolution logic from `BattleRoyaleEnv`.
        *   `[T21.6]` **Migration:** Adapt systems (`CombatSystem`, `AgentSystem`, `MoraleSuppressionSystem`?) to listen for collision events and apply effects/resolve physics.
        *   `[T21.7]` Update/add unit tests for `CollisionSystem` event emission.
    *   `[T22 - HIGH]` **ActionExecutor Implementation:** [REFACTORING]
        *   `[T22.1]` Create `systems/agents/action_executor.py` with `ActionExecutor` class inheriting `BaseSystem`.
        *   `[T22.2]` Implement methods for specific actions (`execute_move`, `execute_rotate`, `execute_shoot`, `execute_resource_interaction`, etc.).
        *   `[T22.3]` Action methods query necessary systems (`EntityManager`, `TerrainSystem`, `ResourceManager`, `CombatSystem` for costs) and apply physics/state changes (e.g., update position via `EntityManager`, request resource extraction, create bullet via `EntityManager`).
        *   `[T22.4]` Implement event emissions for action results (`BULLET_FIRED`, `RESOURCE_COLLECTED`, etc.).
        *   `[T22.5]` Register `ActionExecutor` with `SystemManager`.
        *   `[T22.6]` **Migration:** Refactor `AgentSystem._execute_action` to call appropriate methods on `ActionExecutor`.
        *   `[T22.7]` Add unit tests for `ActionExecutor`.
    *   `[T23 - HIGH]** StateBuilder Implementation:** [REFACTORING]
        *   `[T23.1]` Create `systems/agents/state_builder.py` with `StateBuilder` class (may not need `BaseSystem`).
        *   `[T23.2]` Implement `build_state_vector(agent_id)` method.
        *   `[T23.3]` Method queries required systems (`EntityManager`, `MoraleSuppressionSystem`, `TeamSystem`, `HazardCoverSystem`, etc.) via `SystemManager` or direct reference.
        *   `[T23.4]` Assemble and return the state vector as a NumPy array.
        *   `[T23.5]` Register `StateBuilder` with `SystemManager` if it needs access via `get_system`.
        *   `[T23.6]` **Migration:** Refactor `AgentSystem._get_agent_state` to use `StateBuilder`.
        *   `[T23.7]` Add unit tests for `StateBuilder`.
    *   `[T31 - MEDIUM]` **BattleRoyaleEnv Refactoring:** [REFACTORING]
        *   `[T31.1]` Remove entity management logic (use `EntityManager`).
        *   `[T31.2]` Remove collision detection/resolution logic (handled by `CollisionSystem`).
        *   `[T31.3]` Remove detailed environment update logic (delegate to specific systems like `TimeSystem`, `WeatherSystem`).
        *   `[T31.4]` Refocus `update` method on safe zone logic and coordinating calls to other env systems.
        *   `[T31.5]` Remove direct rendering calls (handled by `VisualizationIntegration`).
        *   `[T31.6]` Update unit tests for `BattleRoyaleEnv`.
    *   `[T32 - MEDIUM]` **Ensure Dedicated Env Managers:** [REFACTORING]
        *   `[T32.1]` Verify `ResourceManager`, `HazardCoverSystem`, `TimeSystem`, `WeatherSystem` fully handle their domains.
        *   `[T32.2]` Migrate any remaining detailed logic for these areas from `BattleRoyaleEnv`.
        *   `[T32.3]` Create separate `PickupSpawner` if pickup logic in `BattleRoyaleEnv` is complex.

## Completed Analysis & Minor Tasks

*   **[COMPLETED]** Analyze `learning_visualizer.py` role and implementation.
*   **[COMPLETED]** Analyze `learning_ui_component.py` structure and integration.
*   **[COMPLETED]** Analyze `main.py` for application structure and system orchestration.
*   **[COMPLETED]** Analyze `visualization_integration.py` integration.
*   **[COMPLETED]** Analyze `system_manager.py` role.
*   **[COMPLETED]** Analyze `config/unified_config.py` structure.
*   **[COMPLETED]** Analyze `systems/environment/environment.py`.
*   **[COMPLETED]** Analyze `systems/physics/collision_system.py`.
*   **[COMPLETED]** Analyze `systems/combat/combat_system.py`.
*   **[COMPLETED]** Analyze `learning_integration.py`.
*   **[COMPLETED]** Analyze `systems/agents/agent_system.py`.
*   **[COMPLETED]** Analyze `systems/agents/team_system.py`.
*   **[COMPLETED]** Analyze core agent classes (`systems/agents/base_agent.py`).
*   **[COMPLETED]** Analyze `systems/visualization/visualization_system.py`.
*   **[COMPLETED]** Analyze `systems/visualization/rendering.py`.
*   **[COMPLETED]** Implement unit tests for `CombatSystem` status effect methods (`apply_status_effect`, `update_status_effects`, `_get_status_effect`). (Previously T07 part 2)
*   **[COMPLETED]** Implement core attack resolution logic design (hit/miss determination based on accuracy, range, LoS) likely within `environment.py` (`_check_bullet_collisions`). (Previously T08)
*   **[COMPLETED]** Design unit tests for core attack resolution logic. (Previously T07 part 1)
*   **[COMPLETED]** Implement comprehensive unit tests for `CombatSystem.calculate_final_damage`. (Previously T05)
*   **[COMPLETED]** Implement peer-to-peer learning logic in `systems/learning/learning_integration.py` (`_share_learning_with_peers`). (Previously T01)
*   **[COMPLETED]** Investigate `pass` statement in `systems/agents/team_system.py` (`_on_agent_action`). (Previously T04)

## Sprint 1: Core Refactoring

**Goal:** Refactor core systems for better modularity, event-driven architecture, and QuadTree integration.

| ID     | Task                                                            | Status      | Assignee | Notes                                                                 |
| :----- | :-------------------------------------------------------------- | :---------- | :------- | :-------------------------------------------------------------------- |
| **T1** | Consolidate entry point                                         | Done        | Agent    | Merged `run_simulation.py` into `main.py`                             |
| **T2** | Implement `EntityManager` with QuadTree                         | Done        | Agent    | Handles entity storage and spatial indexing.                          |
| **T3** | Register `EntityManager` in `main.py`                           | Done        | Agent    | `EntityManager` initialized and passed to systems.                    |
| **T4** | Create `StateBuilder` skeleton                                  | Done        | Agent    | Basic class structure created.                                        |
| **T5** | Create `ActionExecutor` skeleton                                | Done        | Agent    | Basic class structure created.                                        |
| **T6** | Refactor `CollisionSystem` Interface                            | Done        | Agent    | Changed to use `EntityManager`, emit events (`COLLISION_DETECTED`). |
| **T7** | Remove Collision Logic from `BattleRoyaleEnv`                 | Done        | Agent    | Removed internal QuadTree, collision checks, `_resolve_hit`.      |
| **T8** | Implement `CollisionSystem` Logic                               | Done        | Agent    | Process `EntityManager`, detect collisions, emit `COLLISION_DETECTED`.  |
| **T9** | Implement `CombatSystem`                                        | To Do       |          | Handle combat events (`ATTACK_COMMAND`, `BULLET_HIT`, `BULLET_MISS`). |
| **T10**| Implement `MovementSystem`                                      | To Do       |          | Handle `MOVE_COMMAND`, update entity positions via `EntityManager`.     |
| **T11**| Implement `PickupSystem`                                        | Done        | Agent    | Handle `PICKUP_ACQUIRED`, `PICKUP_COMMAND`.                           |
| **T12**| Integrate Systems with Event Bus in `main.py`                   | Done        | Agent    | Connect systems via `EventManager`.                                   |
| **T13**| Implement `StateBuilder` Logic                                  | Done        | Agent    | Aggregate state from `EntityManager` and `BattleRoyaleEnv`.           |
| **T14**| Implement `ActionExecutor` Logic                                | Done        | Agent    | Translate agent actions into system events.                           |
| **T15**| Refactor Agent Action Selection                                 | To Do       |          | Agents use `StateBuilder` output, generate actions for `ActionExecutor`.|
| **T16**| Testing: Collision Detection                                    | To Do       |          | Verify `CollisionSystem` correctly identifies collisions.             |
| **T17**| Testing: Combat Resolution                                      | To Do       |          | Verify `CombatSystem` handles hits/misses correctly.                  |
| **T18**| Testing: Movement                                               | To Do       |          | Verify `MovementSystem` updates positions correctly.                  |
| **T19**| Testing: End-to-End Simulation Loop                             | To Do       |          | Ensure the main loop runs with refactored systems.                  |
| **T20**| Documentation Update                                            | To Do       |          | Update README and code comments for new architecture.               |

---
*Derived Tasks from Initial Analysis (Integrated into T1-T20 where applicable):*
- *T21.1: EntityManager ✅ (Part of T2)*
- *T21.2: Entity Registration ✅ (Part of T3)*
- *T21.3: CollisionSystem Refactor ✅ Interface (Part of T6), Logic (T8)*
- *T21.4: CombatSystem (T9)*
- *T21.5: Remove Env Collision Logic ✅ (Part of T7)*
- *T21.6: StateBuilder (T4, T13)*
- *T21.7: ActionExecutor (T5, T14)*
- *T21.8: EventManager Integration (T12)*
---