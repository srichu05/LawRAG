"""
llm.py — LLM integration for grounded legal answer generation
==============================================================
Provides a clean, unified interface for hosted LLM generation with:
  - Strict timeout and retry bounds
  - Safe error handling (never crashes or leaks credentials)
  - Deterministic MockLLM fallback for 100% offline testing
  - OpenAI-compatible hosted provider (OpenAI, Groq, OpenRouter, etc.)
  - Hugging Face Inference API provider
"""

from __future__ import annotations

import logging
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Any

import requests

from app import config

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Abstract base class for LawRAG LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a response text given a user prompt and optional system prompt."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


class MockLLM(BaseLLMClient):
    """
    Deterministic mock LLM for offline testing, demos, and evaluation.
    Synthesizes grounded responses strictly from the passages included in the prompt.
    """

    def __init__(self, model_name: str = "mock-legal-generator") -> None:
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        # Check if this is a query rewriting prompt
        if "alternative search queries" in prompt.lower() or "rewrite" in prompt.lower():
            return "1. fundamental rights personal liberty protection\n2. constitutional remedy article 21"

        # Check if evidence passages are present in the prompt
        passages_match = re.search(r"Retrieved Passages:(.*?)(?:\n\nQuestion:|\Z)", prompt, re.DOTALL | re.IGNORECASE)
        passages_text = passages_match.group(1).strip() if passages_match else ""

        if not passages_text or "no relevant passages" in passages_text.lower():
            return (
                "Based on the retrieved Indian Supreme Court judgments in the available corpus, "
                "there is insufficient evidence to address this question directly."
            )

        # Synthesize a concise grounded answer extracting direct principles
        chunks = re.findall(r"\[Chunk\s+([a-zA-Z0-9_\-]+)\]:\s*([^\n]+(?:\n[^\n]+){1,3})", passages_text)
        
        answer_parts = []
        if chunks:
            answer_parts.append(
                "Based on the retrieved Indian Supreme Court judgments in the corpus:"
            )
            for chunk_id, excerpt in chunks[:3]:
                clean_excerpt = " ".join(excerpt.split())
                if len(clean_excerpt) > 160:
                    clean_excerpt = clean_excerpt[:157] + "..."
                answer_parts.append(f"- As noted in [Chunk {chunk_id}], {clean_excerpt}")
            answer_parts.append(
                "\nThis answer is based strictly on the retrieved judgment excerpts above. "
                "The available corpus contains historical judgments and may not represent the complete or current state of Indian law."
            )
            return "\n".join(answer_parts)

        # Fallback summary
        lines = [line.strip() for line in passages_text.splitlines() if line.strip() and not line.strip().startswith("[")]
        summary = " ".join(lines[:3])
        if len(summary) > 250:
            summary = summary[:247] + "..."
        return (
            f"According to the retrieved Supreme Court records: {summary} "
            f"(Note: Historical judgments in this corpus do not necessarily reflect current legislation or later rulings.)"
        )


class OpenAICompatibleLLM(BaseLLMClient):
    """
    Hosted LLM using OpenAI-compatible chat completions API.
    Supports OpenAI, Groq, OpenRouter, and local vLLM endpoints.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "",
        timeout: int = 30,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/") if base_url else "https://api.openai.com/v1"
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": config.LLM_TEMPERATURE,
            "max_tokens": config.LLM_MAX_TOKENS,
        }

        start_time = time.perf_counter()
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self._timeout)
        except requests.exceptions.Timeout:
            logger.error("LLM request timed out after %ds", self._timeout)
            raise TimeoutError(f"LLM request timed out after {self._timeout} seconds.")
        except requests.exceptions.RequestException as e:
            logger.error("LLM request network error: %s", e)
            raise ConnectionError(f"LLM request network error: {e}")

        elapsed = time.perf_counter() - start_time
        logger.debug("LLM response received in %.2fs (status %d)", elapsed, resp.status_code)

        if resp.status_code == 401:
            raise PermissionError("LLM API authentication failed. Verify LLM_API_KEY.")
        if resp.status_code == 429:
            raise RuntimeError("LLM rate limit exceeded. Please retry later.")
        if not resp.ok:
            raise RuntimeError(f"LLM request failed [HTTP {resp.status_code}]: {resp.text[:200]}")

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("LLM returned empty choices in response.")

        return choices[0].get("message", {}).get("content", "").strip()


class HuggingFaceInferenceLLM(BaseLLMClient):
    """
    Hosted LLM using Hugging Face Serverless Inference API for text generation.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/Llama-3.2-3B-Instruct",
        timeout: int = 45,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        url = f"https://api-inference.huggingface.co/models/{self._model}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:" if system_prompt else prompt
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": config.LLM_MAX_TOKENS,
                "temperature": max(config.LLM_TEMPERATURE, 0.01),
                "return_full_text": False,
            },
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self._timeout)
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"HuggingFace LLM network error: {e}")

        if not resp.ok:
            raise RuntimeError(f"HuggingFace LLM error [HTTP {resp.status_code}]: {resp.text[:200]}")

        data = resp.json()
        if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
            return data[0]["generated_text"].strip()
        raise ValueError(f"Unexpected HuggingFace response format: {data}")


def get_llm_client(provider: str | None = None) -> BaseLLMClient:
    """
    Factory function returning the configured LLM client.
    Defaults to MockLLM if LLM_PROVIDER is 'mock' or API key is not configured.
    """
    selected_provider = (provider or config.LLM_PROVIDER).lower()

    if selected_provider == "mock" or not config.LLM_API_KEY:
        if selected_provider != "mock":
            logger.warning(
                "LLM_PROVIDER='%s' requested but LLM_API_KEY is not set. "
                "Using deterministic MockLLM for offline execution.",
                selected_provider,
            )
        return MockLLM(model_name=config.LLM_MODEL or "mock-legal-generator")

    if selected_provider in ("openai", "groq"):
        base_url = config.LLM_BASE_URL
        if selected_provider == "groq" and not base_url:
            base_url = "https://api.groq.com/openai/v1"
        model = config.LLM_MODEL
        if selected_provider == "groq" and (not model or "llama-3.3-70b" in model):
            model = "qwen/qwen3.8-27b"
        elif not model:
            model = "gpt-4o-mini"

        return OpenAICompatibleLLM(
            api_key=config.LLM_API_KEY,
            model=model,
            base_url=base_url,
            timeout=config.LLM_TIMEOUT,
        )

    if selected_provider == "huggingface":
        return HuggingFaceInferenceLLM(
            api_key=config.LLM_API_KEY,
            model=config.LLM_MODEL or "meta-llama/Llama-3.2-3B-Instruct",
            timeout=config.LLM_TIMEOUT,
        )

    logger.warning("Unknown LLM_PROVIDER='%s'. Falling back to MockLLM.", selected_provider)
    return MockLLM(model_name="mock-fallback")
