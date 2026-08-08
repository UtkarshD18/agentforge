# AgentForge Product Roadmap

This document outlines the six phases to establish AgentForge as **the operating system for AI-powered creative work**.

---

## Phase 1: First Intelligent Timeline
**Goal**: AI understands the host timeline programmatically.
- **Deliverables**: Resolve Host connection, Motion Analyzer, Knowledge update indices, Media Graph updates, jump-to-frame controls, and minimal Workspace panel.
- **Workflow verification**: User analyzes timeline ➔ motion nodes appear in workspace ➔ user clicks node ➔ timeline jumps to timestamp.

## Phase 2: AI Editor
**Goal**: AI executes edits directly on the timeline.
- **Deliverables**: Planner compiles text prompt ("Remove all dead air") ➔ generates recipe instructions ➔ HostAdapter executes Split/Merge cuts on Resolve timeline.

## Phase 3: AI Director
**Goal**: Multiple specialized agents collaborate on a complex timeline objective.
- **Deliverables**: Speech, Vision, Motion, and Style agents collaborate to compose edit recipes ("Make this feel like a commercial").

## Phase 4: Creative OS Expansion
**Goal**: Extend the core execution graph to other creative applications.
- **Deliverables**: Photoshop, Blender, and VS Code host adapter integrations.

## Phase 5: Capability Marketplace
**Goal**: Standardize plugin packages so community creators can install and share capability nodes.
- **Deliverables**: Plugin installer panel, manifest verifiers, and secure sandbox execution gates.

## Phase 6: Distributed Studio
**Goal**: Run execution graphs across multiple local and cloud worker systems.
- **Deliverables**: Multi-worker scheduler and distributed task queues.

---

## 🎯 Implementation Rule
Every feature proposal must validate exactly one of three goals before coding starts:
1. Does this improve **understanding**?
2. Does this improve **editing**?
3. Does this improve **orchestration**?
