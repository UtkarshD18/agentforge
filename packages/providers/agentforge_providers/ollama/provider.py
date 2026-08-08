import urllib.request
import urllib.error
import json
from typing import List

from agentforge_core.fabric import CapabilityProvider, ModelConfig, AIRequest, AIResponse, AIResponseUsage, ExecutionRequest, ExecutionResponse

class OllamaProvider(CapabilityProvider):
    """
    Decoupled Ollama Local Compute AI Provider.
    Implements standard AIRequest/AIResponse mapping.
    """
    def __init__(self, endpoint: str = "http://localhost:11434") -> None:
        self.endpoint = endpoint
        self._online = False

    def get_provider_name(self) -> str:
        return "ollama"

    def initialize(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.endpoint}/api/tags")
            with urllib.request.urlopen(req, timeout=1.0) as response:
                if response.status == 200:
                    self._online = True
                    return True
        except Exception:
            pass
        self._online = False
        return True

    def get_available_models(self) -> List[ModelConfig]:
        if not self._online:
            return [
                ModelConfig(
                    model_name="deepseek-r1",
                    capabilities=["text_generation"],
                    cost_tier="low",
                    local=True,
                    score=80
                ),
                ModelConfig(
                    model_name="qwen2.5-coder",
                    capabilities=["text_generation"],
                    cost_tier="low",
                    local=True,
                    score=82
                )
            ]

        try:
            req = urllib.request.Request(f"{self.endpoint}/api/tags")
            with urllib.request.urlopen(req, timeout=1.0) as response:
                data = json.loads(response.read().decode("utf-8"))
                models_list = []
                for item in data.get("models", []):
                    name = item.get("name")
                    capabilities = ["text_generation"]
                    if "vision" in name.lower() or "vl" in name.lower():
                        capabilities.append("vision")
                    models_list.append(ModelConfig(
                        model_name=name,
                        capabilities=capabilities,
                        cost_tier="low",
                        local=True,
                        score=80
                    ))
                return models_list
        except Exception:
            return []

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        if not isinstance(request, AIRequest):
            raise TypeError("OllamaProvider only supports executing AIRequest payloads.")
            
        prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])

        if not self._online:
            mock_text = f"[Ollama Mock Mode] Response using local {request.model} for prompt: '{prompt}'"
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
            payload = {
                "model": request.model,
                "prompt": prompt,
                "stream": False
            }
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.endpoint}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30.0) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                text = resp_data.get("response", "")
                
                # Fetch actual tokens returned by Ollama metadata if available
                prompt_tokens = resp_data.get("prompt_eval_count", len(prompt.split()))
                completion_tokens = resp_data.get("eval_count", len(text.split()))
                
                return AIResponse(
                    text=text,
                    usage=AIResponseUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens
                    ),
                    provider_name=self.get_provider_name(),
                    model_name=request.model
                )
        except Exception as e:
            raise RuntimeError(f"Ollama API execution failed on local model {request.model}: {e}")
