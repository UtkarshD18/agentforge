# ADR 0000: Architecture Governance & Freeze Rules

## Status
ACTIVE / ENFORCED

## Context
AgentForge OS v1.0 has reached architectural maturity. To prevent package churn, unnecessary refactoring cycles, and scope creep, we establish permanent freeze rules.

## Decisions
1. **Package Freeze**: The 14 workspace packages (`core`, `project`, `knowledge`, `agents`, `planner`, `scheduler`, `orchestrator`, `runtime`, `resources`, `plugins`, `providers`, `hosts`, `eventbus`, `state`, `workspace`) are permanently frozen. No new top-level packages may be introduced after v1 freeze. New capabilities must be implemented as plugins, providers, analyzers, or host adapters unless a documented architectural limitation is demonstrated.
2. **Interface Stability**: Public API interfaces (e.g. `planner.compile`, `scheduler.schedule`, `orchestrator.run`, `provider.execute`, `resources.allocate`, `hosts.execute_command`) must remain stable. Breaking changes require a major version update.
3. **Plugin-First Development**: All new analyzers, capability adapters, and host integrations must be implemented as modular, dynamically discovered plugin entry points.
4. **Governance Verification**: Any proposed architectural layout changes must first be justified via a new Architecture Decision Record (ADR) and explicitly approved.
5. **Golden Path Execution**: All features must flow through the frozen execution pipeline: Goal ➔ ExecutionPlan ➔ TaskGraph ➔ ExecutionUnit ➔ CapabilityProvider ➔ ExecutionResult ➔ Knowledge/MediaGraph/EventStore ➔ HostCommand ➔ HostAdapter. Direct bypass is prohibited.
6. **VRAM Constraint Scheduling**: To optimize for 8GB GPUs, only one heavyweight local model may reside in VRAM at a time. The scheduler must evict inactive models before allocating subsequent local models.
7. **Strict Event Vocabulary**: Event logs must stick to the namespaced event types schema (`task.*`, `execution.*`, `resource.*`, `knowledge.*`, `graph.*`, `host.*`). Custom dynamic namespaces are forbidden.
8. **Measurable Success Metrics**: Implementations must enforce performance metrics (e.g. host attachment <2s, dashboard updates <100ms, jump-to-frame <200ms, and zero GPU memory leaks).
9. **DaVinci Resolve Reference Host**: DaVinci Resolve serves as our reference host integration. Host API generalizations should only occur once the Resolve implementation is verified and complete.

## Consequences
- Prevents architectural drift.
- Implementation focus shifts entirely to shipping vertical capability slices.
