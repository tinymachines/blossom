#!/usr/bin/env python3
"""
Main test runner for Blossom LLM handler generation with verbose output
"""

import asyncio
import json
import sys
import os
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import click
import ollama
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.syntax import Syntax

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / 'logs' / f'challenge_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ChallengeRunner')
console = Console()

# Add parent paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from prompt_optimizer import PromptOptimizer
from evaluate_handler import HandlerEvaluator
from model_client import ModelClient


class ChallengeRunner:
    """Run handler generation challenges with detailed output"""
    
    def __init__(self, verbose=True):
        load_dotenv()
        self.verbose = verbose
        self.prompt_optimizer = PromptOptimizer()
        self.evaluator = HandlerEvaluator(verbose=verbose)
        self.model_client = ModelClient()
        self.output_dir = Path(__file__).parent.parent / 'generated'
        self.results_file = Path(__file__).parent.parent / 'evaluation' / 'results.json'
        
        logger.info(f"ChallengeRunner initialized")
        logger.debug(f"Output directory: {self.output_dir}")
        logger.debug(f"Results file: {self.results_file}")
        
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
        
        # Display challenge header
        console.print(Panel.fit(
            f"[bold cyan]Challenge:[/bold cyan] {challenge_name}\n"
            f"[bold green]Model:[/bold green] {model}\n"
            f"[bold yellow]Level:[/bold yellow] {level}\n"
            f"[bold magenta]Max Attempts:[/bold magenta] {max_retries}",
            title="🚀 Starting Challenge",
            border_style="bright_blue"
        ))
        
        logger.info(f"Starting challenge: {challenge_name} with model: {model}")
        
        # Create output directory for this model/challenge
        model_dir = self.output_dir / model.replace(':', '_') / challenge_name
        model_dir.mkdir(parents=True, exist_ok=True)
        
        best_score = 0
        best_handler = None
        attempts = []
        
        for attempt in range(max_retries):
            attempt_start = time.time()
            
            console.print(f"\n[bold yellow]🎯 Attempt {attempt + 1}/{max_retries}[/bold yellow]")
            console.print("-" * 50)
            
            logger.info(f"Starting attempt {attempt + 1}/{max_retries}")
            
            try:
                # Generate prompt
                with console.status("[bold green]Creating optimized prompt...") as status:
                    prompt = self.prompt_optimizer.create_prompt(model, challenge_name, level)
                    logger.debug(f"Prompt length: {len(prompt)} characters")
                    if self.verbose:
                        console.print(Panel(
                            Syntax(prompt[:500] + "..." if len(prompt) > 500 else prompt, "text", theme="monokai"),
                            title="Prompt Preview",
                            border_style="dim"
                        ))
                
                # Generate handler code
                console.print("[bold cyan]🤖 Generating handler code...[/bold cyan]")
                generation_start = time.time()
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TimeElapsedColumn(),
                    console=console,
                    transient=True
                ) as progress:
                    task = progress.add_task("Waiting for LLM response...", total=None)
                    handler_code = await self.model_client.generate(model, prompt)
                    progress.update(task, completed=100)
                
                generation_time = time.time() - generation_start
                logger.info(f"Code generation completed in {generation_time:.2f}s")
                console.print(f"[green]✓[/green] Generated in {generation_time:.2f}s")
                
                # Extract code from response
                handler_code = self._extract_code(handler_code)
                logger.debug(f"Extracted {len(handler_code)} characters of code")
                
                # Display code preview if verbose
                if self.verbose:
                    console.print(Panel(
                        Syntax(handler_code[:1000] + "..." if len(handler_code) > 1000 else handler_code, "python", theme="monokai"),
                        title="Generated Code Preview",
                        border_style="dim"
                    ))
                
                # Save generated handler
                handler_path = model_dir / f'handler_attempt{attempt + 1}.py'
                with open(handler_path, 'w') as f:
                    f.write(handler_code)
                console.print(f"[green]✓[/green] Saved to {handler_path.relative_to(self.output_dir.parent)}")
                logger.info(f"Handler saved to {handler_path}")
                
                # Evaluate handler
                console.print("\n[bold magenta]🧪 Evaluating handler...[/bold magenta]")
                eval_start = time.time()
                
                score = await self.evaluator.evaluate(handler_path, level)
                
                eval_time = time.time() - eval_start
                logger.info(f"Evaluation completed in {eval_time:.2f}s with score {score}/100")
                
                attempts.append({
                    'attempt': attempt + 1,
                    'score': score,
                    'path': str(handler_path)
                })
                
                # Display score with visual indicator
                attempt_time = time.time() - attempt_start
                
                score_color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
                score_emoji = "🏆" if score >= 70 else "📈" if score >= 40 else "📉"
                
                console.print(Panel(
                    f"[bold {score_color}]{score_emoji} Score: {score}/100[/bold {score_color}]\n"
                    f"[dim]Time: {attempt_time:.2f}s[/dim]",
                    title="Attempt Result",
                    border_style=score_color
                ))
                
                if score > best_score:
                    best_score = score
                    best_handler = handler_path
                    console.print(f"[bold green]🆙 New best score![/bold green]")
                    
                # If we got a good score, stop retrying
                if score >= 70:
                    console.print(f"[bold green]✅ PASSED with score {score}![/bold green]")
                    break
                elif attempt < max_retries - 1:
                    console.print(f"[yellow]🔄 Score below threshold (70), retrying...[/yellow]")
                    
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}", exc_info=True)
                console.print(f"[bold red]❌ Error: {e}[/bold red]")
                attempts.append({
                    'attempt': attempt + 1,
                    'score': 0,
                    'error': str(e),
                    'time': time.time() - attempt_start
                })
                
        # Save best handler as main
        if best_handler:
            final_path = model_dir / 'handler.py'
            with open(best_handler) as f:
                content = f.read()
            with open(final_path, 'w') as f:
                f.write(content)
                
        # Display summary table
        if self.verbose:
            table = Table(title="Challenge Summary", show_header=True, header_style="bold magenta")
            table.add_column("Attempt", style="cyan", width=10)
            table.add_column("Score", style="yellow", width=12)
            table.add_column("Time", style="green", width=10)
            table.add_column("Status", width=15)
            
            for att in attempts:
                score = att.get('score', 0)
                status_icon = "✅" if score >= 70 else "⚠️" if score >= 40 else "❌"
                status_text = "PASSED" if score >= 70 else "PARTIAL" if score >= 40 else "FAILED"
                time_str = f"{att.get('time', 0):.2f}s" if 'time' in att else "N/A"
                
                table.add_row(
                    str(att['attempt']),
                    f"{score}/100",
                    time_str,
                    f"{status_icon} {status_text}"
                )
            
            console.print(table)
        
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
        logger.info(f"Challenge completed: {challenge_name} - Best score: {best_score}/100")
        
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
        
        console.print(Panel(
            f"[bold cyan]Running ALL challenges for model: {model}[/bold cyan]",
            title="🎯 Full Test Suite",
            border_style="bright_blue"
        ))
        
        logger.info(f"Starting full test suite for model: {model}")
        
        results = []
        for level in range(1, 6):
            result = await self.run_challenge(model, level)
            results.append(result)
            
        # Create summary table
        total_score = sum(r['best_score'] for r in results)
        passed = sum(1 for r in results if r['passed'])
        
        table = Table(
            title=f"Summary for {model}",
            show_header=True,
            header_style="bold cyan",
            title_style="bold magenta"
        )
        table.add_column("Level", style="cyan", width=8)
        table.add_column("Challenge", style="yellow", width=15)
        table.add_column("Score", style="green", width=12)
        table.add_column("Status", width=12)
        table.add_column("Attempts", width=10)
        
        for r in results:
            status = "✅ PASS" if r['passed'] else "❌ FAIL"
            table.add_row(
                str(r['level']),
                r['challenge'].split('_', 1)[1],
                f"{r['best_score']}/100",
                status,
                str(len(r['attempts']))
            )
        
        # Add summary row
        table.add_row(
            "[bold]TOTAL[/bold]",
            "[bold]All Levels[/bold]",
            f"[bold]{total_score}/500[/bold]",
            f"[bold]{passed}/5 passed[/bold]",
            "",
            style="bold white on blue"
        )
        
        console.print(table)
        
        # Display percentage bar
        percentage = (total_score / 500) * 100
        bar_length = 50
        filled = int(bar_length * percentage / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        color = "green" if percentage >= 70 else "yellow" if percentage >= 40 else "red"
        console.print(f"\n[bold {color}]Overall: [{bar}] {percentage:.1f}%[/bold {color}]")
        
        logger.info(f"Test suite completed for {model}: {total_score}/500 ({percentage:.1f}%)")
            
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
@click.option('--verbose/--quiet', default=True, help='Verbose output mode')
@click.option('--max-retries', type=int, default=3, help='Maximum retry attempts per challenge')
def main(model, level, all_models, all_levels, verbose, max_retries):
    """Run Blossom handler generation challenges with detailed output"""
    
    console.print(Panel.fit(
        "[bold cyan]Blossom Handler Generation Test Suite[/bold cyan]\n"
        "[yellow]Automated evaluation of LLM code generation capabilities[/yellow]",
        title="🌸 Welcome to Blossom",
        border_style="bright_magenta"
    ))
    
    runner = ChallengeRunner(verbose=verbose)
    
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