"""
Ollama client wrapper for interacting with local Ollama API.

Supports both LLM text generation and LLaVA multimodal (image + text) analysis.
"""
import logging
import requests
import base64
import time
from pathlib import Path
from typing import Optional, Dict, Any

import config
from utils import setup_logging

logger = setup_logging(__name__)


# ============================================================================
# OLLAMA CLIENT
# ============================================================================

class OllamaClient:
    """Wrapper for Ollama API interactions."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
        verbose: bool = False,
    ):
        """
        Initialize Ollama client.
        
        Args:
            base_url: Ollama API base URL (default: localhost:11434)
            timeout: Request timeout in seconds
            verbose: Enable verbose logging
        """
        self.base_url = base_url
        self.timeout = timeout
        self.verbose = verbose
        self._connection_tested = False
        self._available = False
    
    
    def is_available(self) -> bool:
        """
        Check if Ollama is running and accessible.
        
        Returns:
            True if Ollama is available, False otherwise
        """
        if self._connection_tested:
            return self._available
        
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            self._available = response.status_code == 200
            self._connection_tested = True
            
            if self._available:
                logger.info("✓ Ollama is available and running")
            else:
                logger.warning("⚠ Ollama returned non-200 status")
            
            return self._available
        
        except requests.exceptions.ConnectionError:
            logger.warning(
                f"⚠ Cannot connect to Ollama at {self.base_url}. "
                "Is Ollama running? (Start with: ollama serve)"
            )
            self._connection_tested = True
            self._available = False
            return False
        except Exception as e:
            logger.warning(f"⚠ Error checking Ollama availability: {str(e)}")
            self._connection_tested = True
            self._available = False
            return False
    
    
    def generate_text(
        self,
        prompt: str,
        model: str = "llama3",
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_retries: int = 3,
    ) -> Optional[str]:
        """
        Generate text using Ollama LLM with retry logic.
        
        Args:
            prompt: Input prompt
            model: Model to use (default: llama3)
            temperature: Creativity (0.0-1.0)
            top_p: Diversity sampling parameter
            max_retries: Maximum retry attempts (default: 3)
            
        Returns:
            Generated text or None if failed after all retries
        """
        if not self.is_available():
            logger.error("❌ Ollama is not available")
            return None
        
        for attempt in range(max_retries):
            try:
                if self.verbose or attempt > 0:
                    logger.debug(f"Generating text with {model}... (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "top_p": top_p,
                        "stream": False,
                    },
                    timeout=self.timeout,
                )
                
                # Retry on 500/502/503 errors
                if response.status_code in [500, 502, 503]:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(
                            f"⚠ Ollama returned {response.status_code}, retrying in {wait_time}s... "
                            f"({attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"❌ Ollama returned {response.status_code} after {max_retries} attempts")
                        return None
                
                response.raise_for_status()
                result = response.json()
                
                text = result.get("response", "").strip()
                if self.verbose:
                    logger.debug(f"Generated {len(text)} characters")
                
                return text if text else None
            
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"⚠ Ollama request timed out, retrying in {wait_time}s... "
                        f"({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Ollama request timed out after {max_retries} attempts")
                    return None
            
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"⚠ Ollama request error: {str(e)[:50]}..., "
                        f"retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Ollama request error after {max_retries} attempts: {str(e)}")
                    return None
            
            except Exception as e:
                logger.error(f"❌ Error generating text: {str(e)}")
                return None
        
        logger.error(f"❌ Failed to generate text after {max_retries} attempts")
        return None
    
    
    def analyze_image(
        self,
        image_path: str,
        prompt: str,
        model: str = "llava",
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> Optional[str]:
        """
        Analyze an image using LLaVA model with retry logic.
        
        Args:
            image_path: Path to image file
            prompt: Analysis prompt
            model: Model to use (default: llava)
            temperature: Creativity level
            max_retries: Maximum retry attempts (default: 3)
            
        Returns:
            Analysis result or None if failed after all retries
        """
        if not self.is_available():
            logger.error("❌ Ollama is not available")
            return None
        
        try:
            image_path_obj = Path(image_path)
            if not image_path_obj.exists():
                logger.error(f"❌ Image file not found: {image_path}")
                return None
            
            # Read and encode image to base64
            with open(image_path_obj, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
        
        except Exception as e:
            logger.error(f"❌ Error reading image: {str(e)}")
            return None
        
        for attempt in range(max_retries):
            try:
                if self.verbose or attempt > 0:
                    logger.debug(f"Analyzing image with {model}... (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "images": [image_data],
                        "temperature": temperature,
                        "stream": False,
                    },
                    timeout=self.timeout,
                )
                
                # Retry on 500/502/503 errors
                if response.status_code in [500, 502, 503]:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(
                            f"⚠ Ollama returned {response.status_code}, retrying in {wait_time}s... "
                            f"({attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"❌ Ollama returned {response.status_code} after {max_retries} attempts")
                        return None
                
                response.raise_for_status()
                result = response.json()
                
                text = result.get("response", "").strip()
                if self.verbose:
                    logger.debug(f"Analysis complete ({len(text)} chars)")
                
                return text if text else None
            
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"⚠ Ollama request timed out, retrying in {wait_time}s... "
                        f"({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Ollama request timed out after {max_retries} attempts")
                    return None
            
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"⚠ Ollama request error: {str(e)[:50]}..., "
                        f"retrying in {wait_time}s... ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Ollama request error after {max_retries} attempts: {str(e)}")
                    return None
            
            except Exception as e:
                logger.error(f"❌ Error analyzing image: {str(e)}")
                return None
        
        logger.error(f"❌ Failed to analyze image after {max_retries} attempts")
        return None
    
    
    def list_models(self) -> Dict[str, Any]:
        """
        List available models.
        
        Returns:
            Dictionary with available models
        """
        if not self.is_available():
            return {"error": "Ollama not available"}
        
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Error listing models: {str(e)}")
            return {"error": str(e)}


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_client_instance: Optional[OllamaClient] = None


def get_ollama_client(
    base_url: str = "http://localhost:11434",
    timeout: int = 120,
) -> OllamaClient:
    """
    Get or create Ollama client singleton.
    
    Args:
        base_url: Ollama API URL
        timeout: Request timeout
        
    Returns:
        OllamaClient instance
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = OllamaClient(base_url=base_url, timeout=timeout)
    return _client_instance


def reset_ollama_client():
    """Reset the singleton client instance."""
    global _client_instance
    _client_instance = None
