# ADR 0001: Monorepo Package Layout

## Status
FROZEN

## Context
AgentForge OS v1.0 is designed as an embedded AI operating system for creative hosts. To prevent architectural bloat and packaging refactoring cycles, package boundaries are permanently frozen.

## Decisions
1. **Core Package (`packages/core`)**: House domain model specifications (revisions, media nodes, SQLite repositories).
2. **Project Package (`packages/project`)**: Define workspace settings and collections of active graphs.
3. **Knowledge Package (`packages/knowledge`)**: Memory registries, semantic search, prompt context indices.
4. **Kernel Package (`packages/kernel`)**: Daemon event dispatchers, session registries.
5. **Scheduler Package (`packages/scheduler`)**: Stateless placement engines mapping execution units to resources.
6. **Runtime Package (`packages/runtime`)**: Immutable execution loops.
7. **Providers Package (`packages/providers`)**: Swappable LLM adapters.
8. **Plugins Package (`packages/plugins`)**: crawlers dynamically parsing plugin manifests.
9. **Hosts Package (`packages/hosts`)**: Standardize app commands and capability bindings.

## Consequences
- Renaming packages or adding new core directories is disallowed for v1.
- All new capabilities must compile to swappable plugins within these frozen paths.
