"""Unit tests for CodeBenchmarks — loader, pass@k, and functional correctness."""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}  -- {detail}")


# ── Test: pass@k ───────────────────────────────────────────────────────

def test_pass_at_k():
    """Test pass@k calculation."""
    print("\n--- pass@k Tests ---")

    from scoring.pass_at_k import pass_at_k, combination, calculate_pass_at_k

    # Combination tests
    check("C(5,2) = 10", abs(combination(5, 2) - 10) < 0.001)
    check("C(10,0) = 1", combination(10, 0) == 1)
    check("C(10,10) = 1", combination(10, 10) == 1)
    check("C(3,5) = 0 (k>n)", combination(3, 5) == 0)

    # pass@k tests (known cases from HumanEval paper)
    # If n=200, c=120, k=1: pass@1 ≈ c/n = 0.6
    score = pass_at_k(200, 120, 1)
    check("pass@1(200,120) ≈ 0.6", abs(score - 0.6) < 0.01, f"Got {score:.4f}")

    # If n=200, c=0: pass@k = 0
    check("pass@1(200,0) = 0", pass_at_k(200, 0, 1) == 0)

    # If all correct: pass@k = 1
    check("pass@10(200,200) = 1", pass_at_k(200, 200, 10) == 1)

    # If n-c < k: pass@k = 1
    check("pass@100(200,150) = 1", pass_at_k(200, 150, 100) == 1)

    # Aggregate calculation
    results = [
        {"n": 200, "c": 120, "task_id": "test/1"},
        {"n": 200, "c": 80, "task_id": "test/2"},
        {"n": 200, "c": 40, "task_id": "test/3"},
    ]
    summary = calculate_pass_at_k(results, k_values=[1, 10])
    check("pass@1 aggregate is float", isinstance(summary["pass@1"], float))
    check("pass@10 aggregate is float", isinstance(summary["pass@10"], float))
    check("pass@1 in [0,1]", 0 <= summary["pass@1"] <= 1)


# ── Test: Functional Correctness ───────────────────────────────────────

def test_functional_correctness():
    """Test functional correctness scorer."""
    print("\n--- Functional Correctness Tests ---")

    from scoring.functional_correct import FunctionalCorrectnessScorer

    scorer = FunctionalCorrectnessScorer()

    # All pass
    result = scorer.score([
        {"name": "test1", "passed": True},
        {"name": "test2", "passed": True},
        {"name": "test3", "passed": True},
    ])
    check("All pass → passed=True", result["passed"])
    check("All pass → pass_rate=1.0", result["pass_rate"] == 1.0)

    # Some fail
    result = scorer.score([
        {"name": "test1", "passed": True},
        {"name": "test2", "passed": False},
        {"name": "test3", "passed": True},
    ])
    check("Some fail → passed=False", not result["passed"])
    check("2/3 pass → pass_rate≈0.667", abs(result["pass_rate"] - 0.667) < 0.001)

    # All fail
    result = scorer.score([
        {"name": "test1", "passed": False},
    ])
    check("All fail → passed=False", not result["passed"])
    check("All fail → pass_rate=0", result["pass_rate"] == 0)

    # Empty
    result = scorer.score([])
    check("Empty → passed=False", not result["passed"])

    # Aggregate
    agg = scorer.aggregate([
        {"passed": True, "passed_count": 3, "total_count": 3, "pass_rate": 1.0},
        {"passed": False, "passed_count": 1, "total_count": 3, "pass_rate": 0.333},
    ])
    check("Aggregate: 1/2 problems passed", agg["passed_problems"] == 1)
    check("Aggregate: pass_rate=0.5", agg["pass_rate"] == 0.5)


# ── Test: Benchmark Loader ─────────────────────────────────────────────

def test_benchmark_loader():
    """Test benchmark loader with built-in samples."""
    print("\n--- Benchmark Loader Tests ---")

    from benchmarks.loader import BenchmarkLoader, CodeProblem, TestCase

    loader = BenchmarkLoader()

    # Load HumanEval sample
    dataset = loader.load("humaneval")
    check("HumanEval sample loaded", dataset.name == "HumanEval")
    check("Has problems", len(dataset.problems) > 0)
    check("Problems have task_id", all(p.task_id for p in dataset.problems))
    check("Problems have prompt", all(p.prompt for p in dataset.problems))

    # Load MBPP sample
    dataset = loader.load("mbpp")
    check("MBPP sample loaded", dataset.name == "MBPP")

    # Load custom sample
    dataset = loader.load("custom")
    check("Custom sample loaded", len(dataset.problems) > 0)

    # Test error on unknown benchmark
    try:
        loader.load("nonexistent")
        check("Unknown benchmark error", False, "Should have raised ValueError")
    except ValueError:
        check("Unknown benchmark raises ValueError", True)

    # Test CodeProblem dataclass
    problem = CodeProblem(
        task_id="test/1",
        prompt="def foo(): pass",
        entry_point="foo",
        canonical_solution="",
    )
    check("CodeProblem created", problem.task_id == "test/1")
    check("Default language is python", problem.language == "python")

    # Test TestCase dataclass
    tc = TestCase(name="test_hello", expected="hello")
    check("TestCase created", tc.name == "test_hello")
    check("Default timeout_ms=5000", tc.timeout_ms == 5000)


# ── Run All Tests ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("CodeBenchmarks Unit Tests")
    print("=" * 60)

    test_pass_at_k()
    test_functional_correctness()
    test_benchmark_loader()

    print(f"\n{'=' * 60}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 60}")

    sys.exit(FAIL)
