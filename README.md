# Agent Eval Arena

A simulation testbed for **multi-agent behaviour and its evaluation** — agents compete, cooperate, form teams, build
trust, share resources and learn, while a benchmarking subsystem measures and compares what they actually do.

This is a **simulation testbed, not an LLM application**: the agents are simulated decision-makers (behaviour learning,
experience memory, genetic-algorithm adaption, personality and morale models), not language-model agents. It is here
because the hard parts transfer: agent lifecycle, coordination, and a measurement harness that makes "is this agent
behaviour actually better?" a question with an answer.

## Why it is built this way

Most agent demos show one agent doing one task impressively once. That tells you nothing about whether a change to the
decision policy improved things. This project is structured so behaviour can be **run, measured and compared across
scenarios**, which is the difference between a demo and an experiment.

## Architecture

Everything is a system coordinated by a central manager; systems subscribe to events rather than calling each other, so
behaviour can be added or removed without rewriting the loop.

```
systems/
  core/           base_system, event_system, system_manager  (lifecycle + event bus)
  agents/         agent_system, team_system, formation_system,
                  relationship_system (trust), communication_system
  environment/    terrain_system, resource_system, resource_sharing
  combat/         combat_system, battle_mechanics, combat_mechanics
  learning/       learning_system, behavior_learning,
                  experience_memory, genetic_algorithm
  benchmarking/   benchmark_system, benchmark_runner,
                  benchmark_scenarios, benchmark_ui
  decision/ personality/ morale/ analytics/ physics/ ui/ visualization/
```

- **Agent lifecycle**: creation, per-tick update, death, and state carried across ticks.
- **Coordination**: teams, formations, message passing, and a relationship/trust model that changes over time.
- **Learning**: behaviour copying from observed agents, an experience memory, and genetic-algorithm adaption of traits.
- **Benchmarking**: named scenarios + a runner that executes them and a UI that compares runs — the part that turns
  simulation into evaluation.

## Running it

```bash
pip install -r requirements.txt
python main.py                 # main game loop
pytest -q                      # tests
```

Benchmark runs are driven through `systems/benchmarking/benchmark_runner.py`; scenarios live in
`benchmark_scenarios.py`.

## Status — honest

Working: the simulation loop, the event-driven system manager, agent/team/relationship/communication systems, learning
and memory, and the benchmarking harness with scenarios and comparison UI. It has been built and iterated over several
months with extensive logging used as the debugging instrument.

Not done: no published benchmark results table yet; the `backup_*/` snapshot and per-run `logs/` are development
artifacts and are not tracked here (one run's logs reached ~1 GB, which is why log output is the next thing to make
bounded and structured). UI/rendering code is functional but not the point of the repository.

## Notes

- Large runs produce very large logs; run with output redirected and log rotation on.
- The `weights/` directory is ignored — generated artefacts are not source.
