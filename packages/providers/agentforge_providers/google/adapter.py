from abc import ABC, abstractmethod
import google.generativeai as genai

class GoogleSDKAdapter(ABC):
    """
    Decoupled interface wrapping the Google Gemini Generative AI SDK.
    Prevents direct runtime model dependency on external libraries.
    """
    @abstractmethod
    def configure(self, api_key: str) -> None:
        pass

    @abstractmethod
    def generate_content(self, model_name: str, prompt: str) -> str:
        pass

class GenAISDKAdapter(GoogleSDKAdapter):
    """
    Concrete wrapper utilizing the official google-generativeai package.
    """
    def configure(self, api_key: str) -> None:
        genai.configure(api_key=api_key)

    def generate_content(self, model_name: str, prompt: str) -> str:
        client = genai.GenerativeModel(model_name)
        response = client.generate_content(prompt)
        return response.text
