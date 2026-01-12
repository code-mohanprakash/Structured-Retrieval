"""
LLM Provider Abstraction Layer

Supports multiple LLM providers with unified interface:
- Groq (Llama 3.3, Mixtral) - primary
- Google (Gemini) - fallback
- OpenAI (GPT-4o, GPT-4o-mini) - optional
- Anthropic (Claude 3.5 Sonnet) - optional
- Ollama (local models) - optional

Features:
- Retry logic with exponential backoff
- Token counting and rate limiting
- Error handling and graceful degradation
- Streaming support
"""

import os
import time
import json
import logging
from typing import Optional, Dict, Any, List, Generator
from dataclasses import dataclass
from enum import Enum

import tiktoken
from openai import OpenAI, OpenAIError, RateLimitError
from anthropic import Anthropic, AnthropicError

logger = logging.getLogger(__name__)

# Try to import Google AI, graceful fallback if not installed
try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("google-generativeai not installed. Google/Gemini support disabled.")


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GROQ = "groq"
    GOOGLE = "google"


@dataclass
class LLMConfig:
    """Configuration for LLM provider"""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For Ollama
    temperature: float = 0.1  # Low temp for structured outputs
    max_tokens: int = 4096
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0  # Base delay in seconds


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    provider: LLMProvider
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    error: Optional[str] = None


