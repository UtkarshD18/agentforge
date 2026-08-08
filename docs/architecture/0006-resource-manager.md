# ADR 0006: Hardware Resource Manager

## Status
FROZEN

## Context
Running local models (YOLO, Whisper, Qwen) on local hardware with limited VRAM (such as 8GB) requires aggressive, predictive memory eviction policies.

## Decisions
1. **`ResourceManager`**: Tracks active VRAM/RAM allocations globally.
2. **`ModelManager`**: Handles model states and loads/unloads models to prevent OOM errors.
3. **`MemoryPlanner`**: Allocates reservation tokens to predict and request resources.

## Consequences
- Workers must acquire model reservations before starting inference, avoiding parallel VRAM collisions.
