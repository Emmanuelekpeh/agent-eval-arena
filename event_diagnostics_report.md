# Event Handler Diagnostics Report
Generated at: 2025-04-14 16:31:08

## Event Summary
Total event types tracked: 4

| Event Type | Calls | Handlers | Success Rate | Avg Duration (ms) |
|------------|-------|----------|-------------|------------------|
| {'entity_id': 1} | 1 | 1 | 100.00% | 101.43 |
| {'entity_id': 1, 'other_id': 2} | 1 | 1 | 100.00% | 501.16 |
| {'agent_id': 1, 'damage': 10} | 1 | 1 | 100.00% | 0.00 |
| {'agent_id': 2, 'damage': 20, 'should_fail': True} | 1 | 1 | 0.00% | 0.00 |

## Registered Event Handlers
| Event Type | Handlers |
|------------|----------|
| ENTITY_CREATED | __main__.monitored_handler |
| ENTITY_DESTROYED | None |
| COLLISION | None |
| ENTITY_COLLISION | __main__.slow_monitored_handler |
| AGENT_DAMAGED | __main__.error_monitored_handler |

## Slowest Handlers
| Handler | Avg Duration (ms) |
|---------|------------------|
| __main__.slow_monitored_handler | 501.16 |
| __main__.monitored_handler | 101.43 |
| __main__.error_monitored_handler | 0.00 |

## Most Frequent Errors
### ValueError: 1 occurrences

| Event Type | Handler | Timestamp |
|------------|---------|-----------|
| {'agent_id': 2, 'damage': 20, 'should_fail': True} | __main__.error_monitored_handler | 2025-04-14 16:31:08 |

#### Sample Traceback
```
Traceback (most recent call last):
  File "C:\Users\emman\Projects\training day\utils\event_diagnostics_patched.py", line 481, in wrapper
    result = func(event, *args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\emman\Projects\training day\event_system_test.py", line 115, in error_monitored_handler
    raise ValueError("Simulated error in monitored handler")
ValueError: Simulated error in monitored handler

```

## Handler Statistics
| Handler | Calls | Errors | Error Rate | Avg Duration (ms) |
|---------|-------|--------|------------|------------------|
| __main__.monitored_handler | 1 | 0 | 0.00% | 101.43 |
| __main__.slow_monitored_handler | 1 | 0 | 0.00% | 501.16 |
| __main__.error_monitored_handler | 2 | 1 | 50.00% | 0.00 |