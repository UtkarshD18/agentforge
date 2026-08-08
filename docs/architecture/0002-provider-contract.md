# ADR 0002: Capability Provider Contract

## Status
FROZEN

## Context
Orchestrators need a uniform interface to execute tasks across text models, vision analyzers, and background editing tools without custom routing branches.

## Decisions
1. **Immutable `ExecutionUnit`**: Every task is resolved to an immutable execution unit.
2. **`execute(unit, context)` signature**: Every provider subclass implements a uniform execute endpoint.
3. **`ExecutionResult` list**: Returns lists of typed, first-class results.

## Consequences
- No custom if-statements allowed inside the scheduler loop.
- All actions are fully reproducible, enabling deterministic caching and event replays.
