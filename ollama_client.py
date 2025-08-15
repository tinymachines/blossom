#!/usr/bin/env python3
"""
Minimal Ollama API client using raw HTTP requests.
Bypasses the official library to reduce overhead and gain direct control.
"""

import json
import re
from typing import Optional, Dict, Any, Generator
import requests


class MinimalOllamaClient:
    """Lightweight Ollama client focused on raw API access."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def generate_raw(
        self,
        model: str,
        prompt: str,
        raw: bool = True,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        think: bool = False,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Generate completion using raw mode to bypass templating.
        
        Args:
            model: Model name (e.g., "llama3.2", "qwen2.5-coder")
            prompt: Raw prompt without any templating
            raw: Use raw mode to bypass Ollama's templating
            stream: Stream responses as they're generated
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            think: Enable thinking mode for models that support it
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "raw": raw,
            "stream": stream,
            "options": {
                "temperature": temperature,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
            
        if think:
            payload["think"] = True
            
        # Add any additional options
        payload["options"].update(kwargs)
        
        response = self.session.post(
            f"{self.base_url}/api/generate",
            json=payload,
            stream=stream
        )
        response.raise_for_status()
        
        if stream:
            for line in response.iter_lines():
                if line:
                    yield json.loads(line)
        else:
            yield response.json()
    
    def chat_raw(
        self,
        model: str,
        messages: list,
        raw: bool = True,
        stream: bool = False,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Chat completion using raw mode.
        """
        payload = {
            "model": model,
            "messages": messages,
            "raw": raw,
            "stream": stream,
            "options": kwargs
        }
        
        response = self.session.post(
            f"{self.base_url}/api/chat",
            json=payload,
            stream=stream
        )
        response.raise_for_status()
        
        if stream:
            for line in response.iter_lines():
                if line:
                    yield json.loads(line)
        else:
            yield response.json()
    
    @staticmethod
    def strip_thinking_tags(text: str) -> str:
        """
        Remove common thinking/thought tags from model output.
        Handles various formats: <thinking>, <thought>, <|thinking|>, etc.
        """
        # Common thinking tag patterns
        patterns = [
            r'<thinking>.*?</thinking>',
            r'<thought>.*?</thought>',
            r'<\|thinking\|>.*?<\|/thinking\|>',
            r'<\|thought\|>.*?<\|/thought\|>',
            r'<think>.*?</think>',
            # Also handle unclosed tags at the end
            r'<thinking>.*$',
            r'<thought>.*$',
        ]
        
        result = text
        for pattern in patterns:
            result = re.sub(pattern, '', result, flags=re.DOTALL)
        
        return result.strip()
    
    def generate_code(
        self,
        model: str,
        task: str,
        language: str = "c",
        raw: bool = True,
        temperature: float = 0.3
    ) -> str:
        """
        Generate code for a specific task, stripping thinking tags.
        
        Args:
            model: Model to use
            task: Task description
            language: Target language (c, bash, etc.)
        """
        # Craft a minimal, direct prompt
        if language.lower() == "c":
            prompt = f"Write a C program that {task}. Output only the code, no explanation.\n```c\n"
        elif language.lower() in ["bash", "sh"]:
            prompt = f"Write a bash script that {task}. Output only the code, no explanation.\n```bash\n"
        else:
            prompt = f"Write {language} code that {task}. Output only the code.\n```{language}\n"
        
        # Get the full response
        response_text = ""
        for chunk in self.generate_raw(
            model=model,
            prompt=prompt,
            raw=raw,
            stream=True,
            temperature=temperature,
            max_tokens=2048
        ):
            if "response" in chunk:
                response_text += chunk["response"]
        
        # Strip thinking tags
        clean_text = self.strip_thinking_tags(response_text)
        
        # Extract code from markdown blocks
        code_pattern = rf'```(?:{language}|c|bash|sh)?\n?(.*?)```'
        matches = re.findall(code_pattern, clean_text, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks, return cleaned text
        return clean_text.strip()
    
    def close(self):
        """Close the session."""
        self.session.close()