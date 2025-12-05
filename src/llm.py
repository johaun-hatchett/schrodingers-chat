from openai import OpenAI
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

from messages import AIMessage, Transcript

class LLMException(Exception):
    """Exception raised for errors in the LLM."""
    pass

class BaseLLM(ABC):
    """Abstract base class for LLMs."""
    @abstractmethod
    def generate_response(self, prompt: str, history: Optional[List[Dict[str, str]]]=None) -> AIMessage:
        """Generates a response from the LLM."""
        pass

class GPT(BaseLLM):
    """GPT LLM."""
    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None):
        """Initializes the LLM."""
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def generate_response(self, prompt: str, transcript: Optional[Transcript]=None) -> AIMessage:
        """Generates a response from the LLM."""
        if transcript:
            history: List[Dict[str, str]] = []
            for msg in transcript.serialize():
                if msg["speaker"] == "human":
                    history.append({"role": "user", "content": msg["content"]})
                elif msg["speaker"] == "ai":
                    history.append({"role": "assistant", "content": msg["content"]})
                else:
                    # fallback for unknown speaker
                    history.append({"role": "system", "content": msg["content"]})
        else:
            history: List[Dict[str, str]] = []
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=history + [{"role": "user", "content": prompt}]
            )
            return AIMessage(response.choices[0].message.content)
        except Exception as e:
            raise LLMException(f"Error generating response from {self.model}: {e}")