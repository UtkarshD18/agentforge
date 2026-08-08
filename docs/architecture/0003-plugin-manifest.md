# ADR 0003: Plugin Manifest Schema

## Status
FROZEN

## Context
All executable plugins (providers, analyzers, hosts, graph builders) must declare requirements, outputs, and profiles uniformly to support dynamic local discovery and future marketplace sharing.

## Decisions
1. **Manifest File**: Plugins must ship a root `manifest.yaml` file.
2. **WorkerRequirements**: Decouples hardware labels and VRAM sizes from Python code.
3. **Registry scanning**: Crawls search directories for manifests to auto-populate registries.

## Consequences
- Installing or disabling capabilities requires no code changes.
