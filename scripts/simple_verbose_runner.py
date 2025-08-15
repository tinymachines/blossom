#!/usr/bin/env python3
"""
Simple text-only verbose test runner for slower systems
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import click
from dotenv import load_dotenv

# Add parent paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from prompt_optimizer import PromptOptimizer
from evaluate_handler import HandlerEvaluator
from model_client import ModelClient


class SimpleVerboseRunner:
    """Simple text-based verbose test runner"""
    
    def __init__(self, verbose=True):
        load_dotenv()
        self.verbose = verbose
        self.prompt_optimizer = PromptOptimizer()
        self.evaluator = HandlerEvaluator(verbose=True)
        self.model_client = ModelClient(verbose=True)
        self.output_dir = Path(__file__).parent.parent / 'generated'
        self.results_file = Path(__file__).parent.parent / 'evaluation' / 'results.json'
        self.log_file = Path(__file__).parent.parent / 'logs' / f'simple_verbose_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Track statistics
        self.stats = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'total_time': 0,
            'scores': []
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Simple logging to both console and file"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] [{level:>7}] {message}"
        
        # Console output
        print(formatted)
        
        # File output
        with open(self.log_file, 'a') as f:
            f.write(formatted + '\n')
    
    def print_separator(self, char: str = "=", length: int = 80):
        """Print a separator line"""
        line = char * length
        print(line)
        with open(self.log_file, 'a') as f:
            f.write(line + '\n')
    
    async def run_challenge(
        self, 
        model: str, 
        level: int,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Run a single challenge with verbose text output"""
        
        challenge_name = f"level{level}_{self._get_challenge_name(level)}"
        test_start = time.time()
        
        # Header
        self.print_separator("=")
        self.log(f"STARTING CHALLENGE: {challenge_name}", "START")
        self.log(f"Model: {model}", "INFO")
        self.log(f"Level: {level}", "INFO")
        self.log(f"Max Attempts: {max_retries}", "INFO")
        self.print_separator("-")
        
        # Create output directory
        model_dir = self.output_dir / model.replace(':', '_') / challenge_name
        model_dir.mkdir(parents=True, exist_ok=True)
        self.log(f"Output directory: {model_dir}", "DEBUG")
        
        best_score = 0
        best_handler = None
        attempts = []
        
        for attempt in range(max_retries):
            attempt_start = time.time()
            
            print("")  # Empty line for readability
            self.log(f"ATTEMPT {attempt + 1}/{max_retries}", "ATTEMPT")
            self.print_separator("-", 40)
            
            try:
                # Step 1: Generate prompt
                self.log("Creating optimized prompt...", "STEP")
                prompt_start = time.time()
                
                prompt = self.prompt_optimizer.create_prompt(model, challenge_name, level)
                
                prompt_time = time.time() - prompt_start
                self.log(f"Prompt created in {prompt_time:.2f}s", "TIME")
                self.log(f"Prompt length: {len(prompt)} characters", "DEBUG")
                
                if self.verbose:
                    self.log("Prompt preview (first 200 chars):", "DEBUG")
                    preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
                    for line in preview.split('\n'):
                        self.log(f"  > {line}", "DEBUG")
                
                # Step 2: Generate handler code
                print("")
                self.log("Generating handler code from LLM...", "STEP")
                self.log(f"Sending request to {model}...", "INFO")
                
                generation_start = time.time()
                handler_code = await self.model_client.generate(model, prompt)
                generation_time = time.time() - generation_start
                
                self.log(f"Code generated in {generation_time:.2f}s", "TIME")
                
                # Extract code
                handler_code = self._extract_code(handler_code)
                self.log(f"Extracted {len(handler_code)} characters of Python code", "INFO")
                
                if self.verbose:
                    lines = handler_code.split('\n')
                    self.log(f"Code has {len(lines)} lines", "DEBUG")
                    self.log("Code preview (first 10 lines):", "DEBUG")
                    for i, line in enumerate(lines[:10], 1):
                        self.log(f"  {i:3}: {line}", "CODE")
                
                # Step 3: Save handler
                handler_path = model_dir / f'handler_attempt{attempt + 1}.py'
                with open(handler_path, 'w') as f:
                    f.write(handler_code)
                self.log(f"Handler saved to: {handler_path}", "SAVE")
                
                # Step 4: Evaluate handler
                print("")
                self.log("Starting evaluation...", "STEP")
                self.print_separator(".", 40)
                
                eval_start = time.time()
                score = await self.evaluator.evaluate(handler_path, level)
                eval_time = time.time() - eval_start
                
                self.log(f"Evaluation completed in {eval_time:.2f}s", "TIME")
                
                # Record attempt
                attempt_time = time.time() - attempt_start
                attempts.append({
                    'attempt': attempt + 1,
                    'score': score,
                    'time': attempt_time,
                    'path': str(handler_path)
                })
                
                # Display results
                print("")
                self.print_separator("*", 40)
                self.log(f"SCORE: {score}/100", "RESULT")
                
                if score >= 70:
                    self.log("STATUS: PASSED!", "SUCCESS")
                elif score >= 40:
                    self.log("STATUS: PARTIAL", "WARNING")
                else:
                    self.log("STATUS: FAILED", "ERROR")
                
                self.log(f"Attempt time: {attempt_time:.2f}s", "TIME")
                self.print_separator("*", 40)
                
                if score > best_score:
                    best_score = score
                    best_handler = handler_path
                    self.log("New best score!", "INFO")
                
                # Check if we should stop
                if score >= 70:
                    self.log("Challenge passed! Stopping attempts.", "SUCCESS")
                    break
                elif attempt < max_retries - 1:
                    self.log(f"Score below threshold (70). Retrying...", "INFO")
                    
            except Exception as e:
                self.log(f"Error during attempt: {e}", "ERROR")
                if self.verbose:
                    import traceback
                    tb = traceback.format_exc()
                    for line in tb.split('\n'):
                        self.log(f"  {line}", "TRACE")
                
                attempts.append({
                    'attempt': attempt + 1,
                    'score': 0,
                    'error': str(e),
                    'time': time.time() - attempt_start
                })
        
        # Save best handler
        if best_handler:
            final_path = model_dir / 'handler.py'
            with open(best_handler) as f:
                content = f.read()
            with open(final_path, 'w') as f:
                f.write(content)
            self.log(f"Best handler saved to: {final_path}", "SAVE")
        
        # Summary
        total_time = time.time() - test_start
        print("")
        self.print_separator("=", 60)
        self.log("CHALLENGE SUMMARY", "SUMMARY")
        self.print_separator("-", 60)
        self.log(f"Challenge: {challenge_name}", "INFO")
        self.log(f"Best Score: {best_score}/100", "INFO")
        self.log(f"Status: {'PASSED' if best_score >= 70 else 'FAILED'}", "INFO")
        self.log(f"Total Attempts: {len(attempts)}", "INFO")
        self.log(f"Total Time: {total_time:.2f}s", "INFO")
        
        # Show all attempts
        self.log("Attempt Details:", "INFO")
        for att in attempts:
            status = "PASS" if att.get('score', 0) >= 70 else "FAIL"
            time_str = f"{att.get('time', 0):.2f}s"
            score_str = f"{att.get('score', 0):3}/100"
            self.log(f"  Attempt {att['attempt']}: {score_str} - {status} ({time_str})", "INFO")
        
        self.print_separator("=", 60)
        
        # Update stats
        self.stats['total_tests'] += 1
        if best_score >= 70:
            self.stats['passed'] += 1
        else:
            self.stats['failed'] += 1
        self.stats['scores'].append(best_score)
        self.stats['total_time'] += total_time
        
        # Save result
        result = {
            'model': model,
            'challenge': challenge_name,
            'level': level,
            'timestamp': datetime.now().isoformat(),
            'best_score': best_score,
            'passed': best_score >= 70,
            'attempts': attempts,
            'total_time': total_time
        }
        
        self._save_result(result)
        
        return result
    
    def _get_challenge_name(self, level: int) -> str:
        """Get challenge name for level"""
        names = {
            1: 'echo',
            2: 'counter',
            3: 'collector',
            4: 'executor',
            5: 'sync'
        }
        return names.get(level, 'unknown')
    
    def _extract_code(self, response: str) -> str:
        """Extract Python code from model response"""
        if '```python' in response:
            start = response.find('```python') + 9
            end = response.find('```', start)
            if end > start:
                return response[start:end].strip()
        return response.strip()
    
    def _save_result(self, result: Dict[str, Any]):
        """Save result to results file"""
        if self.results_file.exists():
            with open(self.results_file) as f:
                results = json.load(f)
        else:
            results = []
        
        results.append(result)
        
        with open(self.results_file, 'w') as f:
            json.dump(results, f, indent=2)
    
    async def run_all_challenges(self, model: str):
        """Run all challenge levels"""
        
        suite_start = time.time()
        
        self.print_separator("#", 80)
        self.log("STARTING FULL TEST SUITE", "START")
        self.log(f"Model: {model}", "INFO")
        self.log(f"Levels: 1-5", "INFO")
        self.print_separator("#", 80)
        
        results = []
        for level in range(1, 6):
            print(f"\n\n")  # Add spacing between challenges
            result = await self.run_challenge(model, level)
            results.append(result)
            
            # Progress update
            print("")
            self.log(f"Progress: {level}/5 challenges completed", "PROGRESS")
            current_passed = sum(1 for r in results if r['passed'])
            self.log(f"Current Status: {current_passed}/{level} passed", "PROGRESS")
            print("")
        
        # Final summary
        suite_time = time.time() - suite_start
        total_score = sum(r['best_score'] for r in results)
        passed = sum(1 for r in results if r['passed'])
        
        print("\n\n")
        self.print_separator("#", 80)
        self.log("FINAL TEST SUITE RESULTS", "FINAL")
        self.print_separator("#", 80)
        
        self.log(f"Model: {model}", "INFO")
        self.log(f"Total Score: {total_score}/500 ({total_score/5:.1f}%)", "INFO")
        self.log(f"Challenges Passed: {passed}/5", "INFO")
        self.log(f"Total Time: {suite_time:.2f}s", "INFO")
        
        print("")
        self.log("Individual Results:", "INFO")
        for r in results:
            status = "PASS" if r['passed'] else "FAIL"
            self.log(f"  Level {r['level']} ({r['challenge'].split('_')[1]}): {r['best_score']:3}/100 - {status}", "INFO")
        
        # Performance bar (text-based)
        percentage = (total_score / 500) * 100
        bar_length = 50
        filled = int(bar_length * percentage / 100)
        bar = "#" * filled + "-" * (bar_length - filled)
        
        print("")
        self.log(f"Overall Performance: [{bar}] {percentage:.1f}%", "INFO")
        
        self.print_separator("#", 80)
        
        return results
    
    def show_stats(self):
        """Display accumulated statistics"""
        print("\n")
        self.print_separator("=", 60)
        self.log("SESSION STATISTICS", "STATS")
        self.print_separator("-", 60)
        
        self.log(f"Total Tests Run: {self.stats['total_tests']}", "INFO")
        self.log(f"Tests Passed: {self.stats['passed']}", "INFO")
        self.log(f"Tests Failed: {self.stats['failed']}", "INFO")
        
        if self.stats['scores']:
            avg_score = sum(self.stats['scores']) / len(self.stats['scores'])
            self.log(f"Average Score: {avg_score:.1f}/100", "INFO")
            self.log(f"Best Score: {max(self.stats['scores'])}/100", "INFO")
            self.log(f"Worst Score: {min(self.stats['scores'])}/100", "INFO")
        
        if self.stats['total_time'] > 0:
            self.log(f"Total Time: {self.stats['total_time']:.2f}s", "INFO")
            if self.stats['total_tests'] > 0:
                avg_time = self.stats['total_time'] / self.stats['total_tests']
                self.log(f"Average Time per Test: {avg_time:.2f}s", "INFO")
        
        self.log(f"Log file: {self.log_file}", "INFO")
        self.print_separator("=", 60)