class LLMProviderWrapper:
    """
    Unified interface for multiple LLM providers
    
    Usage:
        >>> config = LLMConfig(
        ...     provider=LLMProvider.OPENAI,
        ...     model="gpt-4o",
        ...     api_key=os.getenv("OPENAI_API_KEY")
        ... )
        >>> provider = LLMProviderWrapper(config)
        >>> response = provider.complete(
        ...     system_prompt="You are a helpful assistant",
        ...     user_prompt="Extract entities from this text"
        ... )
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = None
        self._initialize_client()
        
        # Token encoder for OpenAI models
        try:
            self.encoder = tiktoken.encoding_for_model(config.model)
        except KeyError:
            # Fallback to cl100k_base (GPT-4 encoding)
            self.encoder = tiktoken.get_encoding("cl100k_base")
    
    def _initialize_client(self):
        """Initialize the LLM client based on provider"""
        if self.config.provider == LLMProvider.OPENAI:
            if not self.config.api_key:
                self.config.api_key = os.getenv("OPENAI_API_KEY")
            if not self.config.api_key:
                raise ValueError("OPENAI_API_KEY not found in config or environment")
            self.client = OpenAI(
                api_key=self.config.api_key,
                timeout=self.config.timeout
            )
        
        elif self.config.provider == LLMProvider.ANTHROPIC:
            if not self.config.api_key:
                self.config.api_key = os.getenv("ANTHROPIC_API_KEY")
            if not self.config.api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in config or environment")
            self.client = Anthropic(
                api_key=self.config.api_key,
                timeout=self.config.timeout
            )
        
        elif self.config.provider == LLMProvider.GROQ:
            # Groq uses OpenAI-compatible API
            if not self.config.api_key:
                self.config.api_key = os.getenv("GROQ_API_KEY")
            if not self.config.api_key:
                raise ValueError("GROQ_API_KEY not found in config or environment")
            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url="https://api.groq.com/openai/v1",
                timeout=self.config.timeout
            )
        
        elif self.config.provider == LLMProvider.GOOGLE:
            if not GOOGLE_AVAILABLE:
                raise ValueError("google-generativeai package not installed. Run: pip install google-generativeai")
            if not self.config.api_key:
                self.config.api_key = os.getenv("GOOGLE_API_KEY")
            if not self.config.api_key:
                raise ValueError("GOOGLE_API_KEY not found in config or environment")
            genai.configure(api_key=self.config.api_key)
            self.client = genai.GenerativeModel(self.config.model)
        
        elif self.config.provider == LLMProvider.OLLAMA:
            # Ollama uses OpenAI-compatible API
            base_url = self.config.base_url or "http://localhost:11434/v1"
            self.client = OpenAI(
                base_url=base_url,
                api_key="ollama",  # Dummy key, not validated
                timeout=self.config.timeout
            )
        
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        return len(self.encoder.encode(text))
    
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Complete a prompt with retry logic
        
        Args:
            system_prompt: System/instruction prompt
            user_prompt: User query/task
            json_mode: Force JSON output (OpenAI only)
            temperature: Override default temperature
            max_tokens: Override default max_tokens
        
        Returns:
            LLMResponse with content and metadata
        """
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens
        
        start_time = time.time()
        
        for attempt in range(self.config.max_retries):
            try:
                if self.config.provider == LLMProvider.OPENAI or self.config.provider == LLMProvider.OLLAMA or self.config.provider == LLMProvider.GROQ:
                    response = self._complete_openai(
                        system_prompt, user_prompt, json_mode, temp, max_tok
                    )
                elif self.config.provider == LLMProvider.ANTHROPIC:
                    response = self._complete_anthropic(
                        system_prompt, user_prompt, temp, max_tok
                    )
                elif self.config.provider == LLMProvider.GOOGLE:
                    response = self._complete_google(
                        system_prompt, user_prompt, json_mode, temp, max_tok
                    )
                else:
                    raise ValueError(f"Unsupported provider: {self.config.provider}")
                
                latency_ms = (time.time() - start_time) * 1000
                response.latency_ms = latency_ms
                
                logger.info(
                    f"LLM completion successful: {response.model}, "
                    f"{response.total_tokens} tokens, {latency_ms:.0f}ms"
                )
                
                return response
            
            except (RateLimitError, AnthropicError) as e:
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/{self.config.max_retries}), "
                        f"retrying in {delay}s: {str(e)}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"LLM completion failed after {self.config.max_retries} attempts: {str(e)}")
                    return LLMResponse(
                        content="",
                        model=self.config.model,
                        provider=self.config.provider,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        latency_ms=(time.time() - start_time) * 1000,
                        error=str(e)
                    )
            
            except Exception as e:
                logger.error(f"Unexpected error in LLM completion: {str(e)}")
                return LLMResponse(
                    content="",
                    model=self.config.model,
                    provider=self.config.provider,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=(time.time() - start_time) * 1000,
                    error=str(e)
                )
    
    def _complete_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Complete using OpenAI API"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if json_mode and self.config.provider == LLMProvider.OPENAI:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(**kwargs)
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider=self.config.provider,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            latency_ms=0  # Set by caller
        )
    
    def _complete_google(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Complete using Google Gemini API"""
        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        if json_mode:
            full_prompt += "\n\nRespond with valid JSON only."
        
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        # Extract token counts (Google provides these differently)
        prompt_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0
        completion_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0
        
        return LLMResponse(
            content=response.text,
            model=self.config.model,
            provider=LLMProvider.GOOGLE,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=0  # Set by caller
        )
    
    def _complete_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Complete using Anthropic API"""
        response = self.client.messages.create(
            model=self.config.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Anthropic returns token counts differently
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            provider=self.config.provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=0  # Set by caller
        )
    
    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Complete and parse JSON response
        
        Returns:
            Parsed JSON dict, or empty dict on error
        """
        response = self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
            temperature=temperature
        )
        
        if response.error:
            logger.error(f"LLM error: {response.error}")
            return {}
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}\nContent: {response.content}")
            return {}


# Global provider instances (lazy initialization)
_openai_provider: Optional[LLMProviderWrapper] = None
_anthropic_provider: Optional[LLMProviderWrapper] = None
_groq_provider: Optional[LLMProviderWrapper] = None
_google_provider: Optional[LLMProviderWrapper] = None


def get_groq_provider() -> LLMProviderWrapper:
    """Get or create Groq provider instance"""
    global _groq_provider
    if _groq_provider is None:
        config = LLMConfig(
            provider=LLMProvider.GROQ,
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0.1,
            max_tokens=4096
        )
        _groq_provider = LLMProviderWrapper(config)
    return _groq_provider


def get_google_provider() -> LLMProviderWrapper:
    """Get or create Google Gemini provider instance"""
    global _google_provider
    if _google_provider is None:
        config = LLMConfig(
            provider=LLMProvider.GOOGLE,
            model=os.getenv("GOOGLE_MODEL", "gemini-1.5-flash"),
            temperature=0.1,
            max_tokens=4096
        )
        _google_provider = LLMProviderWrapper(config)
    return _google_provider


def get_openai_provider() -> LLMProviderWrapper:
    """Get or create OpenAI provider instance"""
    global _openai_provider
    if _openai_provider is None:
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=0.1,
            max_tokens=4096
        )
        _openai_provider = LLMProviderWrapper(config)
    return _openai_provider


def get_anthropic_provider() -> LLMProviderWrapper:
    """Get or create Anthropic provider instance (fallback)"""
    global _anthropic_provider
    if _anthropic_provider is None:
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            temperature=0.1,
            max_tokens=4096
        )
        _anthropic_provider = LLMProviderWrapper(config)
    return _anthropic_provider


def complete_with_fallback(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False
) -> LLMResponse:
    """
    Complete using Google Gemini (single provider)
    
    Args:
        system_prompt: System instruction
        user_prompt: User query
        json_mode: Force JSON output
    
    Returns:
        LLMResponse from Google provider
    """
    # Get provider preference from env (default: google)
    preferred_provider = os.getenv("LLM_PROVIDER", "google").lower()
    
    # Only use Google provider
    if not os.getenv("GOOGLE_API_KEY"):
        error_msg = "GOOGLE_API_KEY not configured. Please set it in .env file"
        logger.error(error_msg)
        return LLMResponse(
            content="",
            model="unknown",
            provider=LLMProvider.GOOGLE,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=0,
            error=error_msg
        )
    
    # Use Google provider
    try:
        provider = get_google_provider()
        response = provider.complete(system_prompt, user_prompt, json_mode)
        if not response.error:
            logger.info(f"Successfully used Google Gemini")
            return response
        
        error_msg = f"Google Gemini failed: {response.error}"
        logger.error(error_msg)
        return LLMResponse(
            content="",
            model="unknown",
            provider=LLMProvider.GOOGLE,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=0,
            error=error_msg
        )
    except Exception as e:
        error_msg = f"Google provider failed: {str(e)}"
        logger.error(error_msg)
        return LLMResponse(
            content="",
            model="unknown",
            provider=LLMProvider.GOOGLE,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=0,
            error=error_msg
        )
