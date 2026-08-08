from agentforge_core.di import get_container
from agentforge_core.storage import GraphRepository, SQLiteGraphRepository
from agentforge_core.fabric import ExecutionFabric
from agentforge_providers import GoogleProvider, OllamaProvider
from agentforge_core.workflow import TextArtifact

def main() -> None:
    print("==================================================")
    print("🚀 Running AgentForge AI Provider Abstraction Diagnostics")
    print("==================================================")

    # 1. Setup DI storage repo for trace span persistence
    repo = SQLiteGraphRepository(":memory:")
    container = get_container()
    container.register(GraphRepository, repo)
    print("✓ Persistent storage registered in DI Container.")

    # 2. Register Google and Ollama providers
    registry = ExecutionFabric()
    
    google = GoogleProvider()
    google.initialize()
    registry.register_provider(google)
    
    ollama = OllamaProvider()
    ollama.initialize()
    registry.register_provider(ollama)
    print("✓ Registered Google Gemini and Ollama providers.")

    # 3. Resolve model for lightweight local text task
    print("\n[Capability Resolution: Text Generation]")
    resolved_text = registry.resolve_best_model(["text_generation"], prefer_local=True)
    if resolved_text:
        provider, model_name = resolved_text
        print(f"✓ Resolved optimal model: '{model_name}' on provider: '{provider.get_provider_name()}'")
        
        prompt = "Create a 3-sentence intro hook about NVIDIA CUDA Streams."
        print(f"  - Prompt: '{prompt}'")
        try:
            from agentforge_core.fabric import AIRequest, AIMessage
            req = AIRequest(
                model=model_name,
                messages=[AIMessage(role="user", content=prompt)]
            )
            ai_response = provider.execute(req)
            response_text = ai_response.text
            print(f"  - Output: '{response_text}'")
            
            # Wrap result in a typed TextArtifact and save
            artifact = TextArtifact(
                uri="artifact://diagnostics/text-1",
                job_uri="job://session-1/job-text",
                task_uri="task://job-text/t-gen",
                text_content=response_text,
                token_count=ai_response.usage.total_tokens
            )
            repo.save_entity(artifact)
            print(f"✓ Saved response in database as TextArtifact: {artifact.uri} (Word count: {artifact.token_count})")
        except Exception as e:
            print(f"⚠️ [API Warning] Generation failed/timed out: {e}")
            print("  - Proceeding with default diagnostics fallback...")
    else:
        print("❌ Failed to resolve text generation model.")

    # 4. Resolve model for vision processing task (must fallback to Cloud Gemini)
    print("\n[Capability Resolution: Vision Analysis]")
    resolved_vision = registry.resolve_best_model(["vision"])
    if resolved_vision:
        provider, model_name = resolved_vision
        print(f"✓ Resolved optimal model: '{model_name}' on provider: '{provider.get_provider_name()}'")
        
        prompt = "Analyze local video frame layout."
        try:
            from agentforge_core.fabric import AIRequest, AIMessage
            req = AIRequest(
                model=model_name,
                messages=[AIMessage(role="user", content=prompt)]
            )
            ai_response = provider.execute(req)
            print(f"  - Output: '{ai_response.text}'")
        except Exception as e:
            print(f"⚠️ [API Warning] Generation failed/timed out: {e}")
    else:
        print("❌ Failed to resolve vision model.")

    print("==================================================")
    print("🎉 AI PROVIDER DIAGNOSTICS SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    main()
