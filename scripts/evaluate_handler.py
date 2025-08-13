"""
Handler evaluation system
"""

import asyncio
import sys
import traceback
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import ast


class HandlerEvaluator:
    """Evaluate generated handlers"""
    
    def __init__(self):
        self.test_timeout = 10
        self.zephyr_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(self.zephyr_root / 'src'))
        
    async def evaluate(self, handler_path: Path, level: int) -> int:
        """Evaluate a handler and return score"""
        
        scores = {
            'loads': 0,       # 20 points
            'syntax': 0,      # 10 points
            'structure': 0,   # 20 points
            'functionality': 0, # 50 points
        }
        
        # Check syntax
        if self._check_syntax(handler_path):
            scores['syntax'] = 10
        else:
            return 0  # Can't continue without valid syntax
            
        # Check structure
        scores['structure'] = self._check_structure(handler_path)
        
        # Try to load handler
        if self._check_loads(handler_path):
            scores['loads'] = 20
        else:
            # Return partial score
            return sum(scores.values())
            
        # Run functionality tests
        scores['functionality'] = await self._test_functionality(handler_path, level)
        
        return sum(scores.values())
        
    def _check_syntax(self, handler_path: Path) -> bool:
        """Check if Python syntax is valid"""
        try:
            with open(handler_path) as f:
                code = f.read()
            ast.parse(code)
            return True
        except SyntaxError:
            return False
            
    def _check_structure(self, handler_path: Path) -> int:
        """Check handler structure (20 points max)"""
        score = 0
        
        try:
            with open(handler_path) as f:
                code = f.read()
                
            tree = ast.parse(code)
            
            # Check for required imports (5 points)
            imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            has_base_import = any(
                imp.module and 'zephyr.handlers.base' in imp.module 
                for imp in imports
            )
            if has_base_import:
                score += 5
                
            # Check for handler class (5 points)
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            handler_classes = [
                c for c in classes 
                if any(base.id == 'HotHandler' for base in c.bases if isinstance(base, ast.Name))
            ]
            if handler_classes:
                score += 5
                
            # Check for process method (10 points)
            if handler_classes:
                handler_class = handler_classes[0]
                methods = [
                    node for node in handler_class.body 
                    if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef)
                ]
                has_process = any(m.name == 'process' for m in methods)
                if has_process:
                    score += 10
                    
        except Exception as e:
            print(f"Structure check error: {e}")
            
        return score
        
    def _check_loads(self, handler_path: Path) -> bool:
        """Check if handler can be loaded"""
        
        # Create a test script
        test_script = f"""
import sys
sys.path.insert(0, '{self.zephyr_root / "src"}')

# Mock node
class MockNode:
    def __init__(self):
        self.name = 'TestNode'
        self.machine_id = 'test-123'

# Try to load handler
try:
    with open('{handler_path}') as f:
        code = f.read()
    
    # Execute handler code
    namespace = {{'__name__': '__main__'}}
    exec(code, namespace)
    
    # Find handler class
    for name, obj in namespace.items():
        if isinstance(obj, type) and name.endswith('Handler'):
            # Try to instantiate
            handler = obj(MockNode())
            print("SUCCESS")
            break
except Exception as e:
    print(f"FAILED: {{e}}")
"""
        
        try:
            result = subprocess.run(
                [sys.executable, '-c', test_script],
                capture_output=True,
                text=True,
                timeout=5
            )
            return 'SUCCESS' in result.stdout
        except:
            return False
            
    async def _test_functionality(self, handler_path: Path, level: int) -> int:
        """Test handler functionality based on level"""
        
        # Get test cases for level
        test_cases = self._get_test_cases(level)
        
        # Create test script
        test_script = self._create_test_script(handler_path, test_cases, level)
        
        try:
            # Run test script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_script)
                test_file = f.name
                
            result = await asyncio.create_subprocess_exec(
                sys.executable, test_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                result.communicate(),
                timeout=self.test_timeout
            )
            
            # Parse results
            output = stdout.decode()
            if 'SCORE:' in output:
                score_line = [l for l in output.split('\n') if 'SCORE:' in l][0]
                score = int(score_line.split(':')[1].strip())
                return min(score, 50)  # Cap at 50 points
                
        except asyncio.TimeoutError:
            print("Test timeout")
        except Exception as e:
            print(f"Test error: {e}")
            
        finally:
            # Clean up
            if 'test_file' in locals():
                Path(test_file).unlink(missing_ok=True)
                
        return 0
        
    def _get_test_cases(self, level: int) -> List[Dict[str, Any]]:
        """Get test cases for level"""
        
        if level == 1:  # Echo handler
            return [
                {
                    'input': {'type': 'echo', 'payload': 'Hello', 'from': 'test123'},
                    'expected_type': 'echo_response',
                    'check_payload': lambda p: 'ECHO:' in str(p) and 'Hello' in str(p)
                }
            ]
        elif level == 2:  # Counter handler
            return [
                {
                    'sequence': [
                        {'type': 'chat', 'payload': 'msg1'},
                        {'type': 'chat', 'payload': 'msg2'},
                        {'type': 'stats', 'payload': 'request'}
                    ],
                    'expected_final_type': 'stats_response',
                    'check_final': lambda p: p.get('total_messages', 0) >= 3
                }
            ]
        # Add more test cases for other levels
        
        return []
        
    def _create_test_script(self, handler_path: Path, test_cases: List, level: int) -> str:
        """Create test script for handler"""
        
        return f"""
import asyncio
import sys
sys.path.insert(0, '{self.zephyr_root / "src"}')

class MockNode:
    def __init__(self):
        self.name = 'TestNode'
        self.machine_id = 'test-123'
        
    async def broadcast(self, msg):
        pass

async def test_handler():
    score = 0
    
    # Load handler
    with open('{handler_path}') as f:
        code = f.read()
    
    namespace = {{'__name__': '__main__'}}
    exec(code, namespace)
    
    # Find and instantiate handler
    handler = None
    for name, obj in namespace.items():
        if isinstance(obj, type) and name.endswith('Handler'):
            handler = obj(MockNode())
            break
    
    if not handler:
        print("SCORE: 0")
        return
        
    # Activate if needed
    if hasattr(handler, 'activate'):
        await handler.activate()
        score += 10
    
    # Run level-specific tests
    if {level} == 1:
        # Test echo
        msg = {{'type': 'echo', 'payload': 'Hello', 'from': 'test123'}}
        result = await handler.process(msg)
        if result and result.get('type') == 'echo_response':
            score += 20
        if result and 'ECHO:' in str(result.get('payload', '')):
            score += 20
            
    print(f"SCORE: {{score}}")

asyncio.run(test_handler())
"""