#!/usr/bin/env python3
"""
Main test runner for Blossom LLM handler generation
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import click
import ollama
from dotenv import load_dotenv

# Add parent paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from prompt_optimizer import PromptOptimizer
from evaluate_handler import HandlerEvaluator
from model_client import ModelClient


class ChallengeRunner:
    """Run handler generation challenges"""
    
    def __init__(self):
        load_dotenv()
        self.prompt_optimizer = PromptOptimizer()
        self.evaluator = HandlerEvaluator()
        self.model_client = ModelClient()
        self.output_dir = Path(__file__).parent.parent / 'generated'
        self.results_file = Path(__file__).parent.parent / 'evaluation' / 'results.json'
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        
    async def run_challenge(
        self, 
        model: str, 
        level: int,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Run a single challenge for a model"""
        
        challenge_name = f"level{level}_{self._get_challenge_name(level)}"
        print(f"\n🚀 Running {challenge_name} for {model}")
        
        # Create output directory for this model/challenge
        model_dir = self.output_dir / model.replace(':', '_') / challenge_name
        model_dir.mkdir(parents=True, exist_ok=True)
        
        best_score = 0
        best_handler = None
        attempts = []
        
        for attempt in range(max_retries):
            print(f"\n  Attempt {attempt + 1}/{max_retries}")
            
            try:
                # Generate prompt
                prompt = self.prompt_optimizer.create_prompt(model, challenge_name, level)
                
                # Generate handler code
                print(f"  📝 Generating handler...")
                handler_code = await self.model_client.generate(model, prompt)
                
                # Extract code from response
                handler_code = self._extract_code(handler_code)
                
                # Save generated handler
                handler_path = model_dir / f'handler_attempt{attempt + 1}.py'
                with open(handler_path, 'w') as f:
                    f.write(handler_code)
                print(f"  💾 Saved to {handler_path}")
                
                # Evaluate handler
                print(f"  🧪 Evaluating handler...")
                score = await self.evaluator.evaluate(handler_path, level)
                
                attempts.append({
                    'attempt': attempt + 1,
                    'score': score,
                    'path': str(handler_path)
                })
                
                print(f"  📊 Score: {score}/100")
                
                if score > best_score:
                    best_score = score
                    best_handler = handler_path
                    
                # If we got a good score, stop retrying
                if score >= 70:
                    print(f"  ✅ Passed with score {score}!")
                    break
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                attempts.append({
                    'attempt': attempt + 1,
                    'score': 0,
                    'error': str(e)
                })
                
        # Save best handler as main
        if best_handler:
            final_path = model_dir / 'handler.py'
            with open(best_handler) as f:
                content = f.read()
            with open(final_path, 'w') as f:
                f.write(content)
                
        # Record results
        result = {
            'model': model,
            'challenge': challenge_name,
            'level': level,
            'timestamp': datetime.now().isoformat(),
            'best_score': best_score,
            'passed': best_score >= 70,
            'attempts': attempts,
            'final_handler': str(final_path) if best_handler else None
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
        
        # Look for code blocks
        if '```python' in response:
            start = response.find('```python') + 9
            end = response.find('```', start)
            if end > start:
                return response[start:end].strip()
                
        # If no code blocks, assume entire response is code
        return response.strip()
        
    def _save_result(self, result: Dict[str, Any]):
        """Save result to results file"""
        
        # Load existing results
        if self.results_file.exists():
            with open(self.results_file) as f:
                results = json.load(f)
        else:
            results = []
            
        # Add new result
        results.append(result)
        
        # Save
        with open(self.results_file, 'w') as f:
            json.dump(results, f, indent=2)
            
    async def run_all_challenges(self, model: str):
        """Run all challenge levels for a model"""
        
        print(f"\n🎯 Running all challenges for {model}")
        
        results = []
        for level in range(1, 6):
            result = await self.run_challenge(model, level)
            results.append(result)
            
        # Summary
        print(f"\n📋 Summary for {model}:")
        total_score = sum(r['best_score'] for r in results)
        passed = sum(1 for r in results if r['passed'])
        
        print(f"  Total Score: {total_score}/500")
        print(f"  Challenges Passed: {passed}/5")
        
        for r in results:
            status = "✅" if r['passed'] else "❌"
            print(f"  {status} Level {r['level']}: {r['best_score']}/100")
            
        return results
        
    async def run_all_models(self):
        """Run all challenges for all configured models"""
        
        models = os.getenv('TEST_MODELS', '').split(',')
        models = [m.strip() for m in models if m.strip()]
        
        if not models:
            print("❌ No models configured in TEST_MODELS")
            return
            
        print(f"\n🤖 Testing {len(models)} models")
        
        all_results = {}
        for model in models:
            all_results[model] = await self.run_all_challenges(model)
            
        # Final summary
        print("\n" + "="*60)
        print("FINAL RESULTS")
        print("="*60)
        
        for model, results in all_results.items():
            total = sum(r['best_score'] for r in results)
            passed = sum(1 for r in results if r['passed'])
            print(f"\n{model}:")
            print(f"  Total: {total}/500 ({total/5:.1f}%)")
            print(f"  Passed: {passed}/5")
            
        return all_results


@click.command()
@click.option('--model', help='Model to test (e.g., qwen2.5-coder:1.5b)')
@click.option('--level', type=int, help='Challenge level (1-5)')
@click.option('--all-models', is_flag=True, help='Test all configured models')
@click.option('--all-levels', is_flag=True, help='Run all challenge levels')
def main(model, level, all_models, all_levels):
    """Run Blossom handler generation challenges"""
    
    runner = ChallengeRunner()
    
    if all_models:
        asyncio.run(runner.run_all_models())
    elif model and all_levels:
        asyncio.run(runner.run_all_challenges(model))
    elif model and level:
        asyncio.run(runner.run_challenge(model, level))
    else:
        print("Usage:")
        print("  Run single: --model MODEL --level LEVEL")
        print("  Run all levels: --model MODEL --all-levels")
        print("  Run all models: --all-models")
        

if __name__ == '__main__':
    main()