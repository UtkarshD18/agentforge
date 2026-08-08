# ADR 0004: Execution Event Bus

## Status
FROZEN

## Context
A live creative operating system needs to broadcast pipeline status, logs, VRAM updates, and edits to connected companion UIs reactively.

## Decisions
1. **Decentralized EventBus**: Swappable async and sync event publishers.
2. **ExecutionEventType**: Strict namespaced enums (`task.started`, `resource.update`).
3. **EventStore**: Append-only JSON lines log storing and replaying execution histories.

## Consequences
- The workspace UI relies entirely on event streams, preventing direct tight coupling.
