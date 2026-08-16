# AgentForge System Audit & Prioritized Roadmap (Source of Truth)

> [!NOTE]
> This document is the **Source of Truth** and **Project Hand-off Checklist** for the transition of AgentForge into a premium AI Vlog Editor. Use this to safely resume development of Sprint 3.

---

## 1. System Health & Current Verified Baseline

The repository is currently verified and clean at **Stage Version 0.5** (Sprint 2.5 completion). 

### A. Test Execution Status
- **Unit & Integration Tests**: 58 tests are implemented, and all 58 are passing cleanly (`uv run pytest -v`).
- **E2E Test (`test_real_youtube_short.py`)**: Fully verified. The test connects to DaVinci Resolve, builds a vertical timeline, reframes shots, and renders a 1080x1920 (9:16) MP4 video with `ffprobe` format verification.
  - *Note*: This test skips automatically if DaVinci Resolve is not actively running on the host system.

### B. Gemini Configuration & Verification
- **Integration**: Gemini API calls are loaded via `os.getenv("GEMINI_API_KEY")`.
- **Model**: Configured to use `gemini-2.5-flash` for structured JSON planning (`EditPlan`).
- **Deterministic Fallback**: If `GEMINI_API_KEY` is not present in the environment, the system automatically falls back to generating a deterministic mock plan to avoid crashes.
- **Verification**: Running the tests with `GEMINI_API_KEY` exported connects to Google's GenAI API, successfully generating 20 structured edit cuts with custom zoom, pan, and tilt transforms.

### C. Genuinely Implemented Resolve Features (Sprint 2.5)
- **Timeline Assembly**: Non-destructive In/Out point trimming and appending clips.
- **Race Condition Guard**: `0.2` seconds sleep between timeline appends.
- **Vertical Canvas**: Custom resolution set to `1080x1920` (9:16).
- **Transformation Math**: Scaled calculations for `ZoomX`, `ZoomY`, `Pan`, and `Tilt` to center landscape footage on vertical grids.
- **Timeline Auditor**: Checks timeline structures and frame counts against the original edit plan.
- **Render Engine integration**: Automated rendering via Resolve TikTok preset with polling/timeout.

---

## 2. Sprint 3 Implementation Plan (AI Vlog Editor transition)

The transition plan has been fully drafted and detailed in [implementation_plan.md](file:///home/shadow/.gemini/antigravity-ide/brain/6e512a6a-5f44-4011-b0e2-056ed53ca024/implementation_plan.md). It outlines the integration of 15 components to be implemented in dependency order:

### A. 15-Component Breakdown
1. **GoogleProvider migration**: Upgrade deprecated `google.generativeai` to the new `google.genai` SDK.
2. **DurationSpec & RichStyleProfile**: Replace hardcoded 30-second target with dynamic bounds (`min`/`max`/`target`).
3. **MusicAgent**: Use `librosa` to compute BPM, beat locations, downbeats, and energy curves from audio.
4. **Beat-Aware EditPlan**: Snapping timeline cut positions to the music's beat grid.
5. **StoryAgent**: Structure narrative flow based on Whisper transcripts (HOOK/SETUP/ACTION/PAYOFF/ENDING).
6. **VisionAgent**: A 2-stage visual analyzer using a cheap CPU pre-filter followed by VLM-based scene details extraction.
7. **RichStyleProfile**: Expand editing style grammar with confidence ratings and provenance details.
8. **CaptionAgent**: Generate word-timestamp highlights dynamically.
9. **Resolve Effects Audit**: Test and verify transitions, speed ramps, and opacity transforms on the active Resolve instance.
10. **AudioAgent & AudioPlan**: Apply voice normalization and duck music volume during talking segments.
11. **Subject-Aware Vertical Crop**: Keep faces and main subjects centered during crop/zoom.
12. **VlogShortPipeline**: Wires all agents in the correct execution order.
13. **Editorial Skills**: Loads structured markdown guides into the Director prompt based on editing goals.
14. **QualityControlAgent**: Multi-phase QC checking technical metrics (clipping, freeze, silence) and visual/editorial quality.
15. **E2E Acceptance Suite**: A full verification run generating `AgentForge_Vlog_Short_002.mp4` and `agentforge_edit_report.json`.

---

## 3. Open Design Questions to Resolve

Before starting implementation of Sprint 3 components, align on the following:
1. **Music file location**: Where should test/runtime music files be stored? (Suggested: configured `MUSIC_DIR` environment variable).
2. **Whisper model size**: Upgrade from `whisper-base` to `whisper-small` or `whisper-medium` for word-level caption timestamps?
3. **VLM Backend**: Use local Qwen-VL or leverage remote Gemini Vision API for visual description extraction?
4. **Caption Burn-In**: Fallback to burning subtitles via `ffmpeg` if Resolve Fusion scripting for text is unverified?
5. **Skills Directory**: Commit Markdown guides under `skills/vlog_short/` at the repository root or inside `packages/agents/`?

---

## 4. Safeguard Guide: How to Resume Development

Follow these steps to launch the workspace and continue building:

### A. Prepare Python Environment
Ensure `uv` is installed and run:
```bash
uv venv
source .venv/bin/activate
uv sync
```

### B. Launch DaVinci Resolve
Open DaVinci Resolve on the host system. Ensure that **External Scripting** is enabled in Resolve settings (under *Preferences > System > Control Panels > External scripting* set to "Local").

### C. Run the Core Daemon
Start the AgentForge runtime daemon:
```bash
export GEMINI_API_KEY="your-api-key"
uv run python apps/runtime/agentforge_runtime/main.py
```

### D. Run Verification Checks
- **Unit Tests**:
  ```bash
  uv run pytest
  ```
- **E2E Integration Test** (requires DaVinci Resolve running):
  ```bash
  export GEMINI_API_KEY="your-api-key"
  export PYTHONPATH="/opt/resolve/Developer/Scripting/Modules"
  uv run pytest tests/e2e/test_real_youtube_short.py -v
  ```
