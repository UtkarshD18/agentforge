from agentforge_core.fabric import CapabilityProvider, ModelConfig, ExecutionFabric, AIRequest, AIResponse, AIResponseUsage, ExecutionRequest, ExecutionResponse

class MockCapabilityProvider(CapabilityProvider):
    def __init__(self, name: str, models: list) -> None:
        self.name = name
        self.models = models

    def get_provider_name(self) -> str:
        return self.name

    def initialize(self) -> bool:
        return True

    def get_available_models(self) -> list:
        return self.models

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        if not isinstance(request, AIRequest):
            raise TypeError("MockCapabilityProvider only supports executing AIRequest payloads.")
        prompt = "\n".join([msg.content for msg in request.messages])
        text = f"Mock response from {self.name} using {request.model} for '{prompt}'"
        return AIResponse(
            text=text,
            usage=AIResponseUsage(
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(text.split()),
                total_tokens=len(prompt.split()) + len(text.split())
            ),
            provider_name=self.name,
            model_name=request.model
        )

def test_capability_routing():
    registry = ExecutionFabric()
    
    # 1. Register Mock Google Cloud Provider
    google = MockCapabilityProvider(
        name="google",
        models=[
            ModelConfig(
                model_name="gemini-2.5-flash",
                capabilities=["text_generation", "vision"],
                cost_tier="low",
                local=False,
                score=85
            ),
            ModelConfig(
                model_name="gemini-2.5-pro",
                capabilities=["text_generation", "vision"],
                cost_tier="high",
                local=False,
                score=95
            )
        ]
    )
    registry.register_provider(google)
    
    # 2. Register Mock Ollama Local Provider
    ollama = MockCapabilityProvider(
        name="ollama",
        models=[
            ModelConfig(
                model_name="deepseek-r1",
                capabilities=["text_generation"],
                cost_tier="low",
                local=True,
                score=80
            )
        ]
    )
    registry.register_provider(ollama)
    
    # Check 1: Resolving vision task when cost is not constrained
    match = registry.resolve_best_model(["vision"])
    assert match is not None
    provider, model = match
    assert provider.get_provider_name() == "google"
    assert model == "gemini-2.5-pro" # pro has higher score (95) than flash (85)
    
    # Check 2: Resolving vision task when cost is constrained to low/medium
    match_low = registry.resolve_best_model(["vision"], max_cost_tier="medium")
    assert match_low is not None
    assert match_low[1] == "gemini-2.5-flash" # pro exceeds cost limits, flash chosen
    
    # Check 3: Resolving text task favoring local models (Ollama)
    match_local = registry.resolve_best_model(["text_generation"], prefer_local=True)
    assert match_local is not None
    assert match_local[1] == "deepseek-r1" # r1 score is boosted (80 + 20 = 100) compared to google
