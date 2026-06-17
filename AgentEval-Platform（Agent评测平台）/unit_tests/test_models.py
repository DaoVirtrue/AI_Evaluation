"""Unit tests for AgentEval models"""
import sys
P = F = 0

def test(n, fn):
    global P, F
    try: fn(); print(f"  [PASS] {n}"); P += 1
    except Exception as e: print(f"  [FAIL] {n}: {e}"); F += 1

def run():
    from app.models.models import Base, Project, Evaluation
    test("project_model", lambda: Project(id="test", name="Test"))
    test("evaluation_model", lambda: Evaluation(id="test", project_id="p1", name="Eval"))
    print(f"\n{'='*40}"); print(f"Unit Tests: PASS  {P}  FAIL  {F}")
    sys.exit(0 if F == 0 else 1)

if __name__ == "__main__": run()
