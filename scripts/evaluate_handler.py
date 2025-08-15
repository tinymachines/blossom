"""
Handler evaluation system with comprehensive logging
"""

import asyncio
import sys
import traceback
import json
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import ast
from datetime import datetime

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent.parent / 'logs' / f'evaluation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger('HandlerEvaluator')


class HandlerEvaluator:
    """Evaluate generated handlers"""
    
    def __init__(self, verbose=True):
        self.test_timeout = 10
        self.zephyr_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(self.zephyr_root / 'src'))
        self.verbose = verbose
        logger.info(f"Initialized HandlerEvaluator with zephyr_root={self.zephyr_root}")
        logger.debug(f"Test timeout set to {self.test_timeout} seconds")
        
    async def evaluate(self, handler_path: Path, level: int) -> int:
        """Evaluate a handler and return score"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting evaluation of {handler_path} for level {level}")
        logger.info(f"{'='*60}")
        
        scores = {
            'loads': 0,       # 20 points
            'syntax': 0,      # 10 points
            'structure': 0,   # 20 points
            'functionality': 0, # 50 points
        }
        
        if self.verbose:
            print(f"\n🔍 Evaluating: {handler_path.name}")
            print(f"   Level: {level}")
            print(f"   Max possible score: 100")
        
        # Check syntax
        logger.info("\n[STEP 1/4] Checking Python syntax...")
        if self._check_syntax(handler_path):
            scores['syntax'] = 10
            logger.info("✅ Syntax check PASSED (+10 points)")
            if self.verbose:
                print("   ✅ Syntax: Valid (+10 pts)")
        else:
            logger.error("❌ Syntax check FAILED - Cannot continue")
            if self.verbose:
                print("   ❌ Syntax: Invalid - stopping evaluation")
            return 0  # Can't continue without valid syntax
            
        # Check structure
        logger.info("\n[STEP 2/4] Analyzing handler structure...")
        scores['structure'] = self._check_structure(handler_path)
        logger.info(f"Structure analysis complete: {scores['structure']}/20 points")
        if self.verbose:
            print(f"   📋 Structure: {scores['structure']}/20 pts")
        
        # Try to load handler
        logger.info("\n[STEP 3/4] Attempting to load handler...")
        if self._check_loads(handler_path):
            scores['loads'] = 20
            logger.info("✅ Handler loads successfully (+20 points)")
            if self.verbose:
                print("   ✅ Loading: Success (+20 pts)")
        else:
            logger.warning("⚠️ Handler failed to load - returning partial score")
            if self.verbose:
                print("   ❌ Loading: Failed - partial score only")
            # Return partial score
            total = sum(scores.values())
            logger.info(f"\nPartial Score: {total}/100")
            return total
            
        # Run functionality tests
        logger.info("\n[STEP 4/4] Testing handler functionality...")
        scores['functionality'] = await self._test_functionality(handler_path, level)
        logger.info(f"Functionality tests complete: {scores['functionality']}/50 points")
        if self.verbose:
            print(f"   🧪 Functionality: {scores['functionality']}/50 pts")
        
        total = sum(scores.values())
        logger.info(f"\n{'='*60}")
        logger.info(f"FINAL SCORE: {total}/100")
        logger.info(f"Breakdown: Syntax={scores['syntax']}, Structure={scores['structure']}, Loads={scores['loads']}, Functionality={scores['functionality']}")
        logger.info(f"{'='*60}\n")
        
        if self.verbose:
            print(f"\n   📊 TOTAL SCORE: {total}/100")
            if total >= 70:
                print("   🎉 PASSED!")
            else:
                print("   ⚠️ NEEDS IMPROVEMENT")
        
        return total
        
    def _check_syntax(self, handler_path: Path) -> bool:
        """Check if Python syntax is valid"""
        logger.debug(f"Parsing {handler_path} for syntax errors...")
        try:
            with open(handler_path) as f:
                code = f.read()
            logger.debug(f"Read {len(code)} characters from file")
            ast.parse(code)
            logger.debug("AST parsing successful - no syntax errors found")
            return True
        except SyntaxError as e:
            logger.error(f"Syntax error found: {e}")
            logger.debug(f"Error at line {e.lineno}: {e.text}")
            return False
            
    def _check_structure(self, handler_path: Path) -> int:
        """Check handler structure (20 points max)"""
        score = 0
        logger.debug("Analyzing handler structure...")
        
        try:
            with open(handler_path) as f:
                code = f.read()
                
            tree = ast.parse(code)
            logger.debug("AST tree created for structure analysis")
            
            # Check for required imports (5 points)
            imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            logger.debug(f"Found {len(imports)} import statements")
            has_base_import = any(
                imp.module and 'zephyr.handlers.base' in imp.module 
                for imp in imports
            )
            if has_base_import:
                score += 5
                logger.debug("✅ Found required base handler import (+5)")
            else:
                logger.debug("⚠️ Missing zephyr.handlers.base import")
                
            # Check for handler class (5 points)
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            logger.debug(f"Found {len(classes)} class definitions")
            handler_classes = [
                c for c in classes 
                if any(base.id == 'HotHandler' for base in c.bases if isinstance(base, ast.Name))
            ]
            if handler_classes:
                score += 5
                logger.debug(f"✅ Found {len(handler_classes)} handler class(es) inheriting from HotHandler (+5)")
                for hc in handler_classes:
                    logger.debug(f"   - Class: {hc.name}")
            else:
                logger.debug("⚠️ No handler class found inheriting from HotHandler")
                
            # Check for process method (10 points)
            if handler_classes:
                handler_class = handler_classes[0]
                methods = [
                    node for node in handler_class.body 
                    if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef)
                ]
                logger.debug(f"Found {len(methods)} methods in handler class")
                for m in methods:
                    logger.debug(f"   - Method: {m.name} (async={'Async' in type(m).__name__})")
                
                has_process = any(m.name == 'process' for m in methods)
                if has_process:
                    score += 10
                    logger.debug("✅ Found required 'process' method (+10)")
                else:
                    logger.debug("⚠️ Missing 'process' method")
                    
        except Exception as e:
            logger.error(f"Structure check error: {e}")
            logger.debug(traceback.format_exc())
            
        return score
        
    def _check_loads(self, handler_path: Path) -> bool:
        """Check if handler can be loaded"""
        logger.debug(f"Testing if handler can be instantiated...")
        
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
            logger.debug("Running load test script...")
            result = subprocess.run(
                [sys.executable, '-c', test_script],
                capture_output=True,
                text=True,
                timeout=5
            )
            logger.debug(f"Load test stdout: {result.stdout}")
            logger.debug(f"Load test stderr: {result.stderr}")
            
            success = 'SUCCESS' in result.stdout
            if success:
                logger.debug("✅ Handler instantiation successful")
            else:
                logger.warning(f"❌ Handler instantiation failed: {result.stderr}")
            return success
        except subprocess.TimeoutExpired:
            logger.error("Load test timed out after 5 seconds")
            return False
        except Exception as e:
            logger.error(f"Load test error: {e}")
            return False
            
    async def _test_functionality(self, handler_path: Path, level: int) -> int:
        """Test handler functionality based on level"""
        logger.info(f"Running functionality tests for level {level}")
        
        # Get test cases for level
        test_cases = self._get_test_cases(level)
        logger.debug(f"Retrieved {len(test_cases)} test case(s) for level {level}")
        
        # Create test script
        test_script = self._create_test_script(handler_path, test_cases, level)
        
        try:
            # Run test script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_script)
                test_file = f.name
                
            logger.debug(f"Created test script at {test_file}")
            logger.debug("Test script content (first 500 chars):")
            logger.debug(test_script[:500])
                
            logger.debug(f"Executing test script with {self.test_timeout}s timeout...")
            result = await asyncio.create_subprocess_exec(
                sys.executable, test_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                result.communicate(),
                timeout=self.test_timeout
            )
            
            logger.debug(f"Test execution completed")
            logger.debug(f"Test stdout: {stdout.decode()[:500]}")
            if stderr:
                logger.warning(f"Test stderr: {stderr.decode()[:500]}")
            
            # Parse results
            output = stdout.decode()
            if 'SCORE:' in output:
                score_line = [l for l in output.split('\n') if 'SCORE:' in l][0]
                score = int(score_line.split(':')[1].strip())
                final_score = min(score, 50)  # Cap at 50 points
                logger.info(f"Functionality test score: {final_score}/50")
                return final_score
            else:
                logger.warning("No score found in test output")
                return 0
                
        except asyncio.TimeoutError:
            logger.error(f"Functionality test timed out after {self.test_timeout} seconds")
            if self.verbose:
                print(f"   ⚠️ Test timeout ({self.test_timeout}s)")
        except Exception as e:
            logger.error(f"Functionality test error: {e}")
            logger.debug(traceback.format_exc())
            if self.verbose:
                print(f"   ❌ Test error: {e}")
            
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