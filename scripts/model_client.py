"""
LLM API client wrapper for Ollama and Anthropic
"""

import os
import asyncio
from typing import Optional
import ollama
from anthropic import AsyncAnthropic
from dotenv import load_dotenv


class ModelClient:
    """Unified client for LLM APIs"""
    
    def __init__(self):
        load_dotenv()
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.ollama_client = ollama.Client(host=self.ollama_host)
        
        # Anthropic for expert model (optional)
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.anthropic = AsyncAnthropic(api_key=api_key)
        else:
            self.anthropic = None
            
    async def generate(
        self, 
        model: str, 
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate completion from model"""
        
        if model.startswith('claude'):
            return await self._generate_anthropic(model, prompt, temperature, max_tokens)
        else:
            return await self._generate_ollama(model, prompt, temperature, max_tokens)
            
    async def _generate_ollama(
        self,
        model: str,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate using Ollama"""
        
        # Run in executor since ollama client is sync
        loop = asyncio.get_event_loop()
        
        def _generate():
            response = self.ollama_client.generate(
                model=model,
                prompt=prompt,
                options={
                    'temperature': temperature or 0.3,
                    'num_predict': max_tokens or 2048,
                    'stop': ['```\n\n', '```\n#', '```\nclass'],  # Stop at end of code block
                }
            )
            return response['response']
            
        return await loop.run_in_executor(None, _generate)
        
    async def _generate_anthropic(
        self,
        model: str,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate using Anthropic (for expert model)"""
        
        if not self.anthropic:
            raise ValueError("Anthropic API key not configured")
            
        response = await self.anthropic.messages.create(
            model=model,
            max_tokens=max_tokens or 4096,
            temperature=temperature or 0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
        
    async def check_model(self, model: str) -> bool:
        """Check if model is available"""
        
        try:
            if model.startswith('claude'):
                return self.anthropic is not None
            else:
                # Check Ollama
                models = self.ollama_client.list()
                return any(m['name'] == model for m in models['models'])
        except:
            return False