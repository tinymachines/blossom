#!/usr/bin/env python3
"""
Test harness for evaluating LLM-generated code against task specifications.
Compiles C code, executes programs, and validates output against expected results.
"""

import os
import sys
import yaml
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import time
import json
from datetime import datetime

from ollama_client import MinimalOllamaClient


class TaskHarness:
    """Executes task templates and evaluates generated code."""
    
    def __init__(self, model: str = "qwen2.5-coder:1.5b", ollama_url: str = "http://localhost:11434"):
        self.model = model
        self.client = MinimalOllamaClient(ollama_url)
        self.work_dir = Path(tempfile.mkdtemp(prefix="blossom_"))
        self.results = []
        
    def load_template(self, template_path: Path) -> Dict[str, Any]:
        """Load a task template from YAML file."""
        with open(template_path, 'r') as f:
            return yaml.safe_load(f)
    
    def generate_code(self, template: Dict[str, Any]) -> str:
        """Generate code using the LLM based on template specifications."""
        print(f"Generating {template['language']} code for {template['name']}...")
        
        # Build the full prompt with constraints if specified
        full_prompt = template['prompt']
        
        if 'constraints' in template:
            constraints = template['constraints']
            if 'required_includes' in constraints and template['language'] == 'c':
                includes = ', '.join(constraints['required_includes'])
                full_prompt += f"\nMust include: {includes}"
            if 'forbidden_functions' in constraints:
                forbidden = ', '.join(constraints['forbidden_functions'])
                full_prompt += f"\nDo not use: {forbidden}"
            if 'shebang' in constraints and template['language'] == 'bash':
                full_prompt += f"\nStart with: {constraints['shebang']}"
        
        # Generate code
        code = self.client.generate_code(
            model=self.model,
            task=full_prompt,
            language=template['language'],
            temperature=0.3
        )
        
        return code
    
    def compile_c(self, code: str, template: Dict[str, Any]) -> Optional[Path]:
        """Compile C code and return path to executable."""
        build_config = template.get('build', {})
        
        # Write source file
        source_file = self.work_dir / f"{template['name']}.c"
        with open(source_file, 'w') as f:
            f.write(code)
        
        # Compile
        output_file = self.work_dir / build_config.get('output', template['name'])
        compiler = build_config.get('compiler', 'gcc')
        flags = build_config.get('flags', ['-O2', '-Wall'])
        
        cmd = [compiler] + flags + ['-o', str(output_file), str(source_file)]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                print(f"Compilation failed:\n{result.stderr}")
                return None
            return output_file
        except subprocess.TimeoutExpired:
            print("Compilation timed out")
            return None
        except Exception as e:
            print(f"Compilation error: {e}")
            return None
    
    def prepare_bash(self, code: str, template: Dict[str, Any]) -> Path:
        """Prepare bash script for execution."""
        script_file = self.work_dir / f"{template['name']}.sh"
        
        # Ensure shebang is present
        if not code.startswith('#!'):
            shebang = template.get('constraints', {}).get('shebang', '#!/bin/bash')
            code = f"{shebang}\n{code}"
        
        with open(script_file, 'w') as f:
            f.write(code)
        
        # Make executable
        script_file.chmod(0o755)
        return script_file
    
    def run_test(self, executable: Path, test_case: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        Run a single test case against the executable.
        Returns (passed, actual_output, error_message).
        """
        stdin_data = test_case.get('stdin', '')
        expected_stdout = test_case.get('expected_stdout', '').strip()
        timeout = test_case.get('timeout', 2)
        
        try:
            result = subprocess.run(
                [str(executable)],
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            actual_output = result.stdout.strip()
            
            # Compare outputs
            if actual_output == expected_stdout:
                return True, actual_output, None
            else:
                return False, actual_output, f"Expected:\n{expected_stdout}\nGot:\n{actual_output}"
            
        except subprocess.TimeoutExpired:
            return False, "", f"Test timed out after {timeout} seconds"
        except Exception as e:
            return False, "", f"Runtime error: {e}"
    
    def evaluate_task(self, template_path: Path) -> Dict[str, Any]:
        """
        Complete evaluation pipeline for a single task template.
        """
        template = self.load_template(template_path)
        result = {
            'name': template['name'],
            'language': template['language'],
            'timestamp': datetime.now().isoformat(),
            'model': self.model,
            'tests': []
        }
        
        # Generate code
        start_time = time.time()
        code = self.generate_code(template)
        generation_time = time.time() - start_time
        
        result['generation_time'] = generation_time
        result['generated_code'] = code
        
        # Save generated code
        code_file = self.work_dir / f"{template['name']}_generated.{template['language']}"
        with open(code_file, 'w') as f:
            f.write(code)
        
        # Prepare executable
        if template['language'] == 'c':
            executable = self.compile_c(code, template)
            if not executable:
                result['compilation_failed'] = True
                result['tests'] = [{'name': t['name'], 'passed': False, 'error': 'Compilation failed'} 
                                  for t in template['tests']]
                result['success_rate'] = 0
                return result
        elif template['language'] in ['bash', 'sh']:
            executable = self.prepare_bash(code, template)
        else:
            result['error'] = f"Unsupported language: {template['language']}"
            result['success_rate'] = 0
            return result
        
        # Run tests
        for test_case in template['tests']:
            test_result = {'name': test_case['name']}
            passed, output, error = self.run_test(executable, test_case)
            
            test_result['passed'] = passed
            test_result['output'] = output
            if error:
                test_result['error'] = error
            
            result['tests'].append(test_result)
        
        # Calculate success rate
        total_tests = len(result['tests'])
        passed_tests = sum(1 for t in result['tests'] if t['passed'])
        result['success_rate'] = passed_tests / total_tests if total_tests > 0 else 0
        
        return result
    
    def run_all_templates(self, template_dir: Path) -> List[Dict[str, Any]]:
        """Run all templates in a directory."""
        results = []
        
        for template_path in sorted(template_dir.glob("*.yaml")):
            print(f"\n{'='*60}")
            print(f"Evaluating: {template_path.name}")
            print('='*60)
            
            result = self.evaluate_task(template_path)
            results.append(result)
            
            # Print summary
            print(f"\nResults for {result['name']}:")
            print(f"  Language: {result['language']}")
            print(f"  Generation time: {result['generation_time']:.2f}s")
            print(f"  Success rate: {result['success_rate']*100:.0f}%")
            
            for test in result['tests']:
                status = "✓" if test['passed'] else "✗"
                print(f"  {status} {test['name']}")
                if not test['passed'] and 'error' in test:
                    print(f"    Error: {test['error'][:100]}")
        
        return results
    
    def save_results(self, results: List[Dict[str, Any]], output_file: Path):
        """Save evaluation results to JSON."""
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    
    def cleanup(self):
        """Clean up temporary files."""
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
        self.client.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test harness for LLM code generation")
    parser.add_argument("--model", default="qwen2.5-coder:1.5b", help="Ollama model to use")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama API URL")
    parser.add_argument("--template-dir", default="task-templates", help="Directory with task templates")
    parser.add_argument("--output", default="results.json", help="Output file for results")
    parser.add_argument("--keep-work-dir", action="store_true", help="Keep temporary work directory")
    
    args = parser.parse_args()
    
    # Initialize harness
    harness = TaskHarness(model=args.model, ollama_url=args.ollama_url)
    
    try:
        # Run evaluations
        template_dir = Path(args.template_dir)
        if not template_dir.exists():
            print(f"Template directory not found: {template_dir}")
            sys.exit(1)
        
        results = harness.run_all_templates(template_dir)
        
        # Save results
        harness.save_results(results, Path(args.output))
        
        # Print summary
        print(f"\n{'='*60}")
        print("OVERALL SUMMARY")
        print('='*60)
        
        total_tasks = len(results)
        total_tests = sum(len(r['tests']) for r in results)
        passed_tests = sum(sum(1 for t in r['tests'] if t['passed']) for r in results)
        
        print(f"Tasks evaluated: {total_tasks}")
        print(f"Total tests run: {total_tests}")
        print(f"Tests passed: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
        
        if args.keep_work_dir:
            print(f"\nWork directory kept at: {harness.work_dir}")
        
    finally:
        if not args.keep_work_dir:
            harness.cleanup()


if __name__ == "__main__":
    main()