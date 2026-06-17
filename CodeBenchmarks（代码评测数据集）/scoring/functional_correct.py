"""
Functional Correctness Scorer — determines if generated code passes tests.

This is the primary scoring method for code evaluation:
    Code is correct if and only if it passes ALL test cases.

Unlike the current AgentEval platform's keyword-match scoring,
this evaluates actual execution correctness.
"""
from __future__ import annotations

from typing import List, Optional


class FunctionalCorrectnessScorer:
    """
    Evaluates code based on test case passing.

    A problem is considered "correct" (c=1) if ALL test cases pass.
    A problem is considered "incorrect" (c=0) if ANY test case fails.
    """

    def score(self, test_results: List[dict]) -> dict:
        """
        Score a single problem's test results.

        Args:
            test_results: List of test case results with at least {'passed': bool}

        Returns:
            dict with: passed (all passed?), passed_count, total_count, pass_rate
        """
        if not test_results:
            return {
                "passed": False,
                "passed_count": 0,
                "total_count": 0,
                "pass_rate": 0.0,
            }

        passed_count = sum(1 for t in test_results if t.get("passed", False))
        total_count = len(test_results)

        return {
            "passed": passed_count == total_count,
            "passed_count": passed_count,
            "total_count": total_count,
            "pass_rate": passed_count / total_count if total_count > 0 else 0.0,
        }

    def aggregate(self, results_per_problem: List[dict]) -> dict:
        """
        Aggregate across multiple problems.

        Args:
            results_per_problem: List of results from self.score() for each problem

        Returns:
            Aggregate statistics
        """
        total_problems = len(results_per_problem)
        if total_problems == 0:
            return {
                "total_problems": 0,
                "passed_problems": 0,
                "pass_rate": 0.0,
                "avg_test_pass_rate": 0.0,
            }

        passed_problems = sum(1 for r in results_per_problem if r["passed"])
        avg_test_rate = sum(r["pass_rate"] for r in results_per_problem) / total_problems

        return {
            "total_problems": total_problems,
            "passed_problems": passed_problems,
            "pass_rate": passed_problems / total_problems,
            "avg_test_pass_rate": avg_test_rate,
        }
