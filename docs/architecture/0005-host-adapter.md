# ADR 0005: Host Adapter Contract

## Status
FROZEN

## Context
AgentForge OS must remain host-independent, running inside DaVinci Resolve, Photoshop, Blender, or VS Code by swapping active host adapter registrations.

## Decisions
1. **`HostAdapter` Base Class**: Declares abstract hooks for commands and capabilities.
2. **`HostCommand`**: Standardized command payloads (`timeline.edit`, `canvas.resize`).
3. **`HostCapabilities`**: Active host capability flags.

## Consequences
- The kernel runs independent of application-specific APIs.
