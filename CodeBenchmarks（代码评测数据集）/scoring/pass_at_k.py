"""
pass@k Calculator — standard metric for code generation evaluation.

Implements the unbiased estimator from the HumanEval paper:
    pass@k = 1 - C(n-c, k) / C(n, k)

Where:
    n = total number of samples per problem
    c = number of correct samples
    k = the k in pass@k

Reference: Chen et al., "Evaluating Large Language Models Trained on Code" (2021)
"""
from __future__ import annotations

import math
from typing import List


def combination(n: int, k: int) -> float:
    """
    Calculate C(n, k) = n! / (k! * (n-k)!)

    Returns 0 if k > n (by convention).
    """
    if k > n:
        return 0.0
    if k == 0 or k == n:
        return 1.0
    # Use multiplicative formula for numerical stability
    k = min(k, n - k)
    result = 1.0
    for i in range(k):
        result = result * (n - i) / (i + 1)
    return result


def pass_at_k(n: int, c: int, k: int) -> float:
    """
    Calculate pass@k using the unbiased estimator.

    pass@k = 1 - C(n-c, k) / C(n, k)  (when n-c >= k)
    pass@k = 1                            (when n-c < k, i.e., all samples pass)

    Args:
        n: Total number of samples generated for this problem
        c: Number of samples that pass all tests
        k: The k parameter (k=1, k=10, k=100 are common)

    Returns:
        float between 0.0 and 1.0 (estimated probability that at least 1
        of k samples passes)
    """
    if n == 0:
        return 0.0
    if c == 0:
        return 0.0
    if n - c < k:
        return 1.0  # Not enough wrong samples — at least 1 of k passes

    comb_all = combination(n, k)
    comb_wrong = combination(n - c, k)

    if comb_all == 0:
        return 0.0

    return 1.0 - comb_wrong / comb_all


def calculate_pass_at_k(
    results_per_problem: List[dict],
    k_values: List[int] = None,
) -> dict:
    """
    Calculate pass@k across all problems.

    Args:
        results_per_problem: List of dicts with keys:
            - 'n': total samples for this problem
            - 'c': number of correct samples
            - 'task_id': problem identifier (optional)
        k_values: List of k values to calculate (default: [1, 5, 10, 100])

    Returns:
        dict with keys like 'pass@1', 'pass@5', etc. (averaged across problems)
    """
    if k_values is None:
        k_values = [1, 5, 10, 100]

    if not results_per_problem:
        return {f"pass@{k}": 0.0 for k in k_values}

    scores: dict = {f"pass@{k}": [] for k in k_values}

    for result in results_per_problem:
        n = result.get("n", 0)
        c = result.get("c", 0)
        for k in k_values:
            score = pass_at_k(n, c, k)
            scores[f"pass@{k}"].append(score)

    # Average across all problems
    return {
        f"pass@{k}": sum(scores[f"pass@{k}"]) / len(scores[f"pass@{k}"])
        for k in k_values
    }


def calculate_pass_at_k_detailed(
    results_per_problem: List[dict],
    k_values: List[int] = None,
) -> dict:
    """
    Calculate pass@k with per-problem breakdown.

    Returns:
        dict with summary (averages) and per_problem (individual scores)
    """
    if k_values is None:
        k_values = [1, 5, 10]

    summary = calculate_pass_at_k(results_per_problem, k_values)

    per_problem = []
    for result in results_per_problem:
        problem_scores = {
            "task_id": result.get("task_id", "unknown"),
            "n": result.get("n", 0),
            "c": result.get("c", 0),
        }
        for k in k_values:
            problem_scores[f"pass@{k}"] = pass_at_k(
                result.get("n", 0), result.get("c", 0), k
            )
        per_problem.append(problem_scores)

    return {
        "summary": summary,
        "per_problem": per_problem,
        "k_values": k_values,
        "total_problems": len(results_per_problem),
    }
