#!/usr/bin/env python3
"""
Demo script showing raw Ollama API usage and thinking tag stripping.
"""

from ollama_client import MinimalOllamaClient
import json


def demo_raw_api():
    """Demonstrate raw API usage with thinking tag handling."""
    
    client = MinimalOllamaClient()
    
    print("=" * 60)
    print("Ollama Raw API Demo - Minimal Overhead")
    print("=" * 60)
    
    # Example 1: Generate C code with raw mode
    print("\n1. Generating C code (raw mode, no templating):")
    print("-" * 40)
    
    prompt = """Write a C function that reverses a string in place. Only the code:
```c
"""
    
    response_text = ""
    for chunk in client.generate_raw(
        model="qwen2.5-coder:1.5b",
        prompt=prompt,
        raw=True,
        stream=True,
        temperature=0.3,
        max_tokens=500
    ):
        if "response" in chunk:
            response_text += chunk["response"]
    
    # Clean and display
    clean_code = client.strip_thinking_tags(response_text)
    print(clean_code[:500])  # First 500 chars
    
    # Example 2: Bash script generation
    print("\n2. Generating Bash script (raw mode):")
    print("-" * 40)
    
    code = client.generate_code(
        model="qwen2.5-coder:1.5b",
        task="counts the number of lines in all .txt files in current directory",
        language="bash",
        temperature=0.3
    )
    print(code)
    
    # Example 3: Show token usage and timing
    print("\n3. Performance metrics (non-streaming):")
    print("-" * 40)
    
    for response in client.generate_raw(
        model="qwen2.5-coder:1.5b",
        prompt="Write hello world in C",
        raw=True,
        stream=False,
        temperature=0.1
    ):
        if "eval_count" in response:
            print(f"Tokens generated: {response['eval_count']}")
            print(f"Generation time: {response['eval_duration']/1e9:.2f}s")
            print(f"Tokens/sec: {response['eval_count']/(response['eval_duration']/1e9):.1f}")
    
    client.close()


if __name__ == "__main__":
    demo_raw_api()