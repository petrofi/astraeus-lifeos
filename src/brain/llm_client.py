"""
ASTRAEUS - Autonomous Life Orchestrator
LLM Client Module

This module provides a unified interface for multiple AI providers:
- OpenAI GPT-4
- Google Gemini
- Ollama (local models)
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator
import structlog

from src.config import settings

logger = structlog.get_logger()


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key)
            self.model = model
            logger.info("OpenAI client initialized", model=model)
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response using OpenAI API."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("OpenAI generation failed", error=str(e))
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using OpenAI API."""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error("OpenAI streaming failed", error=str(e))
            raise


class GeminiClient(BaseLLMClient):
    """Google Gemini client implementation."""
    
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model)
            self.model_name = model
            logger.info("Gemini client initialized", model=model)
        except ImportError:
            raise ImportError("Please install google-generativeai: pip install google-generativeai")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response using Gemini API."""
        try:
            # Combine system prompt with user prompt for Gemini
            full_prompt = f"{system_prompt}\n\n---\n\nKullanıcı mesajı: {prompt}"
            
            # Run in thread pool since Gemini SDK is sync
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    }
                )
            )
            return response.text
        except Exception as e:
            logger.error("Gemini generation failed", error=str(e))
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using Gemini API."""
        try:
            full_prompt = f"{system_prompt}\n\n---\n\nKullanıcı mesajı: {prompt}"
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    },
                    stream=True
                )
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error("Gemini streaming failed", error=str(e))
            raise


class OllamaClient(BaseLLMClient):
    """Ollama local model client implementation."""
    
    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3"):
        try:
            import ollama
            self.client = ollama.AsyncClient(host=host)
            self.model = model
            self.host = host
            logger.info("Ollama client initialized", host=host, model=model)
        except ImportError:
            raise ImportError("Please install ollama: pip install ollama")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response using Ollama."""
        try:
            response = await self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error("Ollama generation failed", error=str(e))
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using Ollama."""
        try:
            stream = await self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                },
                stream=True
            )
            async for chunk in stream:
                if chunk["message"]["content"]:
                    yield chunk["message"]["content"]
        except Exception as e:
            logger.error("Ollama streaming failed", error=str(e))
            raise


def get_llm_client(
    provider: Optional[str] = None,
    **kwargs
) -> BaseLLMClient:
    """
    Factory function to get the appropriate LLM client based on configuration.
    
    Args:
        provider: Override the provider from settings (openai, gemini, ollama)
        **kwargs: Additional arguments passed to the client
    
    Returns:
        Configured LLM client instance
    """
    provider = provider or settings.ai_provider
    
    if provider == "openai":
        return OpenAIClient(
            api_key=kwargs.get("api_key", settings.openai_api_key),
            model=kwargs.get("model", settings.openai_model)
        )
    elif provider == "gemini":
        return GeminiClient(
            api_key=kwargs.get("api_key", settings.gemini_api_key),
            model=kwargs.get("model", settings.gemini_model)
        )
    elif provider == "ollama":
        return OllamaClient(
            host=kwargs.get("host", settings.ollama_host),
            model=kwargs.get("model", settings.ollama_model)
        )
    else:
        raise ValueError(f"Unknown AI provider: {provider}")


# Create a default client instance
async def get_default_client() -> BaseLLMClient:
    """Get the default LLM client based on settings."""
    return get_llm_client()
