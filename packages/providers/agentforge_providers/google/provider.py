import os
from typing import List, Optional
from pydantic import BaseModel

from agentforge_core.fabric import CapabilityProvider, ModelConfig, AIRequest, AIResponse, AIResponseUsage, ExecutionRequest, ExecutionResponse
from agentforge_providers.google.adapter import GoogleSDKAdapter, GenAISDKAdapter

class GoogleProvider(CapabilityProvider):
    """
    Decoupled Google Gemini AI Provider.
    Implements standard AIRequest/AIResponse mapping and uses the pluggable SDK adapter.
    """
    def __init__(self, sdk_adapter: Optional[GoogleSDKAdapter] = None) -> None:
        self._api_key = os.getenv("GEMINI_API_KEY")
        self.adapter = sdk_adapter or GenAISDKAdapter()
        self._initialized = False

    def get_provider_name(self) -> str:
        return "google"

    def initialize(self) -> bool:
        if self._api_key:
            try:
                self.adapter.configure(self._api_key)
                self._initialized = True
                return True
            except Exception:
                pass
        self._initialized = True
        return True

    def get_available_models(self) -> List[ModelConfig]:
        return [
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

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        if not isinstance(request, AIRequest):
            raise TypeError("GoogleProvider only supports executing AIRequest payloads.")
            
        # Reconstruct standard prompt query from messages
        prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])

        if not self._api_key:
            # Fallback mock mode
            mock_text = f"[Google Gemini Mock Mode] Response using {request.model} for prompt: '{prompt}'"
            return AIResponse(
                text=mock_text,
                usage=AIResponseUsage(
                    prompt_tokens=len(prompt.split()),
                    completion_tokens=len(mock_text.split()),
                    total_tokens=len(prompt.split()) + len(mock_text.split())
                ),
                provider_name=self.get_provider_name(),
                model_name=request.model
            )

        try:
            self.initialize()
            response_text = self.adapter.generate_content(request.model, prompt)
            
            # Estimate token counts for the returned response
            prompt_tokens = len(prompt.split())
            completion_tokens = len(response_text.split())
            
            return AIResponse(
                text=response_text,
                usage=AIResponseUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens
                ),
                provider_name=self.get_provider_name(),
                model_name=request.model
            )
        except Exception as e:
            raise RuntimeError(f"Google Gemini provider failed to generate content: {e}")
