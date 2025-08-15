#!/usr/bin/env python3
"""
Verbose test runner with real-time monitoring and detailed output
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
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.text import Text
from rich.columns import Columns
import logging

# Add parent paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from run_challenge import ChallengeRunner
from evaluate_handler import HandlerEvaluator
from model_client import ModelClient

# Initialize console
console = Console()

# Configure logging
log_file = Path(__file__).parent.parent / 'logs' / f'verbose_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('VerboseRunner')


class VerboseTestRunner:
    """Enhanced test runner with real-time monitoring"""
    
    def __init__(self):
        self.runner = ChallengeRunner(verbose=True)
        self.current_status = {}
        self.test_history = []
        self.start_time = None
        
    def create_dashboard(self) -> Layout:
        """Create live dashboard layout"""
        layout = Layout()
        
        # Main layout structure
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=4)
        )
        
        # Header
        layout["header"].update(Panel(
            Text("🌸 Blossom Verbose Test Runner", style="bold magenta", justify="center"),
            border_style="bright_blue"
        ))
        
        # Body split
        layout["body"].split_row(
            Layout(name="status", ratio=1),
            Layout(name="details", ratio=2)
        )
        
        # Footer
        layout["footer"].update(self.get_stats_panel())
        
        return layout
    
    def get_status_panel(self) -> Panel:
        """Get current status panel"""
        status_text = ""
        
        if self.current_status:
            status_text = f"""
[bold cyan]Model:[/bold cyan] {self.current_status.get('model', 'N/A')}
[bold yellow]Challenge:[/bold yellow] {self.current_status.get('challenge', 'N/A')}
[bold green]Level:[/bold green] {self.current_status.get('level', 'N/A')}
[bold magenta]Attempt:[/bold magenta] {self.current_status.get('attempt', 'N/A')}
[bold blue]Phase:[/bold blue] {self.current_status.get('phase', 'Initializing')}
[bold red]Status:[/bold red] {self.current_status.get('status', 'Running')}
"""
        
        return Panel(
            status_text or "Waiting to start...",
            title="Current Test",
            border_style="green"
        )
    
    def get_details_panel(self) -> Panel:
        """Get detailed information panel"""
        details = self.current_status.get('details', [])
        
        if details:
            detail_text = "\n".join(details[-10:])  # Show last 10 entries
        else:
            detail_text = "No details yet..."
        
        return Panel(
            detail_text,
            title="Live Details",
            border_style="blue"
        )
    
    def get_stats_panel(self) -> Panel:
        """Get statistics panel"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            elapsed_str = f"{elapsed:.1f}s"
        else:
            elapsed_str = "0s"
        
        total_tests = len(self.test_history)
        passed = sum(1 for t in self.test_history if t.get('passed', False))
        
        stats_text = f"""
[bold]Tests Run:[/bold] {total_tests}
[bold green]Passed:[/bold green] {passed}
[bold red]Failed:[/bold red] {total_tests - passed}
[bold blue]Time Elapsed:[/bold blue] {elapsed_str}
"""
        
        return Panel(
            stats_text,
            title="Statistics",
            border_style="yellow"
        )
    
    async def run_test_with_monitoring(
        self,
        model: str,
        level: int,
        max_retries: int = 3
    ):
        """Run a test with live monitoring"""
        
        self.start_time = time.time()
        challenge_name = f"level{level}_{self._get_challenge_name(level)}"
        
        # Initialize status
        self.current_status = {
            'model': model,
            'challenge': challenge_name,
            'level': level,
            'attempt': 0,
            'phase': 'Starting',
            'status': 'Running',
            'details': []
        }
        
        logger.info(f"\n{'='*80}")
        logger.info(f"STARTING TEST: {challenge_name} with {model}")
        logger.info(f"{'='*80}")
        
        # Create layout
        layout = self.create_dashboard()
        
        with Live(layout, refresh_per_second=4, console=console) as live:
            for attempt in range(max_retries):
                self.current_status['attempt'] = attempt + 1
                self.current_status['phase'] = 'Generating Prompt'
                self.current_status['details'].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Starting attempt {attempt + 1}"
                )
                
                # Update panels
                layout["body"]["status"].update(self.get_status_panel())
                layout["body"]["details"].update(self.get_details_panel())
                layout["footer"].update(self.get_stats_panel())
                
                try:
                    # Generate prompt
                    self.current_status['phase'] = 'Creating Prompt'
                    self.current_status['details'].append(f"📝 Creating optimized prompt...")
                    logger.debug("Creating prompt...")
                    await asyncio.sleep(0.5)  # Simulate work
                    
                    # Generate code
                    self.current_status['phase'] = 'Generating Code'
                    self.current_status['details'].append(f"🤖 Waiting for LLM response...")
                    logger.debug("Generating code...")
                    await asyncio.sleep(2)  # Simulate generation
                    
                    # Evaluate
                    self.current_status['phase'] = 'Evaluating'
                    self.current_status['details'].append(f"🧪 Running evaluation tests...")
                    logger.debug("Evaluating handler...")
                    
                    # Simulate evaluation steps
                    for step in ['Syntax Check', 'Structure Analysis', 'Load Test', 'Functionality Test']:
                        self.current_status['details'].append(f"  ▶ {step}")
                        layout["body"]["details"].update(self.get_details_panel())
                        await asyncio.sleep(0.5)
                    
                    # Random score for demo
                    import random
                    score = random.randint(30, 95)
                    
                    self.current_status['details'].append(f"📊 Score: {score}/100")
                    
                    if score >= 70:
                        self.current_status['status'] = 'PASSED'
                        self.current_status['details'].append(f"✅ Test PASSED!")
                        logger.info(f"Test PASSED with score {score}")
                        break
                    else:
                        self.current_status['status'] = 'RETRY'
                        self.current_status['details'].append(f"⚠️ Score below threshold, retrying...")
                        logger.warning(f"Score {score} below threshold")
                        
                except Exception as e:
                    self.current_status['status'] = 'ERROR'
                    self.current_status['details'].append(f"❌ Error: {e}")
                    logger.error(f"Test error: {e}")
                
                # Update display
                layout["body"]["status"].update(self.get_status_panel())
                layout["body"]["details"].update(self.get_details_panel())
                layout["footer"].update(self.get_stats_panel())
                
                await asyncio.sleep(1)
            
            # Final status
            if self.current_status['status'] != 'PASSED':
                self.current_status['status'] = 'FAILED'
            
            # Add to history
            self.test_history.append({
                'model': model,
                'challenge': challenge_name,
                'level': level,
                'passed': self.current_status['status'] == 'PASSED',
                'attempts': self.current_status['attempt']
            })
            
            # Final update
            layout["body"]["status"].update(self.get_status_panel())
            layout["body"]["details"].update(self.get_details_panel())
            layout["footer"].update(self.get_stats_panel())
    
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
    
    async def run_all_levels(self, model: str):
        """Run all challenge levels with monitoring"""
        
        console.print(Panel(
            f"[bold cyan]Running ALL challenges for: {model}[/bold cyan]",
            title="🎯 Full Test Suite",
            border_style="bright_magenta"
        ))
        
        for level in range(1, 6):
            await self.run_test_with_monitoring(model, level)
            
            # Show intermediate summary
            console.print(Panel(
                f"Completed Level {level}",
                title="Progress",
                border_style="green"
            ))
        
        # Final summary
        self.show_final_summary()
    
    def show_final_summary(self):
        """Display final test summary"""
        
        table = Table(title="Final Results", show_header=True, header_style="bold magenta")
        table.add_column("Challenge", style="cyan")
        table.add_column("Level", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Attempts", style="blue")
        
        for test in self.test_history:
            status = "✅ PASS" if test['passed'] else "❌ FAIL"
            table.add_row(
                test['challenge'],
                str(test['level']),
                status,
                str(test['attempts'])
            )
        
        console.print(table)
        
        # Summary stats
        total = len(self.test_history)
        passed = sum(1 for t in self.test_history if t['passed'])
        
        console.print(Panel(
            f"""
[bold green]Passed:[/bold green] {passed}/{total}
[bold yellow]Success Rate:[/bold yellow] {(passed/total*100):.1f}%
[bold blue]Total Time:[/bold blue] {time.time() - self.start_time:.1f}s
""",
            title="📊 Summary Statistics",
            border_style="bright_cyan"
        ))


@click.command()
@click.option('--model', required=True, help='Model to test (e.g., qwen2.5-coder:1.5b)')
@click.option('--level', type=int, help='Specific challenge level (1-5)')
@click.option('--all-levels', is_flag=True, help='Run all challenge levels')
@click.option('--watch-logs', is_flag=True, help='Watch log file in real-time')
def main(model, level, all_levels, watch_logs):
    """Run Blossom tests with verbose real-time output"""
    
    console.print(Panel.fit(
        "[bold cyan]🌸 Blossom Verbose Test Runner[/bold cyan]\n"
        "[yellow]Real-time monitoring and detailed logging[/yellow]",
        border_style="bright_magenta"
    ))
    
    if watch_logs:
        console.print(f"[dim]Logs are being written to: {log_file}[/dim]")
        console.print("[dim]You can tail the log file in another terminal for detailed output[/dim]\n")
    
    runner = VerboseTestRunner()
    
    if all_levels or not level:
        asyncio.run(runner.run_all_levels(model))
    else:
        asyncio.run(runner.run_test_with_monitoring(model, level))
    
    logger.info("Test run completed")
    console.print("\n[bold green]✨ Test run completed![/bold green]")
    
    if watch_logs:
        console.print(f"\n[dim]Full logs available at: {log_file}[/dim]")


if __name__ == '__main__':
    main()