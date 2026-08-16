# AgentForge OS: Core Design Principles

This document serves as the project's "constitution." Every code addition, plugin implementation, or architectural extension must adhere to these ten principles.

---

### 1. Runtime is Provider-Agnostic
The core execution engine does not depend on specific LLMs or API providers. Agents request abstract **Capabilities** (e.g. `reasoning`, `transcription`), and the scheduler resolves them dynamically.

### 2. Runtime Owns Execution, Studio Owns Visualization
The backend runtime owns all state, orchestration logic, and graph execution. The frontend Studio UI is a pure renderer of state and events. The runtime must be capable of running fully headless.

### 3. Everything Important Emits Events
Any status shift, error, tool invocation, token count update, or human interaction must emit a structured, versioned event onto the central **Event Bus**. The UI does not poll.

### 4. Agents Communicate via Artifacts
Agents never modify or share mutable internal state. An agent writes outputs to immutable **Artifacts** (e.g., transcripts, timelines), which are consumed by downstream agents.

### 5. Workflows are Data, Not Code
Workflow DAGs are defined as JSON/YAML structures. You do not write Python code to create a new editing sequence; you write a workflow graph configuration.

### 6. Packages are Portable
A package is a self-contained bundle containing prompts, layouts, constraints, and custom UI definitions. Installing a capability is as simple as dropping a directory or `.zip` file into the runtime paths.

### 7. Core Stays Open Source
The orchestrator runtime, scheduler, event bus, storage interfaces, basic video plugins, and frontend Studio UI are fully open source (MIT/Apache). Commercial value is delivered exclusively via signed premium plugins and optional hosted cloud services.

### 8. Everything is Replaceable Behind Interfaces
From the storage backend (SQLite/SurrealDB) to the UI panels, every system component sits behind a stable abstract interface. If a component must be replaced, the rest of the application remains unchanged.

### 9. APIs are Versioned
All internal APIs, WebSocket routers, and Event schemas are versioned (e.g. `/api/v1/`, event version `"1.0"`). This ensures backward compatibility as Studio and Runtime evolve independently.

### 10. Prefer Composition Over Inheritance
Model capabilities, tools, and supervisor hierarchies are built by composing small, single-responsibility components rather than extending deep class hierarchies.

### 11. Rigorous Architectural Filtering
Only adopt structural suggestions and suggestions after deep thinking about the established architecture. Only integrate changes that provide clear engineering value, keeping the core lightweight, modular, and performant.