@click.command()
@click.option('--model', required=True, help='Model to test (e.g., qwen2.5-coder:1.5b)')
@click.option('--level', type=int, help='Specific challenge level (1-5)')
@click.option('--all-levels', is_flag=True, help='Run all challenge levels')
@click.option('--max-retries', type=int, default=3, help='Maximum retry attempts')
@click.option('--quiet', is_flag=True, help='Less verbose output')
def main(model, level, all_levels, max_retries, quiet):
    """Simple text-based verbose test runner for Blossom"""
    
    print("\n" + "="*80)
    print(" " * 25 + "BLOSSOM SIMPLE VERBOSE RUNNER")
    print(" " * 20 + "Text-only output for slower systems")
    print("="*80 + "\n")
    
    runner = SimpleVerboseRunner(verbose=not quiet)
    
    print(f"Configuration:")
    print(f"  Model: {model}")
    print(f"  Max Retries: {max_retries}")
    print(f"  Verbose: {not quiet}")
    print(f"  Log File: {runner.log_file}")
    print("")
    
    try:
        if all_levels or not level:
            asyncio.run(runner.run_all_challenges(model))
        else:
            asyncio.run(runner.run_challenge(model, level, max_retries))
        
        # Show final stats
        runner.show_stats()
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        runner.log("Test interrupted by user", "WARNING")
        runner.show_stats()
    
    except Exception as e:
        print(f"\nFatal error: {e}")
        runner.log(f"Fatal error: {e}", "ERROR")
        import traceback
        runner.log(traceback.format_exc(), "TRACE")
    
    print(f"\n✓ Test run completed")
    print(f"✓ Full logs saved to: {runner.log_file}\n")


if __name__ == '__main__':
    main()