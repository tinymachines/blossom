#!/usr/bin/env python3
"""
Example integration showing how LLM-generated handlers could be integrated
with the Zephyr mesh network system.
"""

import subprocess
import tempfile
from pathlib import Path
from ollama_client import MinimalOllamaClient


class HandlerGenerator:
    """Generate Zephyr-compatible message handlers using LLMs."""
    
    def __init__(self, model: str = "qwen2.5-coder:1.5b"):
        self.client = MinimalOllamaClient()
        self.model = model
    
    def generate_stream_handler(self, handler_name: str, description: str) -> str:
        """
        Generate a C-based stream handler that can be compiled and piped.
        """
        prompt = f"""Write a C program for a Zephyr mesh network handler called '{handler_name}'.
{description}

The program should:
1. Read messages from stdin (one per line)
2. Process according to the description
3. Output results to stdout
4. Use line buffering for real-time operation
5. Handle SIGTERM gracefully

Format: Each input line is "TYPE DATA", output should be "HANDLER_OUTPUT DATA"
Only the code:
```c
"""
        
        code = self.client.generate_code(
            model=self.model,
            task=prompt,
            language="c",
            temperature=0.3
        )
        
        return code
    
    def generate_bash_handler(self, handler_name: str, description: str) -> str:
        """
        Generate a bash-based handler for simple text processing.
        """
        prompt = f"""Write a bash script for a Zephyr mesh handler called '{handler_name}'.
{description}

The script should:
1. Read from stdin continuously
2. Process each line according to the description  
3. Output to stdout with line buffering
4. Handle common Linux text processing tools (grep, sed, awk)

Only the code:
```bash
"""
        
        code = self.client.generate_code(
            model=self.model,
            task=prompt,
            language="bash",
            temperature=0.3
        )
        
        return code
    
    def compile_handler(self, code: str, output_path: Path) -> bool:
        """Compile C handler code."""
        with tempfile.NamedTemporaryFile(suffix='.c', delete=False) as f:
            f.write(code.encode())
            source_file = f.name
        
        try:
            result = subprocess.run(
                ['gcc', '-O2', '-o', str(output_path), source_file],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
        finally:
            Path(source_file).unlink(missing_ok=True)
    
    def create_handler_wrapper(self, handler_path: Path, handler_type: str) -> str:
        """
        Create a Python wrapper that integrates with Zephyr's handler system.
        """
        wrapper = f'''#!/usr/bin/env python3
"""
Auto-generated Zephyr handler wrapper.
Bridges between Python handler system and compiled binary handler.
"""

import subprocess
import asyncio
from typing import Optional


class GeneratedHandler:
    """Handler that delegates to compiled binary."""
    
    def __init__(self):
        self.handler_path = "{handler_path}"
        self.handler_type = "{handler_type}"
        self.process = None
    
    async def start(self):
        """Start the handler subprocess."""
        self.process = await asyncio.create_subprocess_exec(
            self.handler_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
    
    async def handle(self, message: dict) -> Optional[str]:
        """Process a message through the handler."""
        if not self.process:
            await self.start()
        
        # Format message for handler
        msg_line = f"{{message.get('type', 'unknown')}} {{message.get('data', '')}}"
        
        # Send to handler and get response
        self.process.stdin.write(msg_line.encode() + b'\\n')
        await self.process.stdin.drain()
        
        # Read response (with timeout)
        try:
            response = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=1.0
            )
            return response.decode().strip()
        except asyncio.TimeoutError:
            return None
    
    async def stop(self):
        """Stop the handler subprocess."""
        if self.process:
            self.process.terminate()
            await self.process.wait()


# Export for Zephyr handler system
handler = GeneratedHandler()
'''
        return wrapper


def demo_handler_generation():
    """Demonstrate generating handlers for Zephyr."""
    
    print("Generating Zephyr Handlers with LLM")
    print("=" * 60)
    
    generator = HandlerGenerator()
    
    # Example 1: Generate a message filter handler
    print("\n1. Generating Message Filter Handler (C)")
    print("-" * 40)
    
    filter_code = generator.generate_stream_handler(
        "priority_filter",
        "Filters messages by priority. Only forwards messages containing 'PRIORITY:HIGH' or 'URGENT'."
    )
    
    print("Generated code preview:")
    print(filter_code[:500])
    
    # Example 2: Generate a statistics handler
    print("\n2. Generating Statistics Handler (Bash)")
    print("-" * 40)
    
    stats_code = generator.generate_bash_handler(
        "message_stats",
        "Counts message types and outputs statistics every 10 messages. Format: 'STATS type1:count1 type2:count2'"
    )
    
    print("Generated code preview:")
    print(stats_code[:500])
    
    # Example 3: Show how to integrate with Zephyr
    print("\n3. Integration with Zephyr")
    print("-" * 40)
    
    handler_dir = Path("/tmp/generated_handlers")
    handler_dir.mkdir(exist_ok=True)
    
    # Compile the C handler
    handler_binary = handler_dir / "priority_filter"
    if generator.compile_handler(filter_code, handler_binary):
        print(f"✓ Compiled handler to: {handler_binary}")
        
        # Generate Python wrapper
        wrapper_code = generator.create_handler_wrapper(handler_binary, "stream_filter")
        wrapper_path = handler_dir / "priority_filter.py"
        wrapper_path.write_text(wrapper_code)
        print(f"✓ Created wrapper at: {wrapper_path}")
    else:
        print("✗ Compilation failed")
    
    generator.client.close()


if __name__ == "__main__":
    demo_handler_generation()