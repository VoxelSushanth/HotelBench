"""
HotelBench Evaluation Harness
Headless eval runner with pass/fail scoring and metrics
"""

import json
import asyncio
import argparse
import time
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from config import EVAL_OUTPUT_DIR, EVAL_RESULTS_FILE
from agent.graph import HotelBenchAgent
from agent.memory import memory_store


class EvalHarness:
    """Evaluation harness for running test cases and computing metrics."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.agent: HotelBenchAgent = None
        self.results: List[Dict[str, Any]] = []
    
    async def initialize(self):
        """Initialize the agent."""
        self.agent = HotelBenchAgent(headless=self.headless)
    
    async def run_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case and return results."""
        task = test_case["task"]
        test_id = test_case["id"]
        
        print(f"\n{'='*60}")
        print(f"Running Test Case #{test_id}: {task}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Run the task
            run_id = await self.agent.run(task)
            
            # Wait for completion (with timeout)
            max_wait = 120  # 2 minutes max per task
            wait_interval = 1
            elapsed = 0
            
            while elapsed < max_wait:
                run_data = memory_store.get_run(run_id)
                if run_data and run_data.get("status") in ["complete", "failed"]:
                    break
                await asyncio.sleep(wait_interval)
                elapsed += wait_interval
            
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            # Get final state
            run_data = memory_store.get_run(run_id) or {}
            
            # Evaluate success
            success = self._evaluate_success(test_case, run_data)
            
            result = {
                "test_id": test_id,
                "task": task,
                "run_id": run_id,
                "success": success,
                "status": run_data.get("status", "timeout"),
                "iterations": run_data.get("iteration", 0),
                "confidence": run_data.get("result", {}).get("confidence", 0) if run_data.get("result") else 0,
                "latency_ms": latency_ms,
                "error": run_data.get("error"),
                "expected_action_type": test_case.get("expected_action_type"),
                "difficulty": test_case.get("difficulty", "unknown"),
                "action_history": run_data.get("action_history", [])
            }
            
            status_str = "✅ PASS" if success else "❌ FAIL"
            print(f"{status_str} - Status: {result['status']}, Iterations: {result['iterations']}, Confidence: {result['confidence']:.2f}, Latency: {latency_ms:.0f}ms")
            
            if result["error"]:
                print(f"   Error: {result['error']}")
            
            return result
            
        except Exception as e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            result = {
                "test_id": test_id,
                "task": task,
                "run_id": None,
                "success": False,
                "status": "error",
                "iterations": 0,
                "confidence": 0,
                "latency_ms": latency_ms,
                "error": str(e),
                "expected_action_type": test_case.get("expected_action_type"),
                "difficulty": test_case.get("difficulty", "unknown"),
                "action_history": []
            }
            
            print(f"❌ FAIL - Error: {str(e)}")
            return result
    
    def _evaluate_success(self, test_case: Dict[str, Any], run_data: Dict[str, Any]) -> bool:
        """Evaluate if a test case passed."""
        # Check if task completed successfully
        if run_data.get("status") != "complete":
            return False
        
        result = run_data.get("result", {})
        
        # Check confidence threshold
        if result.get("confidence", 0) < 0.5:
            return False
        
        # Check if task_complete was set
        if not result.get("action_taken"):
            return False
        
        # For now, we consider it a pass if the agent reported completion with reasonable confidence
        # In production, you'd add more sophisticated validation
        return True
    
    def compute_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute aggregate metrics from results."""
        total = len(results)
        passed = sum(1 for r in results if r["success"])
        
        latencies = [r["latency_ms"] for r in results if r["success"]]
        confidences = [r["confidence"] for r in results if r["success"]]
        iterations = [r["iterations"] for r in results if r["success"]]
        
        # Compute failure modes
        failure_modes = {}
        for r in results:
            if not r["success"]:
                error = r.get("error", "unknown") or "unknown"
                # Categorize error
                if "selector_not_found" in error:
                    mode = "selector_not_found"
                elif "Max iterations" in error:
                    mode = "max_iterations_reached"
                elif "Claude API" in error or "API" in error:
                    mode = "api_error"
                elif "timeout" in error.lower():
                    mode = "timeout"
                else:
                    mode = "other"
                
                failure_modes[mode] = failure_modes.get(mode, 0) + 1
        
        # P95 latency
        sorted_latencies = sorted(latencies) if latencies else [0]
        p95_idx = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
        
        metrics = {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "task_success_rate": passed / total if total > 0 else 0,
            "avg_iterations": sum(iterations) / len(iterations) if iterations else 0,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "p95_latency_ms": p95_latency,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "failure_modes": failure_modes,
            "results_by_difficulty": self._group_by_difficulty(results)
        }
        
        return metrics
    
    def _group_by_difficulty(self, results: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
        """Group results by difficulty level."""
        grouped = {}
        for r in results:
            diff = r.get("difficulty", "unknown")
            if diff not in grouped:
                grouped[diff] = {"total": 0, "passed": 0}
            grouped[diff]["total"] += 1
            if r["success"]:
                grouped[diff]["passed"] += 1
        return grouped
    
    async def run_all(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run all test cases and return summary."""
        print(f"\n{'#'*60}")
        print(f"# HotelBench Evaluation Harness")
        print(f"# Running {len(test_cases)} test cases")
        print(f"{'#'*60}\n")
        
        self.results = []
        
        for test_case in test_cases:
            result = await self.run_test_case(test_case)
            self.results.append(result)
            
            # Small delay between tests to avoid rate limiting
            await asyncio.sleep(1)
        
        # Compute metrics
        metrics = self.compute_metrics(self.results)
        
        return metrics
    
    def save_results(self, metrics: Dict[str, Any], output_path: str):
        """Save results to JSON file."""
        output = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "individual_results": self.results
        }
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_path}")
    
    def print_summary(self, metrics: Dict[str, Any]):
        """Print a summary of the evaluation results."""
        print(f"\n{'#'*60}")
        print(f"# EVALUATION SUMMARY")
        print(f"{'#'*60}")
        
        print(f"\n📊 Overall Metrics:")
        print(f"   Total Tests: {metrics['total_tests']}")
        print(f"   Passed: {metrics['passed']}")
        print(f"   Failed: {metrics['failed']}")
        print(f"   Success Rate: {metrics['task_success_rate']*100:.1f}%")
        
        print(f"\n⏱️ Performance:")
        print(f"   Avg Iterations: {metrics['avg_iterations']:.2f}")
        print(f"   Avg Confidence: {metrics['avg_confidence']:.2f}")
        print(f"   Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
        print(f"   P95 Latency: {metrics['p95_latency_ms']:.0f}ms")
        
        print(f"\n📈 Results by Difficulty:")
        for diff, stats in metrics.get('results_by_difficulty', {}).items():
            rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"   {diff.capitalize()}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")
        
        if metrics.get('failure_modes'):
            print(f"\n⚠️ Failure Modes:")
            for mode, count in metrics['failure_modes'].items():
                print(f"   {mode}: {count}")
        
        # Quality gate check
        print(f"\n{'#'*60}")
        if metrics['task_success_rate'] >= 0.75:
            print("✅ QUALITY GATE PASSED: Success rate >= 75%")
        else:
            print("❌ QUALITY GATE FAILED: Success rate < 75%")
        
        if metrics['avg_confidence'] >= 0.80:
            print("✅ QUALITY GATE PASSED: Avg confidence >= 0.80")
        else:
            print("❌ QUALITY GATE FAILED: Avg confidence < 0.80")
        print(f"{'#'*60}\n")


async def main():
    parser = argparse.ArgumentParser(description="HotelBench Evaluation Harness")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run with visible browser")
    parser.add_argument("--output", type=str, default=EVAL_RESULTS_FILE, help="Output file path")
    parser.add_argument("--test-cases", type=str, default="evals/test_cases.json", help="Test cases file")
    
    args = parser.parse_args()
    
    # Load test cases
    with open(args.test_cases, 'r') as f:
        test_cases = json.load(f)
    
    # Initialize harness
    harness = EvalHarness(headless=args.headless)
    await harness.initialize()
    
    try:
        # Run all tests
        metrics = await harness.run_all(test_cases)
        
        # Save results
        harness.save_results(metrics, args.output)
        
        # Print summary
        harness.print_summary(metrics)
        
    finally:
        # Cleanup
        if harness.agent:
            await harness.agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
