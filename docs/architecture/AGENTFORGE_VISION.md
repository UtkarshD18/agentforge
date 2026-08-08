# AgentForge Vision

## 1. What is AgentForge?
AgentForge is **the operating system for AI-powered creative work**, not just another AI video editor. It coordinates heterogeneous local and cloud resources (Whisper, YOLO, LLMs) to orchestrate complex creative analysis and editing workflows directly inside host creative software.

## 2. Who is it for?
AgentForge targets professional video creators first, starting with a deep, bidirectional integration inside **DaVinci Resolve**. It will extend to other creative host environments (Photoshop, Blender, VS Code) in future major versions.

## 3. Flagship Workflow
A user opens Resolve, attaches the AgentForge panel, and clicks "Analyze Timeline." An interactive, live-pulsing task DAG coordinates visual, language, and motion analyzers to compile structured metadata, write entries directly to the Project Knowledge Store, and allow frame-accurate jump-to timestamp controls.

## 4. Two-Side IPC Architecture Model
To ensure native creative host integration, AgentForge enforces a split execution boundaries topology:
1. **Embedded Workflow Panel (Host-Side)**: Docked directly inside the creative host UI (e.g. HTML5/JavaScript panel inside Resolve), responsible for reading/writing host state and rendering the chat and task DAG visualizer dashboard.
2. **AgentForge Engine (Daemon-Side)**: Background process running locally, responsible for managing multi-agent reasoning, cloud models (Gemini Flash), local models execution, VRAM allocation planner, and persistence.
3. **IPC Interconnect**: A local WebSocket/HTTP API gateway manages bidirectional synchronization between the Host Panel and the background Daemon Engine.

## 5. What Should Never Change?
- **Host-Agnostic Core**: Host applications are isolated behind standard `HostCommand` instruction adapters.
- **Model-Agnostic Capabilities**: AI models are hidden behind abstract capability resolvers.
- **Resource-Aware Scheduling**: Global hardware manager (RAM/VRAM) allocations enforce OOM-free local model loading/unloading limits.
- **Strict Data Integrity**: Unambiguous, version-controlled Media and Execution graphs stored statefully in separate SQLite databases.
- **Golden Path Execution**: All pipeline changes flow sequentially from Goal to ExecutionPlan to TaskGraph to ExecutionUnit to CapabilityProvider to EventStore.
- **Independent Capability Replacement**: Every capability must be independently replaceable without altering the orchestration layer (e.g. replacing Whisper with Deepgram/Parakeet leaves planning intact).
