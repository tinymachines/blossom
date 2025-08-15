"""
LLM API client wrapper for Ollama and Anthropic with detailed logging
"""

import os
import asyncio
import logging
import time
import json
from typing import Optional, Dict, Any
import ollama
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ModelClient')


class ModelClient:
    """Unified client for LLM APIs with comprehensive logging"""
    
    def __init__(self, verbose=True):
        load_dotenv()
        self.verbose = verbose
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.ollama_client = ollama.Client(host=self.ollama_host)
        
        logger.info(f"Initializing ModelClient")
        logger.debug(f"Ollama host: {self.ollama_host}")
        
        # Track generation statistics
        self.stats = {
            'total_generations': 0,
            'total_tokens': 0,
            'total_time': 0,
            'models_used': {}
        }
        
        # Anthropic for expert model (optional)
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.anthropic = AsyncAnthropic(api_key=api_key)
            logger.info("Anthropic client initialized")
        else:
            self.anthropic = None
            logger.debug("No Anthropic API key found")
            
    async def generate(
        self, 
        model: str, 
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate completion from model with detailed logging"""
        
        start_time = time.time()
        self.stats['total_generations'] += 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Generation Request #{self.stats['total_generations']}")
        logger.info(f"Model: {model}")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        logger.debug(f"Temperature: {temperature or 'default'}")
        logger.debug(f"Max tokens: {max_tokens or 'default'}")
        
        if self.verbose:
            logger.debug(f"First 200 chars of prompt: {prompt[:200]}...")
        
        try:
            if model.startswith('claude'):
                response = await self._generate_anthropic(model, prompt, temperature, max_tokens)
            else:
                response = await self._generate_ollama(model, prompt, temperature, max_tokens)
            
            elapsed = time.time() - start_time
            self.stats['total_time'] += elapsed
            self.stats['total_tokens'] += len(response.split())
            
            if model not in self.stats['models_used']:
                self.stats['models_used'][model] = {'count': 0, 'total_time': 0}
            self.stats['models_used'][model]['count'] += 1
            self.stats['models_used'][model]['total_time'] += elapsed
            
            logger.info(f"Generation completed in {elapsed:.2f}s")
            logger.debug(f"Response length: {len(response)} characters, ~{len(response.split())} tokens")
            
            if self.verbose:
                logger.debug(f"First 200 chars of response: {response[:200]}...")
            
            logger.info(f"{'='*60}\n")
            
            return response
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Generation failed after {elapsed:.2f}s: {e}")
            logger.debug(f"Error details:", exc_info=True)
            raise
            
    async def _generate_ollama(
        self,
        model: str,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate using Ollama with detailed logging"""
        
        logger.debug(f"Using Ollama backend for {model}")
        
        # Run in executor since ollama client is sync
        loop = asyncio.get_event_loop()
        
        def _generate():
            generation_start = time.time()
            logger.debug(f"Sending request to Ollama at {self.ollama_host}")
            
            options = {
                'temperature': temperature or 0.3,
                'num_predict': max_tokens or 2048,
                'stop': ['```\n\n', '```\n#', '```\nclass'],  # Stop at end of code block
            }
            
            logger.debug(f"Generation options: {json.dumps(options, indent=2)}")
            
            try:
                response = self.ollama_client.generate(
                    model=model,
                    prompt=prompt,
                    options=options
                )
            except Exception as e:
                if "pull" in str(e).lower() or "not found" in str(e).lower():
                    logger.warning(f"Model {model} not found locally. Attempting to pull it...")
                    # Try to pull the model first
                    try:
                        self.ollama_client.pull(model)
                        logger.info(f"Successfully pulled model {model}")
                        # Retry generation after pull
                        response = self.ollama_client.generate(
                            model=model,
                            prompt=prompt,
                            options=options
                        )
                    except Exception as pull_error:
                        logger.error(f"Failed to pull model {model}: {pull_error}")
                        raise
                else:
                    raise
            
            generation_time = time.time() - generation_start
            
            # Log response metadata if available
            if isinstance(response, dict):
                logger.debug(f"Ollama response metadata:")
                for key in ['total_duration', 'load_duration', 'eval_count', 'eval_duration']:
                    if key in response:
                        logger.debug(f"  {key}: {response[key]}")
                
                if 'eval_count' in response and 'eval_duration' in response:
                    tokens_per_sec = response['eval_count'] / (response['eval_duration'] / 1e9)
                    logger.info(f"Generation speed: {tokens_per_sec:.1f} tokens/sec")
            
            logger.debug(f"Ollama generation completed in {generation_time:.2f}s")
            return response['response']
            
        return await loop.run_in_executor(None, _generate)
        
    async def _generate_anthropic(
        self,
        model: str,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate using Anthropic with detailed logging"""
        
        logger.debug(f"Using Anthropic backend for {model}")
        
        if not self.anthropic:
            logger.error("Anthropic API key not configured")
            raise ValueError("Anthropic API key not configured")
        
        generation_start = time.time()
        logger.debug(f"Sending request to Anthropic API")
        
        params = {
            'model': model,
            'max_tokens': max_tokens or 4096,
            'temperature': temperature or 0.3,
        }
        logger.debug(f"Generation parameters: {json.dumps(params, indent=2)}")
            
        response = await self.anthropic.messages.create(
            **params,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        generation_time = time.time() - generation_start
        
        # Log response metadata
        logger.debug(f"Anthropic response metadata:")
        logger.debug(f"  Model: {response.model}")
        logger.debug(f"  Usage: {response.usage}")
        logger.debug(f"  Stop reason: {response.stop_reason}")
        
        if response.usage:
            logger.info(f"Token usage - Input: {response.usage.input_tokens}, Output: {response.usage.output_tokens}")
        
        logger.debug(f"Anthropic generation completed in {generation_time:.2f}s")
        
        return response.content[0].text
        
    async def check_model(self, model: str) -> bool:
        """Check if model is available with logging"""
        
        logger.debug(f"Checking availability of model: {model}")
        
        try:
            if model.startswith('claude'):
                available = self.anthropic is not None
                logger.debug(f"Anthropic model {model}: {'available' if available else 'not configured'}")
                return available
            else:
                # Check Ollama
                logger.debug(f"Querying Ollama for available models...")
                models = self.ollama_client.list()
                available_models = [m['name'] for m in models['models']]
                logger.debug(f"Available Ollama models: {available_models}")
                
                available = any(m['name'] == model for m in models['models'])
                if not available:
                    logger.warning(f"Model {model} not found in Ollama, but will attempt to use it anyway (may auto-pull)")
                    return True  # Allow attempting to use any model - Ollama may auto-pull it
                logger.debug(f"Model {model}: found")
                return available
        except Exception as e:
            logger.warning(f"Could not check model availability: {e}, assuming model is available")
            return True  # Be permissive on errors
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics"""
        stats = self.stats.copy()
        
        if stats['total_generations'] > 0:
            stats['avg_time'] = stats['total_time'] / stats['total_generations']
            stats['avg_tokens'] = stats['total_tokens'] / stats['total_generations']
        
        logger.info("Generation Statistics:")
        logger.info(f"  Total generations: {stats['total_generations']}")
        logger.info(f"  Total time: {stats['total_time']:.2f}s")
        logger.info(f"  Average time: {stats.get('avg_time', 0):.2f}s")
        logger.info(f"  Total tokens: {stats['total_tokens']}")
        
        for model, model_stats in stats['models_used'].items():
            avg = model_stats['total_time'] / model_stats['count']
            logger.info(f"  {model}: {model_stats['count']} generations, avg {avg:.2f}s")
        
        return stats